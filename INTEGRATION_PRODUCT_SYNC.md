# Hợp đồng API: Đồng bộ sản phẩm Firestore → ChromaDB

> **Bản bàn giao từ team App Android cho team Service RAG (Python/FastAPI).**
> App Android **đã tích hợp sẵn** phần gọi 2 endpoint dưới đây (xem `RagApi.kt`,
> `AddProductViewModel.kt`, `MyProductsViewModel.kt`). Nhiệm vụ của bạn: **hiện thực 2 endpoint
> này ở service Python** để mỗi khi app thêm/sửa/xóa sản phẩm thì vector trong ChromaDB được
> cập nhật theo. File này là "hợp đồng" — bám sát tuyệt đối tên path, field, mã lỗi.

---

## 1. Bối cảnh

- Sản phẩm là **nguồn sự thật ở Firestore** collection `products` (project `appmobie-ccbf3`).
- ChromaDB hiện được nạp bằng script chạy tay 1 lần: `python -m app.scripts.index_products`.
  → Vấn đề: thêm/sửa/xóa sản phẩm trong app thì ChromaDB **không tự cập nhật**.
- Giải pháp (Cách A — app chủ động gọi): sau khi ghi Firestore thành công, app gọi thêm HTTP
  tới service RAG để index/xóa vector tương ứng.
- Dùng chung 1 Firebase project với `/chat` nên xác thực **y hệt** endpoint `/chat`
  (Firebase ID token, verify bằng `firebase_admin.auth.verify_id_token`).

---

## 2. HỢP ĐỒNG API (phần quan trọng nhất)

Xác thực **bắt buộc** cho cả 2 endpoint (giống `/chat`):
```
Authorization: Bearer <firebase_id_token>
Content-Type: application/json
```

### 2.1. `POST /products/index` — thêm mới HOẶC cập nhật (upsert)

App gọi endpoint này **sau khi thêm mới** và **sau khi sửa** sản phẩm. Một endpoint duy nhất cho
cả hai vì với vector DB, add và update là **cùng một thao tác upsert** (idempotent).

**Request body:**
```json
{ "id": "abc123" }
```
| Trường | Kiểu   | Bắt buộc | Ghi chú                                             |
|--------|--------|----------|-----------------------------------------------------|
| `id`   | string | ✅       | Document id của sản phẩm trong Firestore `products`. |

> ⚠️ App **chỉ gửi `id`**, KHÔNG gửi toàn bộ sản phẩm. Service phải **tự đọc lại**
> `products/{id}` từ Firestore (nguồn sự thật) rồi mới embed. Lý do: tránh lệch dữ liệu
> giữa payload của app và Firestore, và tái dùng đúng logic đã có trong `index_products`.

**Service phải làm:**
1. Verify token → 401 nếu thiếu/sai/hết hạn.
2. (Khuyến nghị) Kiểm quyền: chỉ cho `sellerId == uid` hoặc user role `admin` index sản phẩm đó → 403 nếu không.
3. Đọc `products/{id}` từ Firestore. Nếu không tồn tại → `404`.
4. Tạo embedding từ các field văn bản (title, description, category, ...) — **giống hệt** cách
   `index_products` đang làm để không lệch không gian vector.
5. `collection.upsert(ids=[id], ...)` vào ChromaDB (id sản phẩm = id vector).

**Response 200:**
```json
{ "status": "ok", "id": "abc123" }
```

### 2.2. `DELETE /products/index/{id}` — xóa vector

App gọi **sau khi xóa** sản phẩm khỏi Firestore.

- `id` nằm trên **path**, không có request body.
- Service: verify token (+ kiểm quyền như trên) → `collection.delete(ids=[id])`.
- Xóa 1 id không tồn tại nên coi là **thành công** (idempotent), trả 200 luôn.

**Response 200:**
```json
{ "status": "ok", "id": "abc123" }
```

### 2.3. Mã lỗi cần hỗ trợ (thống nhất với `/chat`)
| HTTP  | Khi nào                                   | Body gợi ý                                      |
|-------|-------------------------------------------|-------------------------------------------------|
| `401` | Thiếu / sai / hết hạn Firebase ID token   | `{"detail":"Thiếu Firebase ID token."}`         |
| `403` | User không phải chủ sản phẩm / không admin | `{"detail":"Không có quyền."}`                 |
| `404` | (chỉ index) `products/{id}` không tồn tại | `{"detail":"Không tìm thấy sản phẩm."}`         |
| `422` | Thiếu `id` trong body                     | `{"detail":[{...}]}` (validation FastAPI)       |
| `5xx` | Lỗi embed/ChromaDB/service                | Bất kỳ — app đã nuốt lỗi, chỉ log (xem mục 4).  |

