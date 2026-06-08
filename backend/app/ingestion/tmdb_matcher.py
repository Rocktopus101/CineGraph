import difflib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.services.tmdb_service import TmdbService


class TmdbMatcher:
    def __init__(self, db: AsyncSession, tmdb: TmdbService):
        self.db = db
        self.tmdb = tmdb

    async def find_or_create_movie(self, title: str, year: int | None, letterboxd_uri: str | None) -> Movie:
        if letterboxd_uri:
            result = await self.db.execute(
                select(Movie).where(Movie.letterboxd_uri == letterboxd_uri)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        result = await self.db.execute(
            select(Movie).where(Movie.title.ilike(title))
        )
        candidates = result.scalars().all()
        for c in candidates:
            if year and c.year and abs(c.year - year) <= 1:
                return c

        tmdb_result = await self.tmdb.search_movie(title, year)
        if not tmdb_result:
            movie = Movie(title=title, year=year, letterboxd_uri=letterboxd_uri)
            self.db.add(movie)
            await self.db.flush()
            return movie

        best = self._pick_best_match(title, year, tmdb_result.get("results", []))
        if not best:
            movie = Movie(title=title, year=year, letterboxd_uri=letterboxd_uri)
            self.db.add(movie)
            await self.db.flush()
            return movie

        tmdb_id = best["id"]
        result = await self.db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
        existing = result.scalar_one_or_none()
        if existing:
            if letterboxd_uri and not existing.letterboxd_uri:
                existing.letterboxd_uri = letterboxd_uri
            return existing

        details = await self.tmdb.get_movie_details(tmdb_id)
        movie = self._movie_from_tmdb(details, letterboxd_uri)
        self.db.add(movie)
        await self.db.flush()
        return movie

    def _pick_best_match(self, title: str, year: int | None, results: list[dict]) -> dict | None:
        if not results:
            return None
        best_score = 0.0
        best = None
        for r in results:
            r_title = r.get("title", "")
            r_year = int(r.get("release_date", "0000")[:4]) if r.get("release_date") else None
            sim = difflib.SequenceMatcher(None, title.lower(), r_title.lower()).ratio()
            if year and r_year and abs(year - r_year) <= 1:
                sim += 0.3
            elif year and r_year and year != r_year:
                sim -= 0.2
            if sim > best_score:
                best_score = sim
                best = r
        return best if best_score > 0.5 else (results[0] if results else None)

    def _movie_from_tmdb(self, details: dict, letterboxd_uri: str | None) -> Movie:
        release = details.get("release_date", "")
        year = int(release[:4]) if release and len(release) >= 4 else None
        genres = [g["name"] for g in details.get("genres", [])]
        cast = [c["name"] for c in details.get("credits", {}).get("cast", [])[:10]]
        directors = [
            c["name"]
            for c in details.get("credits", {}).get("crew", [])
            if c.get("job") == "Director"
        ]
        return Movie(
            tmdb_id=details["id"],
            title=details.get("title", ""),
            original_title=details.get("original_title"),
            year=year,
            runtime=details.get("runtime"),
            overview=details.get("overview"),
            poster_path=details.get("poster_path"),
            backdrop_path=details.get("backdrop_path"),
            release_date=release,
            vote_average=details.get("vote_average"),
            letterboxd_uri=letterboxd_uri,
            metadata_json={"genres": genres, "cast": cast, "directors": directors},
        )
