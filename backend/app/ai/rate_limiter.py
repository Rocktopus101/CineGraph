import asyncio
import logging
import re
import time
from collections import deque
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRY_DELAY_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)


class EmbeddingRateLimiter:
    """Sliding-window limiter shared across all embedding API calls."""

    def __init__(self, rpm_limit: int = 60):
        self.rpm_limit = max(1, rpm_limit)
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= 60.0:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.rpm_limit:
                wait = 60.0 - (now - self._timestamps[0]) + 0.25
                logger.info("Embedding rate limit: waiting %.1fs", wait)
                await asyncio.sleep(wait)
                return await self.acquire()

            self._timestamps.append(time.monotonic())


_limiter: EmbeddingRateLimiter | None = None


def get_embedding_rate_limiter(rpm_limit: int) -> EmbeddingRateLimiter:
    global _limiter
    if _limiter is None or _limiter.rpm_limit != rpm_limit:
        _limiter = EmbeddingRateLimiter(rpm_limit)
    return _limiter


def parse_retry_delay(error: Exception) -> float | None:
    match = _RETRY_DELAY_RE.search(str(error))
    if match:
        return float(match.group(1))
    return None


def is_rate_limit_error(error: Exception) -> bool:
    msg = str(error)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


def is_transient_llm_error(error: Exception) -> bool:
    msg = str(error)
    lower = msg.lower()
    return (
        is_rate_limit_error(error)
        or "503" in msg
        or "unavailable" in lower
        or "high demand" in lower
        or "overloaded" in lower
        or "internal" in lower and "500" in msg
    )


async def with_embedding_retry(
    fn: Callable[[], T],
    *,
    rpm_limit: int,
    max_retries: int,
    min_delay_seconds: float,
) -> T:
    limiter = get_embedding_rate_limiter(rpm_limit)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            await limiter.acquire()
            await asyncio.sleep(min_delay_seconds)
            return await fn()
        except Exception as exc:
            last_error = exc
            if not is_rate_limit_error(exc):
                raise
            delay = parse_retry_delay(exc) or min(120.0, 5.0 * (2**attempt))
            logger.warning(
                "Embedding rate limited (attempt %d/%d), retrying in %.1fs",
                attempt + 1,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error


async def with_chat_retry(
    fn: Callable[[], T],
    *,
    max_retries: int,
    base_delay_seconds: float,
    max_delay_seconds: float = 15.0,
) -> T:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            return await fn()
        except Exception as exc:
            last_error = exc
            if not is_transient_llm_error(exc):
                raise
            if attempt == max_retries - 1:
                break
            raw_delay = parse_retry_delay(exc) or min(60.0, base_delay_seconds * (2**attempt))
            delay = min(raw_delay, max_delay_seconds)
            logger.warning(
                "Chat transient error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error
