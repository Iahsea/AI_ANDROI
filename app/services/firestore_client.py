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
        # Dùng cho kiểm quyền khi index (sellerId == uid). Có thể rỗng nếu doc cũ.
        "sellerId": str(data.get("sellerId", "")),
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


def fetch_product(product_id: str) -> dict[str, Any] | None:
    """Đọc một sản phẩm `products/{id}` từ Firestore, đã chuẩn hoá.

    Trả về None nếu document không tồn tại (hoặc thiếu trường bắt buộc).
    """
    db = firestore.client()
    doc = db.collection(PRODUCTS_COLLECTION).document(product_id).get()
    if not doc.exists:
        return None
    return _to_product_dict(doc)


def build_index_text(product: dict[str, Any]) -> str:
    """Ghép title + description + category thành text để embed.

    Nguồn sự thật duy nhất cho cách ghép text; dùng chung giữa job re-index toàn bộ
    (`index_products`) và endpoint sync để không lệch không gian vector.
    """
    return " ".join(
        part
        for part in (
            product.get("title", ""),
            product.get("description", ""),
            product.get("category", ""),
        )
        if part
    ).strip()
