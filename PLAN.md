# PLAN — RAG Chatbot Service

Backend RAG (Python + FastAPI) làm chatbot hỏi đáp sản phẩm cho một app bán hàng Android.
App Android là một project riêng; service này chạy độc lập và được app gọi qua HTTP.

> **Lưu ý tích hợp:** App Android ĐÃ CÓ SẴN một hệ thống chat hoàn chỉnh
> (chat giữa người dùng, chạy trên Firestore realtime). Chatbot AI sẽ TÁI DÙNG hệ chat này
> thay vì làm màn hình mới — bot được coi là một "người tham gia" (participant) đặc biệt.
> Xem chi tiết ở mục 9.

## 1. Mục tiêu

- Nhận câu hỏi của người dùng về sản phẩm, tìm các sản phẩm liên quan bằng vector search, rồi
  dùng LLM sinh câu trả lời **chỉ dựa trên** dữ liệu sản phẩm thật (giảm bịa đặt).
- Trả về kèm danh sách sản phẩm được tham chiếu để app hiển thị card.
- Tách biệt hoàn toàn khỏi app Android: có thể deploy / cập nhật / scale độc lập.

## 2. Nguồn dữ liệu (Firebase Firestore)

Collection `products`, mỗi document có các trường (khớp với model `Product` của app Android):

| Trường        | Kiểu    | Ghi chú                          |
|---------------|---------|----------------------------------|
| `id`          | int     | id sản phẩm                      |
| `title`       | string  | tên sản phẩm                     |
| `description` | string  | mô tả                            |
| `category`    | string  | danh mục                         |
| `price`       | double  | giá                              |
| `rating`      | object  | đánh giá (rate, count)           |
| `image`       | string  | URL ảnh                          |

## 3. Công nghệ đã chốt

- **Framework**: FastAPI (async), Pydantic cho schema, uvicorn để chạy.
- **Auth**: `firebase-admin` — verify Firebase ID token do app Android gửi lên (tái dùng
  Firebase Auth đang có sẵn của app, KHÔNG tạo hệ auth riêng).
- **Firestore access**: `firebase-admin` (đọc products, có thể lưu lịch sử chat sau này).
- **Embedding + LLM**: Google Generative AI SDK.
  - Embedding: `text-embedding-004`.
  - Sinh câu trả lời: model `gemini` (đọc tên model từ env để dễ đổi).
  - API key đọc từ env `GOOGLE_API_KEY`.
- **Vector store**: ChromaDB chạy local, persist vào `./chroma_data` (giai đoạn đầu; sau này có
  thể chuyển sang Firestore Vector Search mà không đổi interface của `vector_store.py`).
- **Deploy**: Dockerfile để chạy trên Cloud Run / Render (đều có free tier).

## 4. Cấu trúc thư mục

