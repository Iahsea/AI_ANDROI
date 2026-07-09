"""Dependency FastAPI: verify Firebase ID token, trả về uid / claims."""

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Đọc header `Authorization: Bearer <token>`, verify và trả về token đã decode.

    Trả về dict claims (gồm `uid` và các custom claim như `role`/`admin`).
    Lỗi (thiếu token / token không hợp lệ) -> HTTP 401.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return firebase_auth.verify_id_token(credentials.credentials)
    except Exception as exc:  # firebase-admin ném nhiều loại lỗi khác nhau
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_uid(
    user: dict[str, Any] = Depends(get_current_user),
) -> str:
    """Verify token và trả về uid. Lỗi -> HTTP 401."""
    return user["uid"]


def is_admin(user: dict[str, Any]) -> bool:
    """User có phải admin không (dựa vào custom claim của Firebase)."""
    return user.get("admin") is True or user.get("role") == "admin"
