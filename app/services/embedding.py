"""Tạo embedding cho text bằng Google Generative AI (text-embedding-004)."""

import google.generativeai as genai

from app.config import get_settings

EMBEDDING_MODEL = "models/text-embedding-004"

_configured = False


def _ensure_configured() -> None:
    """Cấu hình API key cho SDK (chỉ chạy một lần)."""
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().google_api_key)
        _configured = True


def embed_text(text: str, *, task_type: str = "retrieval_query") -> list[float]:
    """Tạo embedding cho một đoạn text.

    task_type:
      - "retrieval_document" khi index sản phẩm (lưu vào vector store).
      - "retrieval_query" khi embed câu hỏi của người dùng.
    """
    _ensure_configured()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
    )
    return list(result["embedding"])


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Tạo embedding cho nhiều document (dùng khi index sản phẩm)."""
    _ensure_configured()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=texts,
        task_type="retrieval_document",
    )
    return [list(vec) for vec in result["embedding"]]
