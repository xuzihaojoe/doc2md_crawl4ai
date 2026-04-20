from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # ---------- App ----------
    app_name: str = "doc2md web"
    app_secret_key: str = "CHANGE_ME__PLEASE_SET_ENV"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---------- DB ----------
    # MySQL 示例：
    # mysql+pymysql://user:password@127.0.0.1:3306/doc2md?charset=utf8mb4
    database_url: str = "sqlite:///./dev.db"

    # ---------- Crawl default ----------
    crawl_max_pages_default: int = 200
    crawl_concurrency_default: int = 6
    crawl_delay_default: float = 0.2
    crawl_engine_default: str = "http"  # http | playwright | auto

    # ---------- Qiniu (可选) ----------
    qiniu_enabled: bool = False
    qiniu_access_key: str = ""
    qiniu_secret_key: str = ""
    qiniu_bucket: str = ""
    # 公网访问域名（例如 https://xxx.cdn.com ），用于拼接 qiniu_url
    qiniu_public_domain: str = ""
    # key 前缀，方便分目录（可空）
    qiniu_key_prefix: str = "doc2md/"


settings = Settings()

