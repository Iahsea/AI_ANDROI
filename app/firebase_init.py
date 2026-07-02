"""Khởi tạo firebase-admin (dùng chung cho server và script)."""

import os

import firebase_admin
from firebase_admin import credentials

from app.config import get_settings


def init_firebase() -> None:
    """Khởi tạo firebase-admin nếu chưa init.

    Ưu tiên FIREBASE_SERVICE_ACCOUNT_PATH; nếu không có (hoặc file không tồn tại)
    thì fallback về Application Default Credentials (vd: Cloud Run).
    """
    if firebase_admin._apps:  # đã init rồi
        return

    path = get_settings().firebase_service_account_path
    if path and os.path.isfile(path):
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
    else:
        # ADC: đọc từ GOOGLE_APPLICATION_CREDENTIALS hoặc môi trường Google Cloud.
        firebase_admin.initialize_app()
