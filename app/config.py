"""Cấu hình service, đọc từ biến môi trường qua pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Toàn bộ biến môi trường của service."""

    # Google Generative AI
    google_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"

    # Firebase
    # Để trống -> dùng Application Default Credentials (vd: Cloud Run).
    firebase_service_account_path: str | None = None

    # Vector store
    chroma_dir: str = "./chroma_data"

    # RAG
    top_k: int = 5
    # Ngưỡng khoảng cách cosine tối đa để coi sản phẩm là "liên quan".
    # Vector xa hơn ngưỡng này bị loại (tránh trả sản phẩm rác khi không có gì khớp).
    # Đã hiệu chỉnh cho gemini-embedding-001 + dữ liệu hiện tại; chỉnh lại nếu đổi model.
    relevance_max_distance: float = 0.33

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Trả về singleton Settings (cache lại để không đọc env nhiều lần)."""
    return Settings()  # type: ignore[call-arg]
