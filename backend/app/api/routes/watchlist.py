from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.user_data import WatchlistItem
from app.schemas.movie import MovieSearchResult
from app.schemas.user_data import WatchlistCreateRequest, WatchlistItemResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.movie import Movie

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("/", response_model=list[WatchlistItemResponse])
async def get_watchlist(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(WatchlistItem, Movie)
        .join(Movie, WatchlistItem.movie_id == Movie.id)
        .where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.added_at.desc())
    )
    return [
        WatchlistItemResponse(
            id=wi.id,
            movie=MovieSearchResult.model_validate(m),
            added_at=wi.added_at,
        )
        for wi, m in result.all()
    ]


@router.post("/", response_model=WatchlistItemResponse)
async def add_to_watchlist(
    body: WatchlistCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Movie).where(Movie.id == body.movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(404, "Movie not found")

    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.movie_id == body.movie_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Already in watchlist")

    item = WatchlistItem(user_id=user.id, movie_id=body.movie_id)
    db.add(item)
    await db.flush()
    return WatchlistItemResponse(
        id=item.id,
        movie=MovieSearchResult.model_validate(movie),
        added_at=item.added_at,
    )


@router.delete("/{item_id}")
async def remove_from_watchlist(
    item_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    await db.delete(item)
    return {"ok": True}
