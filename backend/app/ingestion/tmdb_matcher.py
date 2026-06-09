import difflib
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.movie import Movie
from app.services.tmdb_service import TmdbService
from app.utils.movie_parse import looks_like_bloated_title, parse_title_year_from_text

logger = logging.getLogger(__name__)


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
            if looks_like_bloated_title(c.title):
                continue
            if year and c.year and abs(c.year - year) <= 1:
                return await self.enrich_movie(c)
            if not year:
                return await self.enrich_movie(c)

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
            return await self.enrich_movie(existing)

        details = await self.tmdb.get_movie_details(tmdb_id)
        movie = self._movie_from_tmdb(details, letterboxd_uri)
        self.db.add(movie)
        await self.db.flush()
        return movie

    def _apply_tmdb_details(self, movie: Movie, details: dict, *, set_tmdb_id: bool = True) -> None:
        release = details.get("release_date", "")
        year = int(release[:4]) if release and len(release) >= 4 else None
        genres = [g["name"] for g in details.get("genres", [])]
        cast = [c["name"] for c in details.get("credits", {}).get("cast", [])[:10]]
        directors = [
            c["name"]
            for c in details.get("credits", {}).get("crew", [])
            if c.get("job") == "Director"
        ]
        if set_tmdb_id:
            movie.tmdb_id = details["id"]
        movie.title = details.get("title", movie.title)
        movie.original_title = details.get("original_title")
        movie.year = year or movie.year
        movie.runtime = details.get("runtime")
        movie.overview = details.get("overview")
        movie.poster_path = details.get("poster_path")
        movie.backdrop_path = details.get("backdrop_path")
        movie.release_date = release or movie.release_date
        movie.vote_average = details.get("vote_average")
        movie.metadata_json = {"genres": genres, "cast": cast, "directors": directors}

    async def _trim_bloated_title(self, movie: Movie) -> None:
        if not looks_like_bloated_title(movie.title):
            return
        search_title, search_year = parse_title_year_from_text(movie.title)
        if search_title and not looks_like_bloated_title(search_title):
            movie.title = search_title
            if search_year:
                movie.year = search_year
            await self.db.flush()

    async def enrich_movie(self, movie: Movie) -> Movie:
        """Fill poster/overview/metadata from TMDB for stub or corrupted records."""
        await self._trim_bloated_title(movie)

        settings = get_settings()
        if not settings.tmdb_api_key:
            return movie

        needs_enrich = (
            not movie.tmdb_id
            or not movie.poster_path
            or not movie.overview
            or looks_like_bloated_title(movie.title)
        )
        if not needs_enrich:
            return movie

        search_title, search_year = parse_title_year_from_text(movie.title)
        if movie.year and not search_year:
            search_year = movie.year

        if movie.tmdb_id:
            try:
                details = await self.tmdb.get_movie_details(movie.tmdb_id)
                self._apply_tmdb_details(movie, details)
                await self.db.flush()
                return movie
            except Exception as exc:
                logger.warning("TMDB refresh failed for movie %s: %s", movie.id, exc)

        try:
            tmdb_result = await self.tmdb.search_movie(search_title, search_year)
        except Exception as exc:
            logger.warning("TMDB search failed for %s (%s): %s", search_title, search_year, exc)
            return movie

        best = self._pick_best_match(search_title, search_year, tmdb_result.get("results", []))
        if not best:
            if looks_like_bloated_title(movie.title):
                movie.title = search_title
                if search_year:
                    movie.year = search_year
                await self.db.flush()
            return movie

        tmdb_id = best["id"]
        result = await self.db.execute(select(Movie).where(Movie.tmdb_id == tmdb_id))
        existing = result.scalar_one_or_none()

        try:
            details = await self.tmdb.get_movie_details(tmdb_id)
        except Exception as exc:
            logger.warning("TMDB details failed for %s: %s", tmdb_id, exc)
            return movie

        if existing and existing.id != movie.id:
            self._apply_tmdb_details(movie, details, set_tmdb_id=False)
        else:
            self._apply_tmdb_details(movie, details, set_tmdb_id=True)

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
        movie = Movie(letterboxd_uri=letterboxd_uri)
        self._apply_tmdb_details(movie, details)
        return movie