```
rag-chatbot-service/
├── app/
│   ├── main.py                  # khởi tạo FastAPI, mount router, init firebase-admin
│   ├── config.py                # đọc env qua pydantic-settings
│   ├── auth.py                  # dependency verify Firebase ID token
│   ├── routers/
│   │   └── chat.py              # POST /chat, GET /health
│   ├── services/
│   │   ├── firestore_client.py  # đọc sản phẩm từ Firestore
│   │   ├── embedding.py         # tạo embedding cho text
│   │   ├── vector_store.py      # wrapper ChromaDB: upsert + query top-k
│   │   └── llm.py               # build prompt + gọi LLM sinh câu trả lời
│   ├── scripts/
│   │   └── index_products.py    # job đồng bộ Firestore -> ChromaDB
│   └── models/
│       └── schemas.py           # Pydantic request/response
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## 5. Đặc tả các thành phần

### `config.py`
Đọc từ env: `GOOGLE_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_PATH`, `GEMINI_MODEL`
(mặc định một model gemini hợp lý), `CHROMA_DIR` (mặc định `./chroma_data`), `TOP_K` (mặc định 5).

### `auth.py`
Dependency FastAPI: đọc header `Authorization: Bearer <token>`, verify bằng
`firebase_admin.auth.verify_id_token`, trả về `uid`. Lỗi -> HTTP 401.

### `services/vector_store.py`
Interface rõ ràng để dễ thay backend sau này:
- `upsert(items: list[dict])` — mỗi item gồm id, text để embed, và metadata (title, price, image, category).
- `query(text: str, top_k: int) -> list[dict]` — trả về các sản phẩm gần nhất kèm metadata.

### `scripts/index_products.py`
Đọc toàn bộ `products` từ Firestore -> với mỗi sản phẩm ghép
`title + " " + description + " " + category` thành text -> tạo embedding -> upsert vào ChromaDB
kèm metadata `{id, title, price, image, category}`. Chạy được bằng `python -m app.scripts.index_products`.

### `routers/chat.py`
**POST `/chat`**
- Bảo vệ bằng dependency auth (yêu cầu Firebase ID token hợp lệ).
- Request: `{ "message": str, "session_id": str }`
- Xử lý: embed `message` -> `vector_store.query` lấy top `TOP_K` -> build prompt (xem dưới) ->
  gọi `llm` -> trả response.
- Response: `{ "answer": str, "referenced_products": [{ "id", "title", "price", "image" }] }`

**GET `/health`** -> `{ "status": "ok" }`

### Prompt cho LLM (trong `services/llm.py`)
- System: "Bạn là trợ lý bán hàng. CHỈ trả lời dựa trên danh sách sản phẩm được cung cấp bên dưới.
  Nếu không có sản phẩm phù hợp, hãy nói thẳng là không tìm thấy. Trả lời bằng tiếng Việt, ngắn gọn."
- Context: chèn top-k sản phẩm (title, description, price, category).
- User: câu hỏi thật của người dùng.

## 6. Bảo mật & vận hành

- File service account JSON **KHÔNG commit** vào Git — thêm vào `.gitignore` cùng `.env` và `chroma_data/`.
- `.env.example` liệt kê tất cả biến env (không chứa giá trị thật).
- API key LLM chỉ nằm ở service này, tuyệt đối không đưa vào app Android.

## 7. Yêu cầu implement

- Viết code đầy đủ, có type hint, dùng Pydantic cho toàn bộ request/response.
- `requirements.txt` ghim phiên bản chính: fastapi, uvicorn, pydantic-settings, firebase-admin,
  google-generativeai, chromadb.
- `README.md` ngắn: cách cài đặt, cách chạy `index_products`, cách chạy server, cách gọi thử `/chat`.
- KHÔNG cần viết test.

## 8. Ngoài phạm vi của SERVICE này (giai đoạn sau)

- Streaming câu trả lời (SSE).
- Lưu lịch sử hội thoại theo `session_id`.
- Chuyển ChromaDB -> Firestore Vector Search.
- Rate limiting.

---

## 9. Tích hợp phía App Android (TÁI DÙNG hệ chat có sẵn)

> Mục này mô tả phần việc ở project ANDROID (không phải ở service Python). Ghi ở đây để giữ
> bức tranh tổng thể; khi implement service Python thì bỏ qua mục này.

### 9.1. Hạ tầng chat đã có sẵn trong app (tái dùng nguyên vẹn)

- **Model `Chat`** (hội thoại): `chatId`, `participants: List<String>` (danh sách uid),
  `names: Map<String,String>`, `lastMessage`, `updatedAt`.
- **Model `ChatMessage`**: `senderId`, `text`, `sentAt` (server timestamp),
  và `productJson: String?` — **đã có sẵn** để đính kèm một `Product` (serialize JSON) vào tin nhắn.
- **UI**: `ChatFragment` + `MessageAdapter` render hội thoại realtime; `ChatListFragment` liệt kê.
- **Repository**: `ChatRepositoryImpl.sendMessage(chat, message)` ghi conversation summary trước,
  rồi add message vào sub-collection (đã tính tới security rules).

### 9.2. Ý tưởng: bot là một "participant" đặc biệt

- Định nghĩa một uid cố định cho bot, ví dụ hằng số `AI_ASSISTANT_UID = "ai-assistant"`.
- Khi user mở chat với trợ lý AI -> tạo `Chat` với `participants = [userUid, AI_ASSISTANT_UID]`,
  `names` chứa tên hiển thị "Trợ lý AI".
- Tin nhắn của user ghi vào Firestore như bình thường (không đổi gì).
- Tin nhắn trả lời của bot có `senderId = AI_ASSISTANT_UID`; `MessageAdapter` tự render vì đang
  lắng nghe Firestore realtime.

### 9.3. Luồng trả lời của bot — CHỌN CÁCH B (đơn giản, ít hạ tầng)

**Cách B (khuyến nghị cho đồ án):**
1. User gửi câu hỏi (message ghi vào Firestore như bình thường).
2. App gọi service RAG qua **Retrofit**: `POST {BASE_URL}/chat` kèm header
   `Authorization: Bearer <firebase_id_token>`, body `{ message, session_id = chatId }`.
3. Nhận về `{ answer, referenced_products }`.
4. App tự ghi một `ChatMessage` của bot vào Firestore:
   - `senderId = AI_ASSISTANT_UID`, `text = answer`.
   - Nếu có sản phẩm gợi ý: set `productJson` = JSON của sản phẩm đầu tiên (dùng `Product.toJson()`)
     để `MessageAdapter` render card sản phẩm sẵn có.

**Cách A (nâng cao, không làm ở giai đoạn này):** Firestore trigger (Cloud Function) tự phát hiện
message mới trong chat có bot -> gọi service RAG -> ghi message trả lời. App không cần đổi gì,
nhưng thêm hạ tầng Cloud Function. Ghi lại để tham khảo sau.

### 9.4. Việc cần làm ở app Android (Cách B)

- Thêm `AI_ASSISTANT_UID` vào `Constants`.
- Thêm Retrofit API interface + service gọi `POST /chat` (base URL của service RAG đọc từ config).
- Trong `ChatViewModel`: sau khi gửi message của user tới chat-với-bot, gọi API RAG, rồi ghi
  message trả lời của bot qua `ChatRepositoryImpl.sendMessage` (tái dùng, không sửa repository).
- Thêm điểm vào (entry point) mở chat với "Trợ lý AI" — ví dụ một mục trong `ChatListFragment`
  hoặc nút trên màn hình sản phẩm.
- Kiểm tra `firestore.rules` cho phép ghi message có participant là `ai-assistant`
  (bot không tự đăng nhập, nên message bot do chính app của user ghi — rule hiện tại dựa trên
  "sender là participant" nên thường đã hợp lệ; cần rà lại để chắc chắn).
