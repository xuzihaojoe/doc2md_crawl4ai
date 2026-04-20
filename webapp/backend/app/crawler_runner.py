from __future__ import annotations

import asyncio
import datetime as dt
import re
import tempfile
import threading
from pathlib import Path

from sqlalchemy.orm import Session

from doc2md_crawl4ai.crawler import CrawlOptions, crawl_site
from doc2md_crawl4ai.writer import bundle_markdown

from .config import settings
from .models import CrawlJob, Document
from .qiniu_uploader import upload_markdown_text


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _title_from_md_path(md_path: Path) -> str:
    # md_path = .../<something>/index.md
    parent = md_path.parent.name
    if parent.lower().endswith(".html"):
        parent = parent[:-5]
    return parent or "index"


def _qiniu_key_for(job_id: str, doc_index: int, title: str) -> str:
    safe_title = "".join([c if c.isalnum() or c in ("-", "_") else "-" for c in title]).strip("-") or "doc"
    prefix = settings.qiniu_key_prefix.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return f"{prefix}{job_id}/{doc_index:05d}-{safe_title}.md"


def run_crawl_job_in_thread(*, db_factory, job_id: str) -> None:
    """
    后台线程入口：抓取 -> 写入 DB ->（可选）上传七牛 -> 生成 merged.md 并入库。

    db_factory: 一个无参函数，返回 Session（避免跨线程复用同一个 Session）。
    """

    def _worker():
        db: Session = db_factory()
        try:
            _run(db=db, job_id=job_id)
        finally:
            db.close()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _run(*, db: Session, job_id: str) -> None:
    job = db.get(CrawlJob, job_id)
    if not job:
        return

    job.status = "running"
    job.error = None
    db.commit()

    out_dir = Path(tempfile.mkdtemp(prefix=f"doc2md_{job_id}_"))

    try:
        include_re = re.compile(job.include) if job.include else None
        exclude_re = re.compile(job.exclude) if job.exclude else None
        opts = CrawlOptions(
            start_url=job.start_url,
            out_dir=out_dir,
            max_pages=job.max_pages,
            concurrency=job.concurrency,
            delay=job.delay,
            scope=job.scope,
            include_re=include_re,
            exclude_re=exclude_re,
            ignore_links=False,
            engine=job.engine,
            main_selector="",
            use_fit_markdown=False,
            verbose=False,
        )

        results = asyncio.run(crawl_site(opts))

        # 逐页入库
        docs: list[Document] = []
        for idx, wr in enumerate(sorted(results, key=lambda x: x.file_path.as_posix())):
            md_path = Path(wr.file_path)
            try:
                md_text = md_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                md_text = md_path.read_text(encoding="utf-8", errors="ignore")

            title = _title_from_md_path(md_path)
            qiniu_key = None
            qiniu_url = None
            try:
                up = upload_markdown_text(key=_qiniu_key_for(job_id, idx, title), text=md_text)
                if up:
                    qiniu_key, qiniu_url = up.key, up.url
            except Exception:
                # 七牛失败不影响主流程
                pass

            doc = Document(
                job_id=job_id,
                title=title,
                url=wr.url,
                doc_index=idx,
                is_merged=False,
                markdown_text=md_text,
                qiniu_key=qiniu_key,
                qiniu_url=qiniu_url,
            )
            docs.append(doc)
            db.add(doc)

        # merged.md
        merged_path = out_dir / "merged.md"
        bundle_markdown(out_dir, merged_path, doc_title=job.start_url, title_mode="basename")
        merged_text = merged_path.read_text(encoding="utf-8", errors="ignore")
        merged_qiniu_key = None
        merged_qiniu_url = None
        try:
            up = upload_markdown_text(key=_qiniu_key_for(job_id, 999999, "merged"), text=merged_text)
            if up:
                merged_qiniu_key, merged_qiniu_url = up.key, up.url
        except Exception:
            pass

        db.add(
            Document(
                job_id=job_id,
                title="merged",
                url=job.start_url,
                doc_index=len(docs),
                is_merged=True,
                markdown_text=merged_text,
                qiniu_key=merged_qiniu_key,
                qiniu_url=merged_qiniu_url,
            )
        )

        job.status = "succeeded"
        job.finished_at = _utcnow()
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.finished_at = _utcnow()
        db.commit()
