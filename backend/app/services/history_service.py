from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.user_data import UserMovie


class HistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_history(
        self,
        user_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        genre: str | None = None,
        min_rating: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[UserMovie, Movie]]:
        query = (
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id)
        )
        if date_from:
            query = query.where(UserMovie.watched_date >= date_from)
        if date_to:
            query = query.where(UserMovie.watched_date <= date_to)
        if min_rating:
            query = query.where(UserMovie.rating >= min_rating)
        query = query.order_by(UserMovie.watched_date.desc().nullslast()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        rows = result.all()
        if genre:
            filtered = []
            for um, m in rows:
                genres = (m.metadata_json or {}).get("genres", [])
                if genre in genres:
                    filtered.append((um, m))
            return filtered
        return list(rows)

    async def get_top_rated(self, user_id: int, limit: int = 20, genre: str | None = None) -> list[tuple[UserMovie, Movie]]:
        return await self.get_history(user_id, min_rating=4.0, limit=limit * 2 if genre else limit)[:limit]

    async def get_reviews(self, user_id: int, limit: int = 50) -> list[tuple[UserMovie, Movie]]:
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id, UserMovie.review_text.isnot(None))
            .order_by(UserMovie.watched_date.desc().nullslast())
            .limit(limit)
        )
        return list(result.all())
