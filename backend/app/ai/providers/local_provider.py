from app.ai.providers.base import ChatCompletionResult, LLMProvider


class LocalProvider(LLMProvider):
    """Zero-vector embeddings and no chat — offline / no-API-key fallback."""

    def __init__(self, embedding_dim: int = 768):
        self._embedding_dim = embedding_dim

    @property
    def name(self) -> str:
        return "local"

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    @property
    def is_available(self) -> bool:
        return True

    @property
    def supports_chat(self) -> bool:
        return False

    def _zero(self) -> list[float]:
        return [0.0] * self._embedding_dim

    async def embed_text(self, text: str) -> list[float]:
        return self._zero()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._zero() for _ in texts]

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1000,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResult:
        return ChatCompletionResult(content=None)
