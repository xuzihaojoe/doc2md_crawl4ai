from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    jobs: Mapped[list["CrawlJob"]] = relationship(back_populates="user")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 任务名称
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")  # pending|running|succeeded|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 任务参数（便于回看/复现）
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    delay: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    engine: Mapped[str] = mapped_column(String(24), nullable=False, default="http")  # http|playwright|auto
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default="same_origin")
    include: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclude: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    anon_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="jobs")
    documents: Mapped[list["Document"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("crawl_jobs.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    doc_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    markdown_text: Mapped[str] = mapped_column(Text().with_variant(LONGTEXT, "mysql"), nullable=False)

    qiniu_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    qiniu_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    job: Mapped["CrawlJob"] = relationship(back_populates="documents")
