from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.evaluation_service import EvaluationService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/metrics")
async def get_metrics(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EvaluationService(db)
    return await svc.get_metrics()


@router.get("/recent-retrievals")
async def recent_retrievals(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, le=50),
):
    svc = EvaluationService(db)
    return await svc.get_recent_retrievals(limit)
