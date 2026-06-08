FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Pin cryptography: 43+ wheels SIGILL on Apple Silicon Docker (exit 132).
RUN pip install --no-cache-dir "cryptography==42.0.8" && pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
    pydantic pydantic-settings python-multipart httpx firebase-admin \
    google-genai openai pgvector python-jose[cryptography]

COPY . .
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
