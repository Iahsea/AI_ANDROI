# Hướng dẫn tích hợp: RAG Chatbot Service ↔ App Android

> **Đọc kỹ file này rồi tích hợp vào project Android.** Đây là bản bàn giao từ team
> làm service RAG (Python/FastAPI). Service đã hoàn thiện, đã test chạy đúng end-to-end.
> Nhiệm vụ của bạn: nối app Android vào service này theo **Cách B** (app tự gọi HTTP rồi
> tự ghi tin trả lời của bot vào Firestore). KHÔNG cần sửa gì ở service Python.

---

## 1. Bối cảnh

- App Android **đã có sẵn hệ chat realtime trên Firestore** (chat giữa người dùng).
- Chatbot AI **tái dùng** hệ chat đó: bot là một "participant" đặc biệt với uid cố định.
- Service RAG nhận câu hỏi → tìm sản phẩm liên quan (vector search) → gọi Gemini sinh câu
  trả lời **chỉ dựa trên sản phẩm thật** → trả về câu trả lời + danh sách sản phẩm tham chiếu.
- Cùng chung **một Firebase project** với app: `appmobie-ccbf3`. Nhờ vậy service verify được
  Firebase ID token do app gửi lên.

---

## 2. HỢP ĐỒNG API (phần quan trọng nhất — bám sát tuyệt đối)

### `POST /chat`

**Bắt buộc** header xác thực:
```
Authorization: Bearer <firebase_id_token>
Content-Type: application/json
```
`<firebase_id_token>` là ID token của user hiện tại, lấy từ Firebase Auth **có sẵn trong app**
(cùng project `appmobie-ccbf3`). Service verify bằng `firebase_admin.auth.verify_id_token`.

**Request body:**
```json
{
  "message": "Có nước hoa nào không?",
  "session_id": "demo-1"
}
```
| Trường       | Kiểu   | Bắt buộc | Ghi chú                                   |
|--------------|--------|----------|-------------------------------------------|
| `message`    | string | ✅ (≥1 ký tự) | Câu hỏi của người dùng.               |
| `session_id` | string | ✅ (≥1 ký tự) | Dùng `chatId` của cuộc chat.          |

**Response 200:**
```json
{
  "answer": "Có các loại nước hoa sau ...",
  "referenced_products": [
    {
      "id": "prod_8",
      "title": "Dior J'adore",
      "price": 89.99,
      "image": "https://cdn.dummyjson.com/.../thumbnail.webp"
    }
  ]
}
```
| Trường                | Kiểu                    | Ghi chú                                            |
|-----------------------|-------------------------|----------------------------------------------------|
| `answer`              | string                  | Câu trả lời tiếng Việt của bot.                    |
| `referenced_products` | mảng object (có thể rỗng) | Top‑K sản phẩm gần nhất. Có thể rỗng `[]`.        |
| `└ id`                | **string**              | ⚠️ Là CHUỖI (vd `"prod_8"`), KHÔNG phải số nguyên. |
| `└ title`             | string                  | Tên sản phẩm.                                      |
| `└ price`             | number (double)         | Giá.                                               |
| `└ image`             | string                  | URL ảnh.                                           |

> ⚠️ **Lưu ý quan trọng:** `referenced_products` là các sản phẩm vector search lấy ra, **độc lập**
> với việc câu trả lời có nhắc tới chúng hay không. Có thể `answer` nói "không tìm thấy" nhưng mảng
> vẫn có vài sản phẩm gần nhất. Nếu chỉ muốn hiện card khi thực sự liên quan, app tự quyết định lọc.

### `GET /health`
Trả `{"status":"ok"}` — dùng để kiểm tra service sống.

### Mã lỗi cần xử lý
| HTTP | Khi nào | Body |
|------|---------|------|
| `401` | Thiếu / sai / hết hạn token | `{"detail":"Thiếu Firebase ID token."}` hoặc `"...không hợp lệ."` |
| `422` | Thiếu `message` hoặc `session_id` | `{"detail":[{...}]}` (dạng validation của FastAPI) |
| `5xx` | Lỗi service/LLM | Nên hiện fallback "hiện chưa trả lời được, thử lại". |