---

## 3. App gọi endpoint này KHI NÀO

| Hành động trong app                         | Endpoint app gọi                     | File Android                        |
|---------------------------------------------|--------------------------------------|-------------------------------------|
| Thêm sản phẩm (Seller/Admin, nút Save)      | `POST /products/index`               | `AddProductViewModel.onSaveClicked` |
| Sửa sản phẩm (nút Save ở chế độ edit)       | `POST /products/index` (upsert)      | `AddProductViewModel.onSaveClicked` |
| Xóa sản phẩm (MyProducts → xác nhận xóa)    | `DELETE /products/index/{id}`        | `MyProductsViewModel.deleteProduct` |

Luồng: **ghi Firestore trước → thành công mới gọi sync**. Vì vậy khi request tới service,
document đã tồn tại (với index) hoặc đã bị xóa (với delete).

---

## 4. Tính nhất quán & xử lý lỗi (đã quyết ở phía app — để bạn nắm)

- Sync là **best-effort**: app bọc `runCatching` + `withTimeoutOrNull(4000ms)`. Nếu service
  chết/timeout/lỗi, app **vẫn coi việc lưu/xóa sản phẩm là thành công** (Firestore là chính),
  chỉ bỏ qua phần đồng bộ. → Service KHÔNG cần lo app bị kẹt khi nó lỗi.
- Hệ quả: ChromaDB **có thể lệch tạm thời** nếu service đang down, hoặc nếu sản phẩm bị sửa
  ngoài app (Firebase Console, script). Vì vậy **vẫn giữ** script `index_products` để
  **re-index toàn bộ** khi cần đồng bộ lại.
- Đề nghị 2 endpoint **idempotent**: gọi lại nhiều lần cho cùng 1 id vẫn an toàn (upsert/delete).

---

## 5. Kết nối mạng (giống `/chat`)

Cùng `RAG_BASE_URL` với `/chat` (`Constants.RAG_BASE_URL`):

| Môi trường            | BASE_URL                                  |
|-----------------------|-------------------------------------------|
| Emulator Android      | `http://10.0.2.2:8000/`                   |
| Điện thoại thật (cùng WiFi) | `http://<IP_LAN_máy_chạy_service>:8000/` |
| Production            | `https://<service>.run.app/` (Cloud Run)  |

Dev dùng `http://` thì app cần `usesCleartextTraffic="true"` (xem `INTEGRATION_FOR_ANDROID.md` mục 3).

---

## 6. Checklist bàn giao (phía Python)

- [ ] `POST /products/index` nhận `{ "id": "..." }`, verify token, đọc lại Firestore, embed + `upsert`.
- [ ] `DELETE /products/index/{id}` verify token, `collection.delete(ids=[id])`, idempotent.
- [ ] Dùng **đúng cùng hàm embedding** với `index_products` (cùng model, cùng field ghép text).
- [ ] Trả JSON `{"status":"ok","id":"..."}` khi thành công; mã lỗi theo mục 2.3.
- [ ] (Khuyến nghị) Kiểm quyền `sellerId == uid` hoặc role `admin` trước khi ghi/xóa vector.
- [ ] Test end-to-end: app thêm 1 sản phẩm → hỏi chatbot thấy sản phẩm mới; xóa → chatbot không còn gợi ý.
- [ ] `index_products` vẫn chạy được để re-index toàn bộ khi cần.

---

## 7. Đối chiếu DTO phía Android (đã hiện thực trong `RagApi.kt`)

```kotlin
data class ProductSyncRequest(val id: String)                    // body POST /products/index
data class SyncResponse(val status: String? = null, val id: String? = null)

@POST("products/index")
suspend fun indexProduct(@Header("Authorization") bearer: String, @Body body: ProductSyncRequest): SyncResponse

@DELETE("products/index/{id}")
suspend fun deleteProductIndex(@Header("Authorization") bearer: String, @Path("id") id: String): SyncResponse
```
