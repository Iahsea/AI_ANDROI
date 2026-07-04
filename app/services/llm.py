"""Build prompt và gọi Gemini để sinh câu trả lời dựa trên sản phẩm."""

from typing import Any

import google.generativeai as genai

from app.config import get_settings

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý bán hàng thân thiện. Danh sách sản phẩm bên dưới đã được chọn sẵn là "
    "liên quan tới câu hỏi của khách. Hãy dựa vào danh sách này để tư vấn ngắn gọn bằng "
    "tiếng Việt, giới thiệu các sản phẩm phù hợp kèm giá. "
    "Nếu (và chỉ nếu) danh sách rỗng thì nói thẳng là không tìm thấy sản phẩm phù hợp. "
    "Tuyệt đối không bịa ra sản phẩm ngoài danh sách."
)

_configured = False


def _ensure_configured() -> None:
    """Cấu hình API key cho SDK (chỉ chạy một lần)."""
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().google_api_key)
        _configured = True


def _build_context(products: list[dict[str, Any]]) -> str:
    """Ghép danh sách sản phẩm thành phần context cho prompt."""
    if not products:
        return "(Không có sản phẩm nào phù hợp.)"

    lines: list[str] = []
    for idx, p in enumerate(products, start=1):
        lines.append(
            f"{idx}. {p.get('title', '')} "
            f"| danh mục: {p.get('category', '')} "
            f"| giá: {p.get('price', 0)}"
        )
    return "\n".join(lines)


def generate_answer(message: str, products: list[dict[str, Any]]) -> str:
    """Sinh câu trả lời cho câu hỏi `message` dựa trên `products`."""
    _ensure_configured()

    model = genai.GenerativeModel(
        model_name=get_settings().gemini_model,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    prompt = (
        "Danh sách sản phẩm liên quan:\n"
        f"{_build_context(products)}\n\n"
        f"Câu hỏi của khách: {message}"
    )

    response = model.generate_content(prompt)
    return (response.text or "").strip()
