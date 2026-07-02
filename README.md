# RAG Chatbot Service

Backend RAG (Python + FastAPI) làm chatbot hỏi đáp sản phẩm cho app bán hàng Android.
Service chạy độc lập, được app gọi qua HTTP. Chi tiết đặc tả xem [`PLAN.md`](./PLAN.md).

Luồng xử lý: câu hỏi → embedding (Google `text-embedding-004`) → vector search (ChromaDB) →
build prompt → sinh câu trả lời (Gemini) → trả về `answer` + danh sách sản phẩm tham chiếu.

## 1. Yêu cầu

- Python 3.11+ (khuyến nghị 3.12).
- Một **Firebase service account** (file JSON) có quyền đọc Firestore.
- **Google API key** (Google AI Studio, free tier): https://aistudio.google.com/apikey

## 2. Cài đặt

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Cấu hình

Copy `.env.example` thành `.env` rồi điền giá trị:

```bash
cp .env.example .env
```

| Biến                            | Bắt buộc | Mặc định            | Ghi chú                                   |
|---------------------------------|----------|---------------------|-------------------------------------------|
| `GOOGLE_API_KEY`                | ✅       | —                   | API key Google AI Studio.                 |
| `GEMINI_MODEL`                  | ❌       | `gemini-2.0-flash`  | Model sinh câu trả lời.                    |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | ❌       | —                   | Đường dẫn file JSON. Để trống → dùng ADC. |
| `CHROMA_DIR`                    | ❌       | `./chroma_data`     | Thư mục persist ChromaDB.                  |
| `TOP_K`                         | ❌       | `5`                 | Số sản phẩm gần nhất lấy ra.               |

> File service account JSON và `.env` **không được commit** (đã có trong `.gitignore`).

## 4. Index sản phẩm (Firestore → ChromaDB)

Trước khi hỏi đáp, cần index dữ liệu sản phẩm vào vector store:

```bash
python -m app.scripts.index_products
```

Chạy lại bất cứ khi nào dữ liệu `products` trên Firestore thay đổi (job dùng `upsert`
theo `id` nên chạy lại an toàn, không tạo bản trùng).

## 5. Chạy server

```bash
uvicorn app.main:app --reload --port 8080
```

- Swagger UI: http://localhost:8080/docs
- Health check: http://localhost:8080/health

## 6. Gọi thử `/chat`

Endpoint yêu cầu header `Authorization: Bearer <firebase_id_token>` (ID token do app
Android lấy từ Firebase Auth).

```bash
curl -X POST http://localhost:8080/chat \
  -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Có áo thun nam nào không?", "session_id": "demo-chat-1"}'
```

Response mẫu:

```json
{
  "answer": "Bên mình có ... phù hợp với nhu cầu của bạn.",
  "referenced_products": [
    { "id": 1, "title": "Áo thun nam", "price": 199000, "image": "https://..." }
  ]
}
```

## 7. Chạy bằng Docker

```bash
docker build -t rag-chatbot-service .
docker run -p 8080:8080 --env-file .env \
  -v "$(pwd)/service-account.json:/app/service-account.json" \
  rag-chatbot-service
```

> Trên Cloud Run, gán service account cho revision và để trống
> `FIREBASE_SERVICE_ACCOUNT_PATH` để dùng Application Default Credentials.

## 8. Cấu trúc thư mục

```
app/
├── main.py                  # khởi tạo FastAPI, mount router
├── config.py                # đọc env (pydantic-settings)
├── firebase_init.py         # init firebase-admin (path hoặc ADC)
├── auth.py                  # verify Firebase ID token
├── routers/chat.py          # POST /chat, GET /health
├── services/
│   ├── firestore_client.py  # đọc products
│   ├── embedding.py         # text-embedding-004
│   ├── vector_store.py      # wrapper ChromaDB
│   └── llm.py               # build prompt + gọi Gemini
├── scripts/index_products.py# sync Firestore → ChromaDB
└── models/schemas.py        # Pydantic request/response
```
# AI_ANDROI
