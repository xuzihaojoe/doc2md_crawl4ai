from __future__ import annotations

from passlib.context import CryptContext

# 注意：bcrypt 在不同版本组合下可能触发 72 bytes 限制/兼容性问题。
# 这里改用 pbkdf2_sha256（纯 Python + 更稳定），满足“最简单用户名+密码”需求。
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
