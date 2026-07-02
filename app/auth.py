"""Dependency FastAPI: verify Firebase ID token, trả về uid."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

_bearer = HTTPBearer(auto_error=False)


def get_current_uid(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Đọc header `Authorization: Bearer <token>`, verify và trả về uid.

    Lỗi (thiếu token / token không hợp lệ) -> HTTP 401.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        decoded = firebase_auth.verify_id_token(credentials.credentials)
    except Exception as exc:  # firebase-admin ném nhiều loại lỗi khác nhau
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return decoded["uid"]