---

## 3. Kết nối mạng — chọn BASE_URL đúng

Service KHÔNG chạy trên điện thoại. Chọn URL theo môi trường:

| Môi trường            | BASE_URL                                  |
|-----------------------|-------------------------------------------|
| Emulator Android      | `http://10.0.2.2:8000/`                   |
| Điện thoại thật (cùng WiFi) | `http://<IP_LAN_máy_chạy_service>:8000/` |
| Production            | `https://<service>.run.app/` (Cloud Run)  |

⚠️ Android chặn HTTP cleartext mặc định. Khi test với `http://`, thêm vào `AndroidManifest.xml`:
```xml
<application android:usesCleartextTraffic="true" ... >
```
Production dùng `https` thì bỏ dòng này.

---

## 4. Các bước tích hợp (Cách B)

> Trước khi code, **hãy đọc code hiện có** của các thành phần sau trong project Android rồi
> ĐIỀU CHỈNH cho khớp tên field/hàm thật (đừng giả định — mở file ra xem):
> - Model `Chat` (`chatId`, `participants`, `names`, `lastMessage`, `updatedAt`)
> - Model `ChatMessage` (`senderId`, `text`, `sentAt`, `productJson`)
> - Model `Product` và hàm serialize (`Product.toJson()` hoặc tương đương)
> - `ChatRepositoryImpl.sendMessage(chat, message)`
> - `ChatViewModel`, `ChatFragment`, `MessageAdapter`, `ChatListFragment`
> - Nơi khai báo `Constants`, cấu hình Retrofit (nếu app đã dùng Retrofit sẵn thì tái dùng)

### 4.1. Thêm hằng số
```kotlin
object Constants {
    const val AI_ASSISTANT_UID  = "ai-assistant"
    const val AI_ASSISTANT_NAME = "Trợ lý AI"
    const val RAG_BASE_URL      = "http://10.0.2.2:8000/"  // đổi theo bảng mục 3
}
```

### 4.2. Retrofit API + DTO
```kotlin
data class ChatRequest(val message: String, val session_id: String)

data class ReferencedProduct(
    val id: String,        // ⚠️ String, không phải Int
    val title: String,
    val price: Double,
    val image: String
)
data class ChatResponse(
    val answer: String,
    val referenced_products: List<ReferencedProduct>
)

interface RagApi {
    @POST("chat")
    suspend fun chat(
        @Header("Authorization") bearer: String,   // "Bearer <idToken>"
        @Body body: ChatRequest
    ): ChatResponse
}
```

### 4.3. Lấy Firebase ID token (dùng Firebase Auth đã có)
```kotlin
suspend fun currentIdToken(): String {
    val user = FirebaseAuth.getInstance().currentUser
        ?: error("Chưa đăng nhập")
    return user.getIdToken(false).await().token!!   // cần kotlinx-coroutines-play-services
}
```

### 4.4. Trong `ChatViewModel`: gửi câu hỏi → gọi RAG → ghi tin của bot
```kotlin
fun sendToAiAssistant(chat: Chat, userText: String) = viewModelScope.launch {
    // (1) Ghi message của user như bình thường (TÁI DÙNG repo, không sửa repo)
    chatRepository.sendMessage(chat, ChatMessage(senderId = currentUserUid, text = userText))

    try {
        // (2) Gọi service RAG
        val token = currentIdToken()
        val resp = ragApi.chat(
            bearer = "Bearer $token",
            body = ChatRequest(message = userText, session_id = chat.chatId)
        )
        // (3) Ghi message trả lời của bot vào Firestore
        val first = resp.referenced_products.firstOrNull()
        chatRepository.sendMessage(chat, ChatMessage(
            senderId = Constants.AI_ASSISTANT_UID,
            text = resp.answer,
            productJson = first?.let { gson.toJson(it.toProduct()) }  // map -> Product của app
        ))
    } catch (e: Exception) {
        chatRepository.sendMessage(chat, ChatMessage(
            senderId = Constants.AI_ASSISTANT_UID,
            text = "Xin lỗi, hiện chưa trả lời được. Vui lòng thử lại."
        ))
    }
}
```
> `MessageAdapter` đang nghe Firestore realtime nên tin nhắn bot **tự hiện**, không cần sửa UI.
> Cần viết hàm map `ReferencedProduct` → `Product` (đúng các field mà `Product.toJson()` và
> `MessageAdapter` mong đợi). Lưu ý `id` là String.

