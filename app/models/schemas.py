"""Pydantic schema cho request/response của service."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body của POST /chat."""

    message: str = Field(..., min_length=1, description="Câu hỏi của người dùng.")
    session_id: str = Field(..., min_length=1, description="Id phiên chat (dùng chatId).")


class ReferencedProduct(BaseModel):
    """Sản phẩm được tham chiếu, trả về cho app hiển thị card."""

    id: str
    title: str
    price: float
    image: str


class ChatResponse(BaseModel):
    """Response của POST /chat."""

    answer: str
    referenced_products: list[ReferencedProduct] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Response của GET /health."""

    status: str = "ok"
