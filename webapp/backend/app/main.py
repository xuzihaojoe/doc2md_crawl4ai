from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
import io
import re
import zipfile
from urllib.parse import urlparse, urlunparse

from .auth import hash_password, verify_password
from .config import settings
from .crawler_runner import run_crawl_job_in_thread
from .db import Base, SessionLocal, engine, get_db
from .deps import Owner, get_current_user, get_owner
from .models import CrawlJob, Document, User
from .schemas import (
    AuthLoginIn,
    AuthRegisterIn,
    CrawlCreateIn,
    CrawlJobOut,
    DocumentDetailOut,
    DocumentOut,
    UserOut,
)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

_FILENAME_BAD = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_filename(name: str, default: str = "file") -> str:
    name = (name or "").strip()
    if not name:
        name = default
    name = _FILENAME_BAD.sub("-", name).strip("-") or default
    return name


def _normalize_url_no_fragment(url: str) -> str:
    """
    与 doc2md_crawl4ai.discovery 的 _normalize_url 保持一致：去掉 fragment，保留 query。
    """
    p = urlparse(url)
    p = p._replace(fragment="")
    return urlunparse(p)


def _default_include_pattern(start_url: str) -> str:
    """
    默认把抓取范围限制在 start_url 对应的“目录/页面”下，避免爬到同级/全站。

    规则（与前端提示一致）：
    - URL 以 / 结尾：抓取该目录下所有页面（按目录前缀匹配）
      https://a.com/x/y/  ->  ^https://a\.com/x/y/
    - URL 不以 / 结尾：默认只抓取当前页面（更安全）
      https://a.com/x/y   ->  ^https://a\.com/x/y/?$
      （这里允许可选的 /，兼容部分站点会把 /y 重定向到 /y/ 的情况）
    """
    norm = _normalize_url_no_fragment(start_url).strip()
    if not norm:
        return ""

    p = urlparse(norm)
    base = f"{p.scheme}://{p.netloc}{p.path}"

    # 以 / 结尾：抓目录
    if base.endswith("/"):
        return "^" + re.escape(base)

    # 不以 / 结尾：抓当前页（允许可选 / 以兼容重定向）
    return "^" + re.escape(base) + "/?$"


app = FastAPI(title=settings.app_name)

app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_allow_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    Base.metadata.create_all(bind=engine)


# -------------------- Auth --------------------
@app.get("/api/auth/me", response_model=UserOut | None)
def auth_me(user: User | None = Depends(get_current_user)) -> UserOut | None:
    if not user:
        return None
    return UserOut(id=user.id, username=user.username)


@app.post("/api/auth/register", response_model=UserOut)
def auth_register(payload: AuthRegisterIn, request: Request, db: Session = Depends(get_db)) -> UserOut:
    exists = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    return UserOut(id=user.id, username=user.username)


@app.post("/api/auth/login", response_model=UserOut)
def auth_login(payload: AuthLoginIn, request: Request, db: Session = Depends(get_db)) -> UserOut:
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    request.session["user_id"] = user.id
    return UserOut(id=user.id, username=user.username)


@app.post("/api/auth/logout")
def auth_logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


