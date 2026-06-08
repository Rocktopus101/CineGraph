from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_admin_user
from app.core.database import get_db
from app.models.user import User
from app.services.observability_service import ObservabilityService
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/admin/ai", tags=["admin"])


class QuerySummary(BaseModel):
    id: int
    user_id: int
    query_text: str
    response_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventSummary(BaseModel):
    id: int
    query_id: int
    event_type: str
    payload_json: dict | None
    latency_ms: int | None
    tokens_in: int | None
    tokens_out: int | None

    model_config = {"from_attributes": True}


@router.get("/queries", response_model=list[QuerySummary])
async def list_queries(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
):
    svc = ObservabilityService(db)
    queries = await svc.get_queries(page, page_size)
    return [QuerySummary.model_validate(q) for q in queries]


@router.get("/queries/{query_id}/events", response_model=list[EventSummary])
async def query_events(
    query_id: int,
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ObservabilityService(db)
    events = await svc.get_query_events(query_id)
    return [EventSummary.model_validate(e) for e in events]


@router.get("/stats")
async def aggregate_stats(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ObservabilityService(db)
    return await svc.get_aggregate_stats()
