"""Kiểm tra Google API key còn dùng được không.

Chạy: python -m app.scripts.check_api_key
"""

import google.generativeai as genai

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    genai.configure(api_key=settings.google_api_key)

    print("Đang kiểm tra API key...\n")

    # 1) Thử list models -> key sai/hết hạn sẽ ném lỗi ngay tại đây.
    models = [m.name for m in genai.list_models()]
    print(f"✓ Key hợp lệ. Truy cập được {len(models)} model.")

    # 2) Thử gọi generate + embed như service thực tế đang dùng.
    chat_model = genai.GenerativeModel(settings.gemini_model)
    resp = chat_model.generate_content("ping")
    print(f"✓ Model chat '{settings.gemini_model}' hoạt động (trả về {len(resp.text)} ký tự).")

    emb = genai.embed_content(
        model=settings.embedding_model,
        content="ping",
        task_type="retrieval_query",
    )
    print(f"✓ Model embedding '{settings.embedding_model}' hoạt động (vector {len(emb['embedding'])} chiều).")

    # 3) Thống kê token của lần gọi vừa rồi (nếu API trả về).
    usage = getattr(resp, "usage_metadata", None)
    if usage:
        print(
            f"\nToken lần gọi thử: prompt={usage.prompt_token_count}, "
            f"output={usage.candidates_token_count}, total={usage.total_token_count}"
        )


if __name__ == "__main__":
    main()
