"""Job đồng bộ Firestore `products` -> ChromaDB.

Chạy: `python -m app.scripts.index_products`
"""

from typing import Any

from app.firebase_init import init_firebase
from app.services import vector_store
from app.services.firestore_client import fetch_all_products

# Chroma upsert theo lô để tránh gọi embedding quá lớn một lần.
BATCH_SIZE = 50


def _build_index_text(product: dict[str, Any]) -> str:
    """Ghép title + description + category thành text để embed."""
    return " ".join(
        part
        for part in (
            product.get("title", ""),
            product.get("description", ""),
            product.get("category", ""),
        )
        if part
    ).strip()


def main() -> None:
    init_firebase()

    products = fetch_all_products()
    print(f"Đọc được {len(products)} sản phẩm từ Firestore.")
    if not products:
        print("Không có sản phẩm nào để index.")
        return

    total = 0
    for start in range(0, len(products), BATCH_SIZE):
        batch = products[start : start + BATCH_SIZE]
        items = [
            {
                "id": p["id"],
                "text": _build_index_text(p),
                "metadata": {
                    "title": p["title"],
                    "price": p["price"],
                    "image": p["image"],
                    "category": p["category"],
                },
            }
            for p in batch
        ]
        vector_store.upsert(items)
        total += len(items)
        print(f"  Đã index {total}/{len(products)}...")

    print(f"Hoàn tất. Tổng số item trong vector store: {vector_store.count()}")


if __name__ == "__main__":
    main()
