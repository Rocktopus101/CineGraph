import hashlib
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.movie import TmdbCache

TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"


class TmdbService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def poster_url(self, path: str | None, size: str = "w342") -> str | None:
        if not path:
            return None
        return f"{IMAGE_BASE}/{size}{path}"

    async def _cached_get(self, cache_key: str, url: str, params: dict) -> dict:
        result = await self.db.execute(
            select(TmdbCache).where(TmdbCache.cache_key == cache_key)
        )
        cached = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if cached and cached.expires_at > now:
            return cached.response_json

        params = {**params, "api_key": self.settings.tmdb_api_key}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        expires = now + timedelta(days=self.settings.tmdb_cache_ttl_days)
        if cached:
            cached.response_json = data
            cached.expires_at = expires
        else:
            self.db.add(TmdbCache(cache_key=cache_key, response_json=data, expires_at=expires))
        await self.db.flush()
        return data

    async def search_movie(self, query: str, year: int | None = None) -> dict:
        params: dict = {"query": query}
        if year:
            params["year"] = year
        key = f"search:{hashlib.md5(f'{query}:{year}'.encode()).hexdigest()}"
        return await self._cached_get(key, f"{TMDB_BASE}/search/movie", params)

    async def get_movie_details(self, tmdb_id: int) -> dict:
        key = f"details:{tmdb_id}"
        params = {"append_to_response": "credits"}
        return await self._cached_get(key, f"{TMDB_BASE}/movie/{tmdb_id}", params)

    async def get_similar(self, tmdb_id: int) -> dict:
        key = f"similar:{tmdb_id}"
        return await self._cached_get(key, f"{TMDB_BASE}/movie/{tmdb_id}/similar", {})
