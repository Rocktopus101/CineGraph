from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.user_data import UserMovie, WatchlistItem
from app.retrieval.retrieval_service import RetrievalService
from app.services.tmdb_service import TmdbService


class MovieService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tmdb = TmdbService(db)
        self.retrieval = RetrievalService(db)

    async def search(self, query: str, limit: int = 20) -> list[Movie]:
        result = await self.db.execute(
            select(Movie)
            .where(or_(Movie.title.ilike(f"%{query}%"), Movie.overview.ilike(f"%{query}%")))
            .limit(limit)
        )
        local = list(result.scalars().all())
        if len(local) >= limit:
            return local

        from app.core.config import get_settings
        if get_settings().tmdb_api_key:
            data = await self.tmdb.search_movie(query)
            for r in data.get("results", [])[:limit - len(local)]:
                existing = await self.db.execute(
                    select(Movie).where(Movie.tmdb_id == r["id"])
                )
                if existing.scalar_one_or_none():
                    continue
                year = int(r["release_date"][:4]) if r.get("release_date") else None
                movie = Movie(
                    tmdb_id=r["id"],
                    title=r.get("title", ""),
                    year=year,
                    overview=r.get("overview"),
                    poster_path=r.get("poster_path"),
                    vote_average=r.get("vote_average"),
                )
                self.db.add(movie)
            await self.db.flush()
            result = await self.db.execute(
                select(Movie).where(Movie.title.ilike(f"%{query}%")).limit(limit)
            )
            return list(result.scalars().all())
        return local

    async def get_detail(self, movie_id: int, user_id: int | None = None) -> Movie | None:
        result = await self.db.execute(select(Movie).where(Movie.id == movie_id))
        return result.scalar_one_or_none()

    async def get_user_context(self, movie_id: int, user_id: int) -> dict:
        um_result = await self.db.execute(
            select(UserMovie).where(UserMovie.user_id == user_id, UserMovie.movie_id == movie_id)
        )
        um = um_result.scalar_one_or_none()
        wl_result = await self.db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id, WatchlistItem.movie_id == movie_id
            )
        )
        in_watchlist = wl_result.scalar_one_or_none() is not None
        return {
            "user_rating": um.rating if um else None,
            "user_review": um.review_text if um else None,
            "watched_date": str(um.watched_date) if um and um.watched_date else None,
            "in_watchlist": in_watchlist,
        }

    async def get_similar(self, movie_id: int, limit: int = 10) -> list[dict]:
        docs = await self.retrieval.find_similar_movies(movie_id, limit)
        output = []
        for doc in docs:
            result = await self.db.execute(select(Movie).where(Movie.id == doc.movie_id))
            m = result.scalar_one_or_none()
            if m:
                output.append({
                    "id": m.id,
                    "title": m.title,
                    "year": m.year,
                    "poster_path": m.poster_path,
                    "score": doc.score,
                })
        return output
