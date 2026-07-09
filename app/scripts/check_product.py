"""Tiện ích DEV: kiểm tra một sản phẩm đã có trong vector store (ChromaDB) chưa.

KHÔNG phải thành phần của service — chỉ dùng khi phát triển/thử nghiệm.

Cách dùng:
    python -m app.scripts.check_product [id ...]

- Không truyền id  -> chỉ in tổng số vector đang có trong collection.
- Truyền 1+ id     -> với mỗi id, in CÓ/KHÔNG và metadata (title/price/category...).

Dùng để verify sau khi app thêm/sửa/xóa sản phẩm: chạy lại script với id đó
để xem vector đã được upsert (CÓ) hay đã bị xóa (KHÔNG).
"""

import sys

# Console Windows mặc định là cp1252, không in được tiếng Việt -> ép UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services import vector_store


def main() -> None:
    ids = sys.argv[1:]

    total = vector_store.count()
    print(f"Tổng số vector trong collection '{vector_store.COLLECTION_NAME}': {total}")

    if not ids:
        print("(Không truyền id — chỉ in tổng số. Dùng: python -m app.scripts.check_product <id>)")
        return

    collection = vector_store._get_collection()
    result = collection.get(ids=ids, include=["metadatas"])

    found = {rid: meta for rid, meta in zip(result["ids"], result["metadatas"])}
    for rid in ids:
        if rid in found:
            print(f"  ✅ CÓ  {rid} -> {found[rid]}")
        else:
            print(f"  ❌ KHÔNG  {rid} (chưa index hoặc đã bị xóa)")


if __name__ == "__main__":
    main()
