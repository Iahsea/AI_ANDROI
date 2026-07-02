"""Điểm khởi động FastAPI: init firebase-admin và mount router."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.firebase_init import init_firebase
from app.routers import chat


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Khởi tạo firebase-admin khi app start."""
    init_firebase()
    yield


app = FastAPI(title="RAG Chatbot Service", version="1.0.0", lifespan=lifespan)
app.include_router(chat.router)
