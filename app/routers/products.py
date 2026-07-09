"""Router: sync sản phẩm Firestore -> ChromaDB.

Hợp đồng do team Android bàn giao (xem INTEGRATION_PRODUCT_SYNC.md):
  - POST   /products/index       -> thêm mới / cập nhật (upsert) vector.
  - DELETE /products/index/{id}  -> xóa vector (idempotent).

Xác thực y hệt /chat (Firebase ID token). App chỉ gửi `id`; service tự đọc lại
`products/{id}` từ Firestore rồi embed **đúng cùng cách** với `index_products`.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, is_admin
from app.models.schemas import ProductSyncRequest, SyncResponse
from app.services import firestore_client, vector_store

router = APIRouter(prefix="/products", tags=["products"])


def _ensure_can_write(product: dict[str, Any], user: dict[str, Any]) -> None:
    """Kiểm quyền: chỉ chủ sản phẩm (sellerId == uid) hoặc admin mới được index.

    Nếu doc không có sellerId (dữ liệu cũ) thì không chặn — không đủ dữ kiện để
    xác định chủ sở hữu, và luồng app luôn ghi Firestore trước với đúng chủ.
    """
    seller_id = product.get("sellerId", "")
    if not seller_id or seller_id == user["uid"] or is_admin(user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền.")


@router.post("/index", response_model=SyncResponse)
def index_product(
    payload: ProductSyncRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> SyncResponse:
    """Đọc lại `products/{id}` từ Firestore, embed và upsert vào ChromaDB."""
    product = firestore_client.fetch_product(payload.id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sản phẩm.",
        )

    _ensure_can_write(product, user)

    vector_store.upsert(
        [
            {
                "id": product["id"],
                "text": firestore_client.build_index_text(product),
                "metadata": {
                    "title": product["title"],
                    "price": product["price"],
                    "image": product["image"],
                    "category": product["category"],
                },
            }
        ]
    )

    return SyncResponse(id=product["id"])


@router.delete("/index/{id}", response_model=SyncResponse)
def delete_product_index(
    id: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> SyncResponse:
    """Xóa vector khỏi ChromaDB. Idempotent: id không tồn tại vẫn trả 200.

    Lưu ý: app xóa Firestore TRƯỚC rồi mới gọi endpoint này, nên `products/{id}`
    đã biến mất -> không thể đọc sellerId để kiểm quyền chủ sở hữu như khi index.
    Vì vậy delete chỉ yêu cầu token hợp lệ (thao tác idempotent, không rò rỉ dữ liệu).
    """
    vector_store.delete([id])
    return SyncResponse(id=id)
