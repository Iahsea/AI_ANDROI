FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cài dependencies trước để tận dụng layer cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source.
COPY app ./app

# Cloud Run / Render truyền cổng qua biến môi trường PORT (mặc định 8080).
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
