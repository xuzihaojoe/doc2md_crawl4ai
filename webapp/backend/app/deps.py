from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if not user_id:
        return None
    return db.get(User, int(user_id))


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return user


def get_anon_id(x_anonymous_id: str | None = Header(default=None, alias="X-Anonymous-Id")) -> str | None:
    return x_anonymous_id


class Owner:
    def __init__(self, *, user: User | None, anon_id: str | None):
        self.user = user
        self.anon_id = anon_id


def get_owner(
    user: User | None = Depends(get_current_user),
    anon_id: str | None = Depends(get_anon_id),
) -> Owner:
    if user:
        return Owner(user=user, anon_id=None)
    if anon_id:
        return Owner(user=None, anon_id=anon_id)
    # 前端会自动生成 anon_id；如果连这个都没有，说明请求不合法
    raise HTTPException(status_code=400, detail="Missing X-Anonymous-Id")

