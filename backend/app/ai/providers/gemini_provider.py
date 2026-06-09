import asyncio
import json
import logging
import uuid

from google import genai
from google.genai import types

from app.ai.providers.base import ChatCompletionResult, LLMProvider, TokenUsage, ToolCallRequest
from app.ai.rate_limiter import is_transient_llm_error, with_chat_retry, with_embedding_retry
from app.core.config import Settings

logger = logging.getLogger(__name__)


def _parse_tool_call_entry(tc: dict) -> tuple[str, dict]:
    """Support OpenAI-style and flat tool_call message formats."""
    if "function" in tc and isinstance(tc["function"], dict):
        fn = tc["function"]
        name = fn.get("name", "")
        raw_args = fn.get("arguments", "{}")
    else:
        name = tc.get("name", "")
        raw_args = tc.get("arguments", "{}")

    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {}
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}

    return name, args


class GeminiProvider(LLMProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = (
            genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def embedding_dim(self) -> int:
        return self.settings.embedding_dim

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _embed_config(self) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(
            output_dimensionality=self.settings.embedding_dim,
            task_type="RETRIEVAL_DOCUMENT",
        )

    async def _call_embed(
        self,
        contents: str | list[str],
        *,
        min_delay_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> list[list[float]]:
        if not self._client:
            raise RuntimeError("Gemini provider not configured")

        async def _request() -> list[list[float]]:
            resp = await self._client.aio.models.embed_content(
                model=self.settings.gemini_embedding_model,
                contents=contents,
                config=self._embed_config(),
            )
            return [list(e.values) for e in resp.embeddings]

        return await with_embedding_retry(
            _request,
            rpm_limit=self.settings.embedding_rpm_limit,
            max_retries=max_retries or self.settings.embedding_max_retries,
            min_delay_seconds=(
                self.settings.embedding_min_delay_seconds
                if min_delay_seconds is None
                else min_delay_seconds
            ),
        )

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self._call_embed(text)
        return vectors[0]

    async def embed_query(self, text: str) -> list[float]:
        """Single-shot embed for live chat — bypasses import rate limiter."""
        if not self._client:
            raise RuntimeError("Gemini provider not configured")
        resp = await self._client.aio.models.embed_content(
            model=self.settings.gemini_embedding_model,
            contents=text,
            config=self._embed_config(),
        )
        return list(resp.embeddings[0].values)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._call_embed(texts)

    def _openai_tools_to_gemini(self, tools: list[dict]) -> list[types.Tool]:
        declarations = []
        for tool in tools:
            fn = tool.get("function", tool)
            declarations.append(
                types.FunctionDeclaration(
                    name=fn["name"],
                    description=fn.get("description", ""),
                    parameters=fn.get("parameters"),
                )
            )
        return [types.Tool(function_declarations=declarations)]

    def _tool_response_parts(self, messages: list[dict], start: int) -> tuple[list[types.Part], int]:
        parts: list[types.Part] = []
        i = start
        while i < len(messages) and messages[i].get("role") == "tool":
            tool_msg = messages[i]
            fn_name = tool_msg.get("name") or "tool"
            parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fn_name,
                        response={"result": tool_msg.get("content", "")},
                    )
                )
            )
            i += 1
        return parts, i

    def _messages_to_contents(self, messages: list[dict]) -> list[types.Content]:
        contents: list[types.Content] = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "user")

            if role == "system":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=f"System: {msg.get('content', '')}")],
                    )
                )
                i += 1
                continue

            if role == "assistant" and msg.get("gemini_content"):
                contents.append(msg["gemini_content"])
                i += 1
                tool_parts, i = self._tool_response_parts(messages, i)
                if tool_parts:
                    contents.append(types.Content(role="user", parts=tool_parts))
                continue

            if role == "tool":
                tool_parts, i = self._tool_response_parts(messages, i)
                if tool_parts:
                    contents.append(types.Content(role="user", parts=tool_parts))
                continue

            if role == "assistant" and msg.get("tool_calls"):
                parts = []
                if msg.get("content"):
                    parts.append(types.Part(text=msg["content"]))
                for tc in msg["tool_calls"]:
                    name, args = _parse_tool_call_entry(tc)
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                name=name,
                                args=args,
                            )
                        )
                    )
                contents.append(types.Content(role="model", parts=parts))
                i += 1
                tool_parts, i = self._tool_response_parts(messages, i)
                if tool_parts:
                    contents.append(types.Content(role="user", parts=tool_parts))
                continue

            gemini_role = "model" if role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=msg.get("content", ""))],
                )
            )
            i += 1
        return contents

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1000,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResult:
        if not self._client:
            raise RuntimeError("Gemini provider not configured")

        config = types.GenerateContentConfig(max_output_tokens=max_tokens)
        if tools:
            config.tools = self._openai_tools_to_gemini(tools)

        async def _request() -> ChatCompletionResult:
            resp = await self._client.aio.models.generate_content(
                model=self.settings.gemini_chat_model,
                contents=self._messages_to_contents(messages),
                config=config,
            )

            content_parts: list[str] = []
            tool_calls: list[ToolCallRequest] = []
            candidate = resp.candidates[0] if resp.candidates else None
            if candidate and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        content_parts.append(part.text)
                    if part.function_call:
                        fc = part.function_call
                        tool_calls.append(
                            ToolCallRequest(
                                id=f"call_{uuid.uuid4().hex[:12]}",
                                name=fc.name,
                                arguments=json.dumps(dict(fc.args) if fc.args else {}),
                            )
                        )

            usage = None
            if resp.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=resp.usage_metadata.prompt_token_count,
                    completion_tokens=resp.usage_metadata.candidates_token_count,
                )

            assistant_message = None
            if tool_calls:
                assistant_message = {
                    "role": "assistant",
                    "content": "\n".join(content_parts) or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in tool_calls
                    ],
                    # Preserve raw model turn so thought_signature survives multi-turn replay.
                    "gemini_content": candidate.content if candidate else None,
                }

            return ChatCompletionResult(
                content="\n".join(content_parts) if content_parts else None,
                tool_calls=tool_calls,
                usage=usage,
                assistant_message=assistant_message,
            )

        async def _attempt() -> ChatCompletionResult:
            return await asyncio.wait_for(
                _request(),
                timeout=self.settings.chat_llm_timeout_seconds,
            )

        try:
            return await with_chat_retry(
                _attempt,
                max_retries=self.settings.chat_max_retries,
                base_delay_seconds=self.settings.chat_retry_base_delay_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Gemini chat timed out after %.0fs",
                self.settings.chat_llm_timeout_seconds,
            )
            raise
        except Exception as exc:
            if is_transient_llm_error(exc):
                logger.warning("Gemini chat unavailable after retries: %s", exc)
            raise
