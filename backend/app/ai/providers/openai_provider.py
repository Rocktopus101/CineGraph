import json
import logging

from openai import APIError, AsyncOpenAI

from app.ai.providers.base import ChatCompletionResult, LLMProvider, TokenUsage, ToolCallRequest
from app.core.config import Settings

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def embedding_dim(self) -> int:
        return self.settings.embedding_dim

    @property
    def is_available(self) -> bool:
        return self._client is not None

    async def embed_text(self, text: str) -> list[float]:
        if not self._client:
            raise RuntimeError("OpenAI provider not configured")
        resp = await self._client.embeddings.create(
            model=self.settings.embedding_model,
            input=text,
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._client:
            raise RuntimeError("OpenAI provider not configured")
        resp = await self._client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
        )
        return [d.embedding for d in resp.data]

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1000,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResult:
        if not self._client:
            raise RuntimeError("OpenAI provider not configured")
        try:
            kwargs: dict = {
                "model": self.settings.chat_model,
                "messages": messages,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
            resp = await self._client.chat.completions.create(**kwargs)
            choice = resp.choices[0]
            tool_calls = [
                ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                )
                for tc in (choice.message.tool_calls or [])
            ]
            usage = None
            if resp.usage:
                usage = TokenUsage(
                    prompt_tokens=resp.usage.prompt_tokens,
                    completion_tokens=resp.usage.completion_tokens,
                )
            return ChatCompletionResult(
                content=choice.message.content,
                tool_calls=tool_calls,
                usage=usage,
                assistant_message=choice.message.model_dump(),
            )
        except APIError as exc:
            logger.warning("OpenAI chat failed (%s)", exc)
            raise
