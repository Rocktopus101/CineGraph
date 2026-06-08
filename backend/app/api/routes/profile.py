from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.taste import AnalyticsResponse, TasteProfileResponse
from app.services.list_generator_service import ListGeneratorService
from app.services.taste_profile_service import TasteProfileService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/taste", response_model=TasteProfileResponse)
async def get_taste(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = TasteProfileService(db)
    profile = await svc.get_profile(user.id)
    if not profile:
        return TasteProfileResponse(summary_text=None, insights_json=None, computed_at=None)
    return TasteProfileResponse.model_validate(profile)


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = TasteProfileService(db)
    data = await svc.get_analytics(user.id)
    return AnalyticsResponse(**data)


@router.post("/taste/refresh", response_model=TasteProfileResponse)
async def refresh_taste(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    taste = TasteProfileService(db)
    profile = await taste.compute_profile(user.id)
    lists = ListGeneratorService(db)
    await lists.generate_lists(user.id)
    return TasteProfileResponse.model_validate(profile)
