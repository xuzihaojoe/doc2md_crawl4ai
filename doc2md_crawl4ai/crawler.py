from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

import aiohttp
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .discovery import DiscoveryOptions, chunked, discover_urls
from .writer import WriteResult, write_index, write_markdown


@dataclass(frozen=True)
class CrawlOptions:
    start_url: str
    out_dir: Path
    max_pages: int = 200
    concurrency: int = 6
    delay: float = 0.0
    scope: str = "same_origin"
    include_re: re.Pattern[str] | None = None
    exclude_re: re.Pattern[str] | None = None
    ignore_links: bool = False
    engine: str = "auto"  # auto | playwright | http
    main_selector: str = ""
    use_fit_markdown: bool = False
    verbose: bool = False


def _build_markdown_generator(opt: CrawlOptions) -> DefaultMarkdownGenerator:
    # 对文档站：PruningContentFilter 通常能把导航/页脚等噪音压下去
    prune = PruningContentFilter(threshold=0.55, threshold_type="dynamic", min_word_threshold=30)
    return DefaultMarkdownGenerator(
        content_filter=prune,
        options={
            "ignore_links": bool(opt.ignore_links),
            "ignore_images": True,
            "escape_html": False,
            "body_width": 0,
            "skip_internal_links": True,
        },
    )


def _build_run_config(opt: CrawlOptions) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=_build_markdown_generator(opt),
        stream=True,  # 我们用流式模式逐个处理结果
        remove_overlay_elements=True,
        word_count_threshold=1,
        page_timeout=80000,
    )


def _pick_markdown(md_obj, use_fit: bool) -> str:
    if use_fit:
        return getattr(md_obj, "fit_markdown", None) or getattr(md_obj, "raw_markdown", None) or str(
            md_obj
        )
    return getattr(md_obj, "raw_markdown", None) or str(md_obj)


def _extract_main_html(html: str, preferred_selector: str = "") -> str:
    """
    轻量“主内容抽取”：
    - 若传入 main_selector，则优先使用
    - 否则按常见文档站结构尝试：main/article/role=main/#content/.content/...；
      找不到就回退整个 body。
    """
    soup = BeautifulSoup(html, "lxml")

    selectors: list[str] = []
    if preferred_selector.strip():
        selectors.append(preferred_selector.strip())

    selectors += [
        "main",
        "article",
        "div[role='main']",
        "#content",
        ".content",
        ".markdown",
        ".md-content",
        ".doc-content",
        ".theme-doc-markdown",  # docusaurus
    ]

    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return str(el)

    body = soup.body
    return str(body) if body else html


async def _crawl_via_http(opt: CrawlOptions, urls: list[str]) -> list[WriteResult]:
    """
    轻量模式：不用浏览器，直接 aiohttp 拉 HTML，再用 Crawl4AI 的 DefaultMarkdownGenerator 转 Markdown。
    适合大多数“静态文档站”；不需要 playwright 的系统依赖。
    """
    md_gen = _build_markdown_generator(opt)

    sem = asyncio.Semaphore(max(1, opt.concurrency))
    headers = {"User-Agent": "doc2md-crawl4ai/0.1.0"}

    async def fetch_and_convert(url: str) -> WriteResult | None:
        async with sem:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                    if r.status >= 400:
                        return None
                    html = await r.text(errors="ignore")
            except Exception:
                return None

            main_html = _extract_main_html(html, preferred_selector=opt.main_selector)
            md_res = md_gen.generate_markdown(input_html=main_html, base_url=url, citations=True)
            content = _pick_markdown(md_res, use_fit=opt.use_fit_markdown)
            content = f"<!-- source: {url} -->\n\n{content}".strip() + "\n"
            return write_markdown(opt.out_dir, url, content)

    results: list[WriteResult] = []
    async with aiohttp.ClientSession(headers=headers) as session:
        pbar = tqdm(total=len(urls), desc="crawl(http)", unit="page")

        it = iter(urls)
        in_flight: set[asyncio.Task] = set()

        def spawn_next() -> None:
            try:
                u = next(it)
            except StopIteration:
                return
            in_flight.add(asyncio.create_task(fetch_and_convert(u)))

        # 预热任务池
        for _ in range(max(1, opt.concurrency)):
            spawn_next()

        while in_flight:
            done, pending = await asyncio.wait(in_flight, return_when=asyncio.FIRST_COMPLETED)
            in_flight = pending

            for t in done:
                try:
                    wr = t.result()
                    if wr:
                        results.append(wr)
                except Exception:
                    # 忽略单页异常
                    pass
                finally:
                    pbar.update(1)

                if opt.delay > 0:
                    await asyncio.sleep(opt.delay)
                spawn_next()

        pbar.close()

    return results


async def crawl_site(opt: CrawlOptions) -> list[WriteResult]:
    opt.out_dir.mkdir(parents=True, exist_ok=True)

    # 1) URL 发现（导航树/站内 BFS）
    disc_opt = DiscoveryOptions(
        start_url=opt.start_url,
        scope=opt.scope,
        include_re=opt.include_re,
        exclude_re=opt.exclude_re,
        verbose=opt.verbose,
    )
    urls = await discover_urls(disc_opt, max_pages=opt.max_pages)
    if opt.verbose:
        print(f"[discover] found {len(urls)} urls")

    # 2) 抓取并生成 Markdown（并发）
    results: list[WriteResult] = []

    async def crawl_playwright() -> list[WriteResult]:
        browser_cfg = BrowserConfig(headless=True, verbose=opt.verbose, java_script_enabled=True)
        run_cfg = _build_run_config(opt)
        if opt.main_selector.strip():
            # Crawl4AI 支持通过 css_selector 限制抓取范围（放到 run config 里）
            run_cfg = run_cfg.clone(css_selector=opt.main_selector.strip())
        out: list[WriteResult] = []

        # Crawl4AI 内部会做资源感知调度；这里再分批以便我们加 delay/更可控
        batches = chunked(urls, max(1, opt.concurrency))

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            pbar = tqdm(total=len(urls), desc="crawl(playwright)", unit="page")
            for batch in batches:
                async for res in await crawler.arun_many(batch, config=run_cfg):
                    pbar.update(1)
                    if not res.success:
                        if opt.verbose:
                            tqdm.write(f"[error] {res.url}: {res.error_message}")
                        continue

                    content = _pick_markdown(res.markdown, use_fit=opt.use_fit_markdown)
                    content = f"<!-- source: {res.url} -->\n\n{content}".strip() + "\n"
                    out.append(write_markdown(opt.out_dir, res.url, content))

                if opt.delay > 0:
                    await asyncio.sleep(opt.delay)
            pbar.close()

        return out

    if opt.engine == "http":
        results = await _crawl_via_http(opt, urls)
    elif opt.engine == "playwright":
        results = await crawl_playwright()
    else:
        # auto：优先 playwright（能处理动态页面/点击），失败则回退 http
        try:
            results = await crawl_playwright()
        except Exception as e:
            if opt.verbose:
                print(f"[warn] playwright engine failed, fallback to http. err={e}")
            results = await _crawl_via_http(opt, urls)

    # 3) 生成索引
    write_index(opt.out_dir, results, title="Docs Index")
    return results
