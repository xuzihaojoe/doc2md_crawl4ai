from __future__ import annotations

from dataclasses import dataclass

from .config import settings


@dataclass(frozen=True)
class QiniuUploadResult:
    key: str
    url: str


def is_qiniu_enabled() -> bool:
    return bool(
        settings.qiniu_enabled
        and settings.qiniu_access_key
        and settings.qiniu_secret_key
        and settings.qiniu_bucket
        and settings.qiniu_public_domain
    )


def upload_markdown_text(*, key: str, text: str) -> QiniuUploadResult | None:
    """
    上传 Markdown 文本到七牛云（可选）。
    - 若未配置（qiniu_enabled=false 或缺少字段），返回 None
    """
    if not is_qiniu_enabled():
        return None

    # 延迟 import，避免用户不启用七牛时也要求安装依赖/触发错误
    from qiniu import Auth, put_data  # type: ignore

    auth = Auth(settings.qiniu_access_key, settings.qiniu_secret_key)
    token = auth.upload_token(settings.qiniu_bucket, key)
    ret, info = put_data(token, key, text.encode("utf-8"))
    if info.status_code >= 400:
        raise RuntimeError(f"qiniu upload failed: {info}")

    public_domain = settings.qiniu_public_domain.rstrip("/")
    return QiniuUploadResult(key=key, url=f"{public_domain}/{key}")

