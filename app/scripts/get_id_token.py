"""Tiện ích DEV: lấy Firebase ID token để test endpoint /chat.

KHÔNG phải thành phần của service — chỉ dùng khi phát triển/thử nghiệm.

Cách hoạt động: dùng service account tạo một custom token cho một uid test,
rồi đổi lấy ID token qua Firebase REST API. Không cần tài khoản email/password.

Cách dùng:
    python -m app.scripts.get_id_token [web_api_key] [uid]

- web_api_key: lấy ở Firebase Console -> Project settings -> General -> "Web API Key"
  (hoặc đặt biến môi trường FIREBASE_WEB_API_KEY). Có thể bỏ qua nếu đã đặt env.
- uid: định danh người dùng test (mặc định "rag-test-user").

Token in ra hết hạn sau ~1 giờ; chạy lại để lấy token mới.
Dán token (dòng đầu) vào nút Authorize của Swagger (/docs) rồi thử /chat.
"""

import json
import os
import sys
import urllib.request

from firebase_admin import auth

from app.firebase_init import init_firebase

SIGN_IN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={key}"
)


def get_id_token(api_key: str, uid: str) -> str:
    """Tạo custom token cho `uid` rồi đổi lấy Firebase ID token."""
    init_firebase()
    custom_token = auth.create_custom_token(uid).decode("utf-8")

    payload = json.dumps(
        {"token": custom_token, "returnSecureToken": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        SIGN_IN_URL.format(key=api_key),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["idToken"]


def main() -> None:
    api_key = None
    uid = "rag-test-user"

    args = sys.argv[1:]
    if args:
        api_key = args[0]
    if len(args) > 1:
        uid = args[1]
    if not api_key:
        api_key = os.getenv("FIREBASE_WEB_API_KEY")

    if not api_key:
        print(__doc__)
        print("Thiếu Web API Key.", file=sys.stderr)
        sys.exit(1)

    token = get_id_token(api_key, uid)
    # In token trần (copy vào ô Authorize của Swagger)...
    print(token)
    # ...và sẵn header Bearer để dán vào curl.
    print(f"\nAuthorization: Bearer {token}", file=sys.stderr)


if __name__ == "__main__":
    main()
