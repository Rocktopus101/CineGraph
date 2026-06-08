import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.agent import AgentService
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
    obs = ObservabilityService(db)

    async def run_chat() -> tuple[str, list, int]:
        if settings.chat_use_agent:
            agent = AgentService(db, obs)
            return await agent.chat(user.id, body.message)

        query_id = await obs.start_query(user.id, body.message)
        rec = RecommendationService(db, obs)
        response, citations = await rec.generate(user.id, body.message)
        await obs.complete_query(response)
        return response, citations, query_id

    try:
        response, citations, query_id = await asyncio.wait_for(
            run_chat(),
            timeout=settings.chat_request_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Chat timed out after %.0fs for user %s; using quick fallback",
            settings.chat_request_timeout_seconds,
            user.id,
        )
        query_id = await obs.start_query(user.id, body.message)
        rec = RecommendationService(db, obs)
        response, citations = await rec.quick_fallback(user.id, body.message)
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
