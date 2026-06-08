from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.movie import MovieSearchResult
from app.schemas.user_data import HistoryItem
from app.services.history_service import HistoryService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/", response_model=list[HistoryItem])
async def get_history(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = None,
    date_to: date | None = None,
    genre: str | None = None,
    min_rating: float | None = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    svc = HistoryService(db)
    rows = await svc.get_history(user.id, date_from, date_to, genre, min_rating, limit, offset)
    return [
        HistoryItem(
            id=um.id,
            movie=MovieSearchResult.model_validate(m),
            watched_date=um.watched_date,
            rating=um.rating,
            review_text=um.review_text,
            source=um.source,
        )
        for um, m in rows
    ]


@router.get("/top-rated", response_model=list[HistoryItem])
async def get_top_rated(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, le=50),
    genre: str | None = None,
):
    svc = HistoryService(db)
    rows = await svc.get_history(user.id, min_rating=3.5, limit=limit, genre=genre)
    rows.sort(key=lambda x: x[0].rating or 0, reverse=True)
    return [
        HistoryItem(
            id=um.id,
            movie=MovieSearchResult.model_validate(m),
            watched_date=um.watched_date,
            rating=um.rating,
            review_text=um.review_text,
            source=um.source,
        )
        for um, m in rows[:limit]
    ]
