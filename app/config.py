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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Trả về singleton Settings (cache lại để không đọc env nhiều lần)."""
    return Settings()  # type: ignore[call-arg]
