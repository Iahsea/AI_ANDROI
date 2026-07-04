"""Truy cập Firestore: đọc collection `products`."""

from typing import Any

from firebase_admin import firestore

PRODUCTS_COLLECTION = "products"


def _to_product_dict(doc: Any) -> dict[str, Any] | None:
    """Chuẩn hoá một Firestore document thành dict sản phẩm.

    Trả về None nếu document thiếu trường bắt buộc (id/title).
    """
    data = doc.to_dict() or {}

    raw_id = data.get("id", doc.id)
    title = data.get("title")
    if raw_id is None or title is None:
        return None

    return {
        "id": str(raw_id),
        "title": str(title),
        "description": str(data.get("description", "")),
        "category": str(data.get("category", "")),
        "price": float(data.get("price", 0) or 0),
        "image": str(data.get("image", "")),
    }


def fetch_all_products() -> list[dict[str, Any]]:
    """Đọc toàn bộ sản phẩm từ Firestore, đã chuẩn hoá."""
    db = firestore.client()
    docs = db.collection(PRODUCTS_COLLECTION).stream()

    products: list[dict[str, Any]] = []
    for doc in docs:
        product = _to_product_dict(doc)
        if product is not None:
            products.append(product)
    return products
