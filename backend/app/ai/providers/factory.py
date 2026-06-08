from functools import lru_cache

from app.ai.providers.base import LLMProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.local_provider import LocalProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import Settings, get_settings


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "openai":
        provider = OpenAIProvider(settings)
        return provider if provider.is_available else LocalProvider(settings.embedding_dim)

    if provider_name == "gemini":
        provider = GeminiProvider(settings)
        return provider if provider.is_available else LocalProvider(settings.embedding_dim)

    if provider_name == "local":
        return LocalProvider(settings.embedding_dim)

    # Default: Gemini
    provider = GeminiProvider(settings)
    return provider if provider.is_available else LocalProvider(settings.embedding_dim)


@lru_cache
def get_llm_provider() -> LLMProvider:
    return create_llm_provider()
