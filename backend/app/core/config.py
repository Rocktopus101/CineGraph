from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Accept standard Postgres URLs (e.g. from Neon) and coerce to asyncpg."""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url.replace("sslmode=require", "ssl=require")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cinegraph:cinegraph@localhost:5432/cinegraph"

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_database_url(cls, value: str) -> str:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    # LLM provider: gemini (default) | openai | local
    llm_provider: str = "gemini"
    embedding_dim: int = 768

    # Gemini (default — free tier at https://aistudio.google.com/apikey)
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    # 2.0 Flash is shut down on the free tier (quota limit: 0). Use 2.5 Flash family.
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_chat_model_fallbacks: str = "gemini-2.5-flash-lite,gemini-3.1-flash-lite,gemini-1.5-flash"

    # OpenAI (optional)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    tmdb_api_key: str = ""

    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    # Preferred on Render: paste the full service-account JSON as one line.
    firebase_service_account_json: str = ""

    dev_mode: bool = False
    dev_skip_onboarding: bool = False
    dev_firebase_uid: str = "dev-user-local"
    dev_admin: bool = False

    tmdb_cache_ttl_days: int = 30
    import_max_file_mb: int = 50

    # Gemini free-tier embedding limits (100 RPM, 30k TPM, 1k RPD)
    embedding_batch_size: int = 8
    embedding_rpm_limit: int = 60
    embedding_min_delay_seconds: float = 1.5
    embedding_max_retries: int = 12
    embedding_max_chunk_chars: int = 600
    # Skip per-film user-history embedding API calls during import (uses zero vectors).
    import_embed_user_history: bool = False

    chat_max_retries: int = 2
    chat_retry_base_delay_seconds: float = 1.0
    # Agent tool loops exceed Render's ~30s free-tier limit; use single-pass chat by default.
    chat_use_agent: bool = False
    # Skip vector retrieval during chat — history + Gemini fits Render's ~30s request limit.
    chat_skip_retrieval: bool = True
    chat_retrieval_timeout_seconds: float = 4.0
    chat_llm_timeout_seconds: float = 26.0

    # Comma-separated origins for CORS (include production frontend URL)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Match Vercel preview deployments (e.g. cine-graph-xxx-vedaant-s-projects.vercel.app)
    cors_origin_regex: str = r"https://.*\.vercel\.app"


@lru_cache
def get_settings() -> Settings:
    return Settings()
