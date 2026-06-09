import asyncio
import json
import logging
import uuid

from google import genai
from google.genai import types

from app.ai.providers.base import ChatCompletionResult, LLMProvider, TokenUsage, ToolCallRequest
from app.ai.rate_limiter import (
    is_rate_limit_error,
    is_transient_llm_error,
    with_chat_retry,
    with_embedding_retry,
)
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


def _is_model_not_found_error(error: Exception) -> bool:
    msg = str(error).lower()
    return "404" in msg or "not found" in msg or "is not supported" in msg


def _should_try_next_chat_model(error: Exception, model: str) -> bool:
    """Try the next model when this one is missing or has no free-tier quota."""
    if _is_model_not_found_error(error):
        return True
    if not is_rate_limit_error(error):
        return False
    msg = str(error).lower()
    model_key = model.lower().replace("_", "-")
    if model_key in msg:
        return True
    if "free_tier" in msg or "limit: 0" in msg:
        return True
    return False


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

    def _chat_models(self) -> list[str]:
        models = [self.settings.gemini_chat_model]
        seen = {self.settings.gemini_chat_model}
        for model in self.settings.gemini_chat_model_fallbacks.split(","):
            model = model.strip()
            if model and model not in seen:
                models.append(model)
                seen.add(model)
        return models

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

    def _split_system_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        chat_messages: list[dict] = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if content:
                    system_parts.append(content)
            else:
                chat_messages.append(msg)
        system_instruction = "\n\n".join(system_parts) if system_parts else None
        return system_instruction, chat_messages

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

    def _parse_generate_response(self, resp) -> ChatCompletionResult:
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

        if not content_parts and not tool_calls:
            finish_reason = getattr(candidate, "finish_reason", None) if candidate else None
            prompt_feedback = getattr(resp, "prompt_feedback", None)
            raise RuntimeError(
                f"Gemini returned no content (finish_reason={finish_reason}, "
                f"prompt_feedback={prompt_feedback})"
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
                "gemini_content": candidate.content if candidate else None,
            }

        return ChatCompletionResult(
            content="\n".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
            usage=usage,
            assistant_message=assistant_message,
        )

    async def _generate_with_model(
        self,
        model: str,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> ChatCompletionResult:
        resp = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return self._parse_generate_response(resp)

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 1000,
        tools: list[dict] | None = None,
    ) -> ChatCompletionResult:
        if not self._client:
            raise RuntimeError("Gemini provider not configured")

        system_instruction, chat_messages = self._split_system_messages(messages)
        contents = self._messages_to_contents(chat_messages)
        if not contents:
            raise RuntimeError("Gemini chat requires at least one user message")

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )
        if tools:
            config.tools = self._openai_tools_to_gemini(tools)

        async def _request() -> ChatCompletionResult:
            last_error: Exception | None = None
            for model in self._chat_models():
                try:
                    result = await self._generate_with_model(model, contents, config)
                    if model != self.settings.gemini_chat_model:
                        logger.info("Gemini chat succeeded with fallback model %s", model)
                    return result
                except Exception as exc:
                    last_error = exc
                    if _should_try_next_chat_model(exc, model):
                        logger.warning("Gemini model %s unavailable, trying next: %s", model, exc)
                        continue
                    raise
            assert last_error is not None
            raise last_error

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
