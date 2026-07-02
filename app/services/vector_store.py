"""Wrapper ChromaDB cho vector search sản phẩm.

Interface tách biệt để sau này có thể đổi backend (vd: Firestore Vector Search)
mà không phải sửa các nơi gọi: chỉ cần giữ nguyên `upsert` và `query`.
"""

from typing import Any

import chromadb

from app.config import get_settings
from app.services.embedding import embed_documents, embed_text

COLLECTION_NAME = "products"

_client: chromadb.ClientAPI | None = None


def _get_collection() -> chromadb.Collection:
    """Lấy (hoặc tạo) collection ChromaDB đã persist."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=get_settings().chroma_dir)
    # Không dùng embedding function của Chroma — ta tự tạo embedding bằng Google.
    return _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert(items: list[dict[str, Any]]) -> None:
    """Thêm/cập nhật sản phẩm vào vector store.

    Mỗi item:
      {
        "id": int,
        "text": str,                # text để embed
        "metadata": {title, price, image, category}
      }
    """
    if not items:
        return

    collection = _get_collection()

    ids = [str(item["id"]) for item in items]
    texts = [item["text"] for item in items]
    metadatas = [_normalize_metadata(item["id"], item["metadata"]) for item in items]
    embeddings = embed_documents(texts)

    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)


def query(text: str, top_k: int) -> list[dict[str, Any]]:
    """Trả về các sản phẩm gần nhất với `text`, kèm metadata.

    Kết quả mỗi phần tử: {id, title, price, image, category}.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    query_embedding = embed_text(text, task_type="retrieval_query")
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    metadatas = result.get("metadatas") or [[]]
    return [dict(meta) for meta in metadatas[0]]


def count() -> int:
    """Số lượng item hiện có trong collection."""
    return _get_collection().count()


def _normalize_metadata(product_id: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    """Chuẩn hoá metadata về đúng kiểu ChromaDB chấp nhận (str/int/float/bool)."""
    return {
        "id": int(product_id),
        "title": str(metadata.get("title", "")),
        "price": float(metadata.get("price", 0) or 0),
        "image": str(metadata.get("image", "")),
        "category": str(metadata.get("category", "")),
    }
