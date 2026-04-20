from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    username: str


class AuthRegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)


class AuthLoginIn(BaseModel):
    username: str
    password: str


class CrawlCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="任务名称")
    start_url: str
    max_pages: int | None = None
    concurrency: int | None = None
    delay: float | None = None
    engine: str | None = None  # http|playwright|auto
    scope: str | None = None  # same_origin|same_domain
    include: str | None = None
    exclude: str | None = None


class CrawlJobOut(BaseModel):
    id: str
    name: str
    start_url: str
    status: str
    error: str | None
    created_at: dt.datetime
    finished_at: dt.datetime | None


class DocumentOut(BaseModel):
    id: int
    job_id: str
    title: str
    url: str
    doc_index: int
    is_merged: bool
    qiniu_url: str | None
    created_at: dt.datetime


class DocumentDetailOut(DocumentOut):
    markdown_text: str

