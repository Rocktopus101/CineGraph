from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.recommendation import ChatRequest, ChatResponse, GenerateRequest
from app.services.observability_service import ObservabilityService
from app.services.recommendation_service import RecommendationService
from app.ai.agent import AgentService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    obs = ObservabilityService(db)
    agent = AgentService(db, obs)
    response, citations, query_id = await agent.chat(user.id, body.message)
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
