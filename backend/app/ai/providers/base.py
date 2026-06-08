from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: str


@dataclass
class ChatCompletionResult:
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    usage: TokenUsage | None = None
    assistant_message: dict | None = None


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...

    @property
    def supports_chat(self) -> bool:
        return self.is_available

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1000,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResult:
        ...
