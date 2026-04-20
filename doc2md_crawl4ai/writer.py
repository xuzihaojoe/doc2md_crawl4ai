from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class WriteResult:
    file_path: Path
    url: str


_INVALID = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_segment(seg: str) -> str:
    seg = seg.strip()
    if not seg:
        return "index"
    seg = _INVALID.sub("-", seg).strip("-")
    return seg or "index"


def url_to_md_path(out_dir: Path, url: str) -> Path:
    """
    按 URL 路径分层保存：
      https://a.com/core/quickstart/  -> out/a.com/core/quickstart/index.md
      https://a.com/api/arun         -> out/a.com/api/arun/index.md
    """
    p = urlparse(url)
    host = _safe_segment(p.netloc)
    parts = [_safe_segment(x) for x in p.path.split("/") if x.strip()]

    # query 也可能区分页面（极少数文档站），简单拼进文件夹名
    if p.query:
        parts.append(_safe_segment(p.query))

    if not parts:
        parts = ["index"]

    # 统一落成目录 + index.md，避免后缀/重名问题
    dir_path = out_dir / host / Path(*parts)
    return dir_path / "index.md"


def write_markdown(out_dir: Path, url: str, markdown: str) -> WriteResult:
    md_path = url_to_md_path(out_dir, url)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    return WriteResult(file_path=md_path, url=url)


def write_index(out_dir: Path, items: list[WriteResult], title: str = "Crawled Docs Index") -> Path:
    idx = out_dir / "index.md"
    lines = [f"# {title}", ""]

    # 用相对路径链接
    for it in sorted(items, key=lambda x: x.file_path.as_posix()):
        rel = it.file_path.relative_to(out_dir).as_posix()
        lines.append(f"- [{it.url}]({rel})")

    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return idx


def _strip_html_suffix(seg: str) -> str:
    seg = seg.strip()
    return seg[:-5] if seg.lower().endswith(".html") else seg


def bundle_markdown(
    in_dir: Path,
    out_file: Path,
    *,
    doc_title: str = "Merged Docs",
    title_mode: str = "basename",  # basename | breadcrumb
    add_separator: bool = True,
) -> Path:
    """
    把爬取输出目录里的多个页面 Markdown 合并为单个 Markdown。

    约定：
    - 单页内容一般存为：<in_dir>/<host>/<path>/index.md
    - <in_dir>/index.md 通常是汇总索引文件，会被自动跳过

    标题规则：
    - basename：只用最后一级目录名作为标题（例如 class.html -> class）
    - breadcrumb：用完整路径拼接（例如 uni-app-x / uts / class）
    """
    in_dir = in_dir.expanduser().resolve()
    out_file = out_file.expanduser().resolve()
    if not in_dir.exists():
        raise FileNotFoundError(f"in_dir not found: {in_dir}")

    md_files = sorted(in_dir.rglob("index.md"), key=lambda p: p.as_posix())
    md_files = [p for p in md_files if p != (in_dir / "index.md")]

    lines: list[str] = [f"# {doc_title}", ""]
    lines.append(f"<!-- bundled_from: {in_dir.as_posix()} -->")
    lines.append("")

    used_titles: set[str] = set()

    for md_path in md_files:
        rel = md_path.relative_to(in_dir)
        parts = list(rel.parts[:-1])  # 去掉 index.md
        cleaned = [_strip_html_suffix(x) for x in parts]

        if not cleaned:
            title = "index"
        elif title_mode == "breadcrumb":
            title = " / ".join(cleaned)
        else:
            # basename：可能重名，重名时回退到 breadcrumb
            title = cleaned[-1]
            if title in used_titles and len(cleaned) > 1:
                title = " / ".join(cleaned[-2:])
            if title in used_titles:
                title = " / ".join(cleaned) or title

        used_titles.add(title)

        lines.append(f"## {title}")
        lines.append("")
        try:
            content = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = md_path.read_text(encoding="utf-8", errors="ignore")
        content = content.strip()
        lines.append(content)
        lines.append("")

        if add_separator:
            lines.append("---")
            lines.append("")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_file
