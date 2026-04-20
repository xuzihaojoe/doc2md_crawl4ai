from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class DiscoveryOptions:
    start_url: str
    scope: str  # same_origin | same_domain
    include_re: re.Pattern[str] | None = None
    exclude_re: re.Pattern[str] | None = None
    verbose: bool = False
    user_agent: str = "doc2md-crawl4ai/0.1.0"
    timeout_s: int = 30


def _normalize_url(url: str) -> str:
    """
    轻量标准化：
    - 去掉 fragment
    - 保留 query（有些 docs 靠 query 区分页）
    """
    p = urlparse(url)
    p = p._replace(fragment="")
    return urlunparse(p)


def _is_in_scope(candidate: str, start: str, scope: str) -> bool:
    c = urlparse(candidate)
    s = urlparse(start)
    if scope == "same_domain":
        return (c.scheme in ("http", "https")) and (c.hostname is not None) and (
            s.hostname is not None
        ) and c.hostname.endswith(s.hostname)
    # same_origin
    return (
        c.scheme == s.scheme
        and c.hostname == s.hostname
        and (c.port or (443 if c.scheme == "https" else 80))
        == (s.port or (443 if s.scheme == "https" else 80))
    )


def _should_keep(url: str, opt: DiscoveryOptions) -> bool:
    if not _is_in_scope(url, opt.start_url, opt.scope):
        return False
    if opt.exclude_re and opt.exclude_re.search(url):
        return False
    if opt.include_re and not opt.include_re.search(url):
        return False
    return True


async def fetch_html(session: aiohttp.ClientSession, url: str, timeout_s: int) -> str | None:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_s)) as r:
            if r.status >= 400:
                return None
            return await r.text(errors="ignore")
    except Exception:
        return None


def extract_links(html: str, base_url: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    urls: set[str] = set()

    # 兼容常见“目录树”结构：a[href]
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        # 跳过一些明显不是文档页的链接
        if href.startswith("javascript:") or href.startswith("mailto:") or href.startswith(
            "tel:"
        ):
            continue
        abs_url = urljoin(base_url, href)
        abs_url = _normalize_url(abs_url)
        urls.add(abs_url)
    return urls


async def discover_urls(opt: DiscoveryOptions, max_pages: int) -> list[str]:
    """
    以 start_url 为起点，基于站内链接 BFS 发现 URL（适合文档站导航树）。
    说明：为了尽量通用，URL 发现阶段用 aiohttp 做轻量抓取；真正内容抓取交给 Crawl4AI。
    """
    start = _normalize_url(opt.start_url)
    seen: set[str] = set()
    q: list[str] = [start]
    out: list[str] = []

    headers = {"User-Agent": opt.user_agent}
    async with aiohttp.ClientSession(headers=headers) as session:
        while q and len(out) < max_pages:
            url = q.pop(0)
            if url in seen:
                continue
            seen.add(url)

            if not _should_keep(url, opt):
                continue

            html = await fetch_html(session, url, opt.timeout_s)
            if html is None:
                continue

            out.append(url)

            for link in extract_links(html, base_url=url):
                if link not in seen and _should_keep(link, opt):
                    q.append(link)

    return out


def chunked(items: Iterable[str], n: int) -> list[list[str]]:
    batch: list[str] = []
    out: list[list[str]] = []
    for it in items:
        batch.append(it)
        if len(batch) >= n:
            out.append(batch)
            batch = []
    if batch:
        out.append(batch)
    return out

