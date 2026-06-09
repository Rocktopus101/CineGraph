import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.ai.agent import AgentService
from app.ai.providers import get_llm_provider
from app.ai.rate_limiter import is_rate_limit_error, is_transient_llm_error
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    ChatHistoryDetail,
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    Citation,
    GenerateRequest,
)
from app.services.observability_service import ObservabilityService
from app.services.recommendation_service import RecommendationService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    settings = get_settings()
    provider = get_llm_provider()
    if not provider.supports_chat:
        logger.error("Chat unavailable: LLM provider %s has no API key", provider.name)
        raise HTTPException(
            503,
            "AI chat is not configured. Set GEMINI_API_KEY on the backend.",
        )

    obs = ObservabilityService(db)

    if settings.chat_use_agent:
        agent = AgentService(db, obs)
        response, citations, query_id = await agent.chat(user.id, body.message)
    else:
        query_id = await obs.start_query(user.id, body.message)
        rec = RecommendationService(db, obs)
        try:
            response, citations = await rec.generate(
                user.id, body.message, allow_fallback=False
            )
        except Exception as exc:
            logger.exception("Chat LLM failed for user %s", user.id)
            if is_rate_limit_error(exc):
                raise HTTPException(
                    429,
                    "Gemini free-tier quota exceeded. Wait about a minute and try again, "
                    "or check usage at https://ai.dev/rate-limit. "
                    "Free tier supports Flash models (e.g. gemini-2.5-flash), not deprecated 2.0 models.",
                ) from exc
            if is_transient_llm_error(exc):
                raise HTTPException(
                    503,
                    "Gemini is temporarily overloaded. We already tried fallback models — please wait a moment and try again.",
                ) from exc
            raise HTTPException(502, f"AI chat failed: {exc}") from exc
        await obs.complete_query(response)

    return ChatResponse(response=response, citations=citations, query_id=query_id)


def _preview(text: str | None, max_len: int = 120) -> str | None:
    if not text:
        return None
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= max_len else f"{one_line[: max_len - 1].rstrip()}…"


@router.get("/history", response_model=list[ChatHistoryItem])
async def chat_history(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    obs = ObservabilityService(db)
    queries = await obs.get_user_queries(user.id, limit=min(limit, 100), offset=offset)
    return [
        ChatHistoryItem(
            id=q.id,
            query_text=q.query_text,
            response_preview=_preview(q.response_text),
            created_at=q.created_at,
        )
        for q in queries
    ]


@router.get("/history/{query_id}", response_model=ChatHistoryDetail)
async def chat_history_detail(
    query_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    obs = ObservabilityService(db)
    query = await obs.get_user_query(user.id, query_id)
    if not query or not query.response_text:
        raise HTTPException(404, "Chat not found")
    raw_citations = await obs.get_query_citations(query_id)
    citations = [Citation(**c) for c in raw_citations if isinstance(c, dict) and "movie_id" in c]
    return ChatHistoryDetail(
        id=query.id,
        query_text=query.query_text,
        response_text=query.response_text,
        citations=citations,
        created_at=query.created_at,
    )


@router.delete("/history/{query_id}", status_code=204)
async def delete_chat_history(
    query_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    obs = ObservabilityService(db)
    if not await obs.delete_user_query(user.id, query_id):
        raise HTTPException(404, "Chat not found")


@router.post("/generate", response_model=ChatResponse)
async def generate(
    body: GenerateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    obs = ObservabilityService(db)
    query_id = await obs.start_query(user.id, body.query)
    rec = RecommendationService(db, obs)
    response, citations = await rec.generate(user.id, body.query, body.filters)
    await obs.complete_query(response)
    return ChatResponse(response=response, citations=citations, query_id=query_id)
