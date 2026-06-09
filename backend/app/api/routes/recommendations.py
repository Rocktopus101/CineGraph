import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.ai.agent import AgentService
from app.ai.providers import get_llm_provider
from app.ai.rate_limiter import is_rate_limit_error
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import ChatRequest, ChatResponse, GenerateRequest
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
            raise HTTPException(502, f"AI chat failed: {exc}") from exc
        await obs.complete_query(response)

    return ChatResponse(response=response, citations=citations, query_id=query_id)


@router.post("/generate", response_model=ChatResponse)
async def generate(
    body: GenerateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    obs = ObservabilityService(db)
    await obs.start_query(user.id, body.query)
    rec = RecommendationService(db, obs)
    response, citations = await rec.generate(user.id, body.query, body.filters)
    await obs.complete_query(response)
    return ChatResponse(response=response, citations=citations)
