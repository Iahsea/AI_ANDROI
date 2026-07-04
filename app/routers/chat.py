"""Router: POST /chat và GET /health."""

from fastapi import APIRouter, Depends

from app.auth import get_current_uid
from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ReferencedProduct,
)
from app.services import llm, vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check đơn giản."""
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    _uid: str = Depends(get_current_uid),
) -> ChatResponse:
    """Nhận câu hỏi -> vector search -> gọi LLM -> trả lời kèm sản phẩm."""
    top_k = get_settings().top_k

    products = vector_store.query(payload.message, top_k=top_k)
    answer = llm.generate_answer(payload.message, products)

    referenced = [
        ReferencedProduct(
            id=str(p["id"]),
            title=str(p.get("title", "")),
            price=float(p.get("price", 0) or 0),
            image=str(p.get("image", "")),
        )
        for p in products
    ]

    return ChatResponse(answer=answer, referenced_products=referenced)
