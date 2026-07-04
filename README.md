# RAG Chatbot Service

Backend RAG (Python + FastAPI) làm chatbot hỏi đáp sản phẩm cho app bán hàng Android.
Service chạy độc lập, được app gọi qua HTTP. Chi tiết đặc tả xem [`PLAN.md`](./PLAN.md).

Luồng xử lý: câu hỏi → embedding (Google `gemini-embedding-001`) → vector search (ChromaDB) →
build prompt → sinh câu trả lời (Gemini) → trả về `answer` + danh sách sản phẩm tham chiếu.

## 1. Yêu cầu

- Python 3.11+ (đã chạy tốt trên 3.13).
- Một **Firebase service account** (file JSON) có quyền đọc Firestore.
- **Google API key** (Google AI Studio, free tier): https://aistudio.google.com/apikey

## 2. Cài đặt

```bash
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

> `chromadb` ghim bản ≥1.5 (lõi Rust, có wheel dựng sẵn cho Windows/Python 3.13)
> nên **không cần** Visual C++ Build Tools.

## 3. Cấu hình

Copy `.env.example` thành `.env` rồi điền giá trị:

```bash
cp .env.example .env
```

| Biến                            | Bắt buộc | Mặc định                       | Ghi chú                                   |
|---------------------------------|----------|--------------------------------|-------------------------------------------|
| `GOOGLE_API_KEY`                | ✅       | —                              | API key Google AI Studio.                 |
| `GEMINI_MODEL`                  | ❌       | `gemini-2.5-flash`             | Model sinh câu trả lời.                    |
| `EMBEDDING_MODEL`               | ❌       | `models/gemini-embedding-001`  | Model tạo embedding.                       |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | ❌       | —                              | Đường dẫn file JSON. Để trống → dùng ADC. |
| `CHROMA_DIR`                    | ❌       | `./chroma_data`                | Thư mục persist ChromaDB.                  |
| `TOP_K`                         | ❌       | `5`                            | Số sản phẩm gần nhất lấy ra.               |

> File service account JSON và `.env` **không được commit** (đã có trong `.gitignore`).
> Nếu key báo model không tồn tại, chạy `list_models` để xem tên model key hỗ trợ.

## 4. Index sản phẩm (Firestore → ChromaDB)

Trước khi hỏi đáp, cần index dữ liệu sản phẩm vào vector store:

```bash
python -m app.scripts.index_products
```

Chạy lại bất cứ khi nào dữ liệu `products` trên Firestore thay đổi (job dùng `upsert`
theo `id` nên chạy lại an toàn, không tạo bản trùng).

## 5. Chạy server

```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

> Nếu cổng 8000 (hoặc 8080) báo lỗi `WinError 10013` thì cổng đang bị tiến trình
> khác chiếm — đổi sang cổng khác, vd `--port 5000`.

## 6. Gọi thử `/chat`

Endpoint yêu cầu header `Authorization: Bearer <firebase_id_token>`.

**Lấy ID token để test** (tiện ích DEV — cần Web API Key của project):

```bash
python -m app.scripts.get_id_token <WEB_API_KEY>
```

Copy chuỗi token ở dòng đầu, rồi gọi `/chat`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <FIREBASE_ID_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Có nước hoa nào không?", "session_id": "demo-1"}'
```

Hoặc dán token vào nút **Authorize** trong `/docs` rồi thử trực tiếp trên giao diện.

Response mẫu:

```json
{
  "answer": "Có các loại nước hoa sau ...",
  "referenced_products": [
    { "id": "prod_8", "title": "Dior J'adore", "price": 89.99, "image": "https://..." }
  ]
}
```

> `id` là **chuỗi** (khớp dữ liệu Firestore thực tế, vd `prod_8`).

## 7. Chạy bằng Docker

```bash
docker build -t rag-chatbot-service .
docker run -p 8000:8080 --env-file .env \
  -v "$(pwd)/service-account.json:/app/service-account.json" \
  rag-chatbot-service
```

> Container chạy ở cổng 8080 nội bộ; lệnh trên map ra cổng 8000 của máy host.
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
│   ├── embedding.py         # gemini-embedding-001
│   ├── vector_store.py      # wrapper ChromaDB
│   └── llm.py               # build prompt + gọi Gemini
├── scripts/
│   ├── index_products.py    # sync Firestore → ChromaDB
│   └── get_id_token.py      # tiện ích DEV lấy ID token để test
└── models/schemas.py        # Pydantic request/response
```