### 4.5. Điểm vào mở chat với Trợ lý AI
```kotlin
val chat = Chat(
    chatId = "$currentUserUid-${Constants.AI_ASSISTANT_UID}",
    participants = listOf(currentUserUid, Constants.AI_ASSISTANT_UID),
    names = mapOf(
        currentUserUid to currentUserName,
        Constants.AI_ASSISTANT_UID to Constants.AI_ASSISTANT_NAME
    )
)
```
Đặt nút/entry point mở chat này ở `ChatListFragment` hoặc màn hình sản phẩm.

### 4.6. Kiểm tra `firestore.rules`
Bot KHÔNG tự đăng nhập — message của bot do **chính app của user** ghi (uid thật). Rà rule đảm bảo:
một participant hợp lệ được ghi message có `senderId` là participant khác (bot `ai-assistant`).
Nếu rule chặn theo kiểu "senderId phải == request.auth.uid" thì phải nới cho case bot.
Nếu không, sẽ bị `PERMISSION_DENIED` khi ghi tin của bot.

---

## 5. Luồng tổng quát

```
User gõ câu hỏi
  ├─(1) app ghi ChatMessage(user) vào Firestore      → MessageAdapter hiện ngay
  ├─(2) app POST /chat (Bearer idToken) ─────────────► Service RAG (Python)
  │                                                      embed → vector search → Gemini
  │        ◄──── { answer, referenced_products } ──────┘
  └─(3) app ghi ChatMessage(bot, answer, productJson) → MessageAdapter hiện card sản phẩm
```

---

## 6. Cách chạy service để test (phía backend, cho bạn tham khảo)

Service chạy độc lập ở repo `rag-chatbot-service`:
```bash
uvicorn app.main:app --reload --port 8000     # server
python -m app.scripts.index_products          # nạp products vào vector store (chạy trước)
python -m app.scripts.get_id_token <WEB_API_KEY>   # lấy ID token để test thủ công
```
`WEB_API_KEY` chính là API key trong `google-services.json` của app Android (project `appmobie-ccbf3`).

---

## 7. Checklist bàn giao

- [ ] Service chạy được, `GET /health` trả `{"status":"ok"}`.
- [ ] Đã chọn đúng `RAG_BASE_URL` cho môi trường test.
- [ ] `usesCleartextTraffic=true` nếu dùng http khi dev.
- [ ] DTO khớp contract, đặc biệt `id` là **String**.
- [ ] Gửi đúng header `Authorization: Bearer <idToken>` (token cùng project Firebase).
- [ ] Map `ReferencedProduct` → `Product` đúng field cho `MessageAdapter`.
- [ ] `firestore.rules` cho phép ghi message của bot.
- [ ] Test: mở chat Trợ lý AI → gửi câu hỏi → thấy câu trả lời + card sản phẩm.

---

## 8. Đã kiểm chứng ở phía service (để bạn yên tâm)

- Đọc 51 sản phẩm từ Firestore `products` → index vào ChromaDB thành công.
- Vector search trả đúng ngữ nghĩa (hỏi "nước hoa" → ra Dior/Gucci/Chanel...).
- Gemini (`gemini-2.5-flash`) sinh câu trả lời bám sát sản phẩm.
- Auth verify đúng: thiếu token → 401; token hợp lệ → 200.
- Gọi `POST /chat` qua HTTP thật trả về `answer` + `referenced_products` kèm ảnh.
