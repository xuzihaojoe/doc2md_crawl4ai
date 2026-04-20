import argparse
import asyncio
import re
from pathlib import Path

from .crawler import CrawlOptions, crawl_site
from .writer import bundle_markdown


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="doc2md_crawl4ai",
        description="输入文档入口 URL，自动发现同域页面并保存为本地 Markdown（基于 Crawl4AI）。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    crawl = sub.add_parser("crawl", help="从入口页开始递归发现页面并抓取为 Markdown")
    crawl.add_argument("--start-url", required=True, help="文档站入口页 URL（通常是目录树首页）")
    crawl.add_argument("--out", required=True, help="输出目录（会创建）")
    crawl.add_argument("--max-pages", type=int, default=200, help="最多抓取页数（默认 200）")
    crawl.add_argument("--concurrency", type=int, default=6, help="并发抓取数（默认 6）")
    crawl.add_argument("--delay", type=float, default=0.0, help="每批抓取后的延迟秒数（默认 0）")
    crawl.add_argument(
        "--scope",
        choices=["same_origin", "same_domain"],
        default="same_origin",
        help="URL 限制范围（默认 same_origin）",
    )
    crawl.add_argument(
        "--include",
        default="",
        help="仅包含匹配该正则的 URL（可选）",
    )
    crawl.add_argument(
        "--exclude",
        default="",
        help="排除匹配该正则的 URL（可选）",
    )
    crawl.add_argument(
        "--ignore-links",
        action="store_true",
        help="Markdown 输出忽略超链接（减少噪音）",
    )
    crawl.add_argument(
        "--engine",
        choices=["auto", "playwright", "http"],
        default="auto",
        help=(
            "抓取引擎：auto=优先 playwright，失败则回退 http；"
            "playwright=浏览器渲染（可处理动态页面）；"
            "http=仅请求 HTML 再用 Crawl4AI 的 Markdown 生成器转换（更轻量）"
        ),
    )
    crawl.add_argument(
        "--main-selector",
        default="",
        help=(
            "可选：只抽取页面某个主内容区域再转 Markdown（CSS selector）。"
            "例如很多文档站用 main/article 或 .markdown/.content。"
        ),
    )
    crawl.add_argument(
        "--use-fit-markdown",
        action="store_true",
        help="保存 fit_markdown（需要配合内容过滤器；默认保存 raw_markdown）",
    )
    crawl.add_argument(
        "--verbose",
        action="store_true",
        help="输出更详细的日志",
    )

    bundle = sub.add_parser("bundle", help="把输出目录里的多个页面 Markdown 合并为单个 Markdown")
    bundle.add_argument("--in", dest="in_dir", required=True, help="crawl 输出目录（例如 ./out_uniapp_uts）")
    bundle.add_argument(
        "--out",
        default="",
        help="输出的合并 Markdown 文件路径（默认：<in>/merged.md）",
    )
    bundle.add_argument("--doc-title", default="Merged Docs", help="合并文档的主标题")
    bundle.add_argument(
        "--title-mode",
        choices=["basename", "breadcrumb"],
        default="basename",
        help="章节标题规则：basename=只用最后一级目录名；breadcrumb=用完整路径拼接",
    )
    bundle.add_argument(
        "--no-separator",
        action="store_true",
        help="不在每个章节末尾插入分隔线（---）",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "crawl":
        out_dir = Path(args.out).expanduser().resolve()
        include_re = re.compile(args.include) if args.include else None
        exclude_re = re.compile(args.exclude) if args.exclude else None

        opts = CrawlOptions(
            start_url=args.start_url,
            out_dir=out_dir,
            max_pages=args.max_pages,
            concurrency=args.concurrency,
            delay=args.delay,
            scope=args.scope,
            include_re=include_re,
            exclude_re=exclude_re,
            ignore_links=args.ignore_links,
            engine=args.engine,
            main_selector=args.main_selector,
            use_fit_markdown=args.use_fit_markdown,
            verbose=args.verbose,
        )
        asyncio.run(crawl_site(opts))
        return 0

    if args.command == "bundle":
        in_dir = Path(args.in_dir).expanduser().resolve()
        out_file = Path(args.out).expanduser().resolve() if args.out else (in_dir / "merged.md")
        bundle_markdown(
            in_dir,
            out_file,
            doc_title=args.doc_title,
            title_mode=args.title_mode,
            add_separator=not bool(args.no_separator),
        )
        print(f"[bundle] wrote: {out_file}")
        return 0

    parser.error("Unknown command")
    return 2
