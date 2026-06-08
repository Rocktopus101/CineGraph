from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.movie import MovieSearchResult
from app.schemas.user_data import ReviewItem
from app.services.history_service import HistoryService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/feed", response_model=list[ReviewItem])
async def review_feed(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, le=100),
):
    svc = HistoryService(db)
    rows = await svc.get_reviews(user.id, limit)
    return [
        ReviewItem(
            id=um.id,
            movie=MovieSearchResult.model_validate(m),
            review_text=um.review_text,
            rating=um.rating,
            watched_date=um.watched_date,
        )
        for um, m in rows
    ]