# -------------------- Crawl Jobs --------------------
@app.post("/api/crawls", response_model=CrawlJobOut)
def create_crawl(payload: CrawlCreateIn, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> CrawlJobOut:
    # 默认 include：限制在 start_url 对应目录，避免爬到同级页面
    include = payload.include
    if not include:
        include = _default_include_pattern(payload.start_url)

    job = CrawlJob(
        name=payload.name,
        start_url=payload.start_url,
        status="pending",
        created_at=_utcnow(),
        user_id=owner.user.id if owner.user else None,
        anon_id=owner.anon_id if owner.anon_id else None,
        max_pages=payload.max_pages or settings.crawl_max_pages_default,
        concurrency=payload.concurrency or settings.crawl_concurrency_default,
        delay=payload.delay if payload.delay is not None else settings.crawl_delay_default,
        engine=payload.engine or settings.crawl_engine_default,
        scope=payload.scope or "same_origin",
        include=include,
        exclude=payload.exclude,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 后台执行
    run_crawl_job_in_thread(db_factory=SessionLocal, job_id=job.id)

    return CrawlJobOut(
        id=job.id,
        name=job.name,
        start_url=job.start_url,
        status=job.status,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@app.get("/api/crawls", response_model=list[CrawlJobOut])
def list_crawls(owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> list[CrawlJobOut]:
    q = select(CrawlJob).order_by(CrawlJob.created_at.desc())
    if owner.user:
        q = q.where(CrawlJob.user_id == owner.user.id)
    else:
        q = q.where(CrawlJob.anon_id == owner.anon_id)
    jobs = db.execute(q).scalars().all()
    return [
        CrawlJobOut(
            id=j.id,
            name=j.name,
            start_url=j.start_url,
            status=j.status,
            error=j.error,
            created_at=j.created_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


def _require_job_owner(db: Session, owner: Owner, job_id: str) -> CrawlJob:
    job = db.get(CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if owner.user and job.user_id == owner.user.id:
        return job
    if owner.anon_id and job.anon_id == owner.anon_id:
        return job
    raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/api/crawls/{job_id}", response_model=CrawlJobOut)
def get_crawl(job_id: str, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> CrawlJobOut:
    j = _require_job_owner(db, owner, job_id)
    return CrawlJobOut(
        id=j.id,
        name=j.name,
        start_url=j.start_url,
        status=j.status,
        error=j.error,
        created_at=j.created_at,
        finished_at=j.finished_at,
    )


@app.get("/api/crawls/{job_id}/documents", response_model=list[DocumentOut])
def list_documents(job_id: str, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> list[DocumentOut]:
    _require_job_owner(db, owner, job_id)
    docs = (
        db.execute(select(Document).where(Document.job_id == job_id).order_by(Document.is_merged.asc(), Document.doc_index.asc()))
        .scalars()
        .all()
    )
    return [
        DocumentOut(
            id=d.id,
            job_id=d.job_id,
            title=d.title,
            url=d.url,
            doc_index=d.doc_index,
            is_merged=d.is_merged,
            qiniu_url=d.qiniu_url,
            created_at=d.created_at,
        )
        for d in docs
    ]


def _require_doc_owner(db: Session, owner: Owner, doc_id: int) -> Document:
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    job = db.get(CrawlJob, d.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if owner.user and job.user_id == owner.user.id:
        return d
    if owner.anon_id and job.anon_id == owner.anon_id:
        return d
    raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/api/documents/{doc_id}", response_model=DocumentDetailOut)
def get_document(doc_id: int, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> DocumentDetailOut:
    d = _require_doc_owner(db, owner, doc_id)
    return DocumentDetailOut(
        id=d.id,
        job_id=d.job_id,
        title=d.title,
        url=d.url,
        doc_index=d.doc_index,
        is_merged=d.is_merged,
        qiniu_url=d.qiniu_url,
        created_at=d.created_at,
        markdown_text=d.markdown_text,
    )


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> dict:
    d = _require_doc_owner(db, owner, doc_id)
    db.delete(d)
    db.commit()
    return {"ok": True}


@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: int, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> StreamingResponse:
    d = _require_doc_owner(db, owner, doc_id)
    filename = _safe_filename(d.title or "document") + ".md"

    def iterfile():
        yield d.markdown_text.encode("utf-8")

    return StreamingResponse(
        iterfile(),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/crawls/{job_id}")
def delete_crawl(job_id: str, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> dict:
    job = _require_job_owner(db, owner, job_id)
    # ORM 级联删除 documents（relationship 已设置 cascade）
    db.delete(job)
    db.commit()
    return {"ok": True}


@app.get("/api/crawls/{job_id}/download.zip")
def download_crawl_zip(job_id: str, owner: Owner = Depends(get_owner), db: Session = Depends(get_db)) -> StreamingResponse:
    job = _require_job_owner(db, owner, job_id)
    docs = (
        db.execute(
            select(Document).where(Document.job_id == job_id).order_by(Document.is_merged.asc(), Document.doc_index.asc())
        )
        .scalars()
        .all()
    )

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 一个简单 README
        zf.writestr(
            "README.txt",
            f"doc2md export\n\njob_id: {job.id}\nstart_url: {job.start_url}\ncreated_at: {job.created_at}\n",
        )
        for d in docs:
            if d.is_merged:
                name = "merged.md"
            else:
                name = f"pages/{d.doc_index:05d}-{_safe_filename(d.title, 'page')}.md"
            zf.writestr(name, d.markdown_text or "")

    mem.seek(0)
    zip_name = _safe_filename("job-" + job.id) + ".zip"

    def iterfile():
        yield mem.getvalue()

    return StreamingResponse(
        iterfile(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


# -------------------- Frontend static (build 后) --------------------
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
