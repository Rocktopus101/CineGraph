import asyncio
import json
import logging
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.core.config import get_settings
from app.ingestion.tmdb_matcher import TmdbMatcher
from app.models.movie import Movie
from app.models.user_data import UserMovie
from app.retrieval.retrieval_service import RetrievalService
from app.schemas.recommendation import Citation
from app.services.observability_service import ObservabilityService
from app.services.tmdb_service import TmdbService
from app.utils.movie_parse import parse_title_year_from_text

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: AsyncSession, obs: ObservabilityService | None = None):
        self.db = db
        self.provider = get_llm_provider()
        self.retrieval = RetrievalService(db)
        self.tmdb = TmdbService(db)
        self.tmdb_matcher = TmdbMatcher(db, self.tmdb)
        self.obs = obs

    async def _load_top_rated(self, user_id: int, limit: int = 10) -> list:
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
            .order_by(UserMovie.rating.desc())
            .limit(limit)
        )
        return result.all()

    async def _load_recent_watches(self, user_id: int, days: int = 31, limit: int = 20) -> list:
        cutoff = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(
                UserMovie.user_id == user_id,
                UserMovie.watched_date.isnot(None),
                UserMovie.watched_date >= cutoff,
            )
            .order_by(UserMovie.watched_date.desc())
            .limit(limit)
        )
        return result.all()

    def _format_history_lines(self, rows: list) -> str:
        return "\n".join(
            f"- {m.title} ({m.year}): rated {um.rating}, watched {um.watched_date}"
            for um, m in rows
        )

    def _history_context_for_query(self, query: str, recent: list, top_rated: list) -> str:
        lower = query.lower()
        wants_recent = any(
            phrase in lower
            for phrase in ("last month", "recent", "recently", "this month", "past month", "lately")
        )
        sections: list[str] = []
        if recent:
            sections.append(f"Recent watches (last ~30 days):\n{self._format_history_lines(recent)}")
        if wants_recent and not recent:
            sections.append("Recent watches (last ~30 days):\n- (none logged in this period)")
        if top_rated:
            sections.append(f"Top-rated overall:\n{self._format_history_lines(top_rated)}")
        return "\n\n".join(sections)

    def _static_fallback(self, history: list, query: str) -> str:
        if not history:
            return "Import or load sample data so I can recommend films based on your taste."
        favorites = ", ".join(m.title for _, m in history[:3])
        return (
            f"Based on your taste, I'd recommend exploring films similar to your favorites "
            f"({favorites}). You asked: {query}"
        )

    async def _retrieve_context(
        self, query: str, user_id: int, filters: dict | None
    ) -> str:
        settings = get_settings()
        if settings.chat_skip_retrieval:
            return ""

        if self.obs:
            self.obs.start_timer("retrieval")
        try:
            docs = await asyncio.wait_for(
                self.retrieval.retrieve(query, user_id, filters),
                timeout=settings.chat_retrieval_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("Chat retrieval skipped (%s)", exc)
            return ""

        if self.obs:
            await self.obs.log_event(
                "retrieval",
                {"docs": [{"movie_id": d.movie_id, "score": d.score, "type": d.source_type} for d in docs]},
                latency_ms=self.obs.elapsed_ms("retrieval"),
            )
        return "\n".join(f"- {d.citation_text} (score: {d.score:.2f})" for d in docs)

    async def generate(
        self,
        user_id: int,
        query: str,
        filters: dict | None = None,
        *,
        allow_fallback: bool = True,
    ) -> tuple[str, list[Citation]]:
        settings = get_settings()
        recent = await self._load_recent_watches(user_id)
        top_rated = await self._load_top_rated(user_id)
        history = recent or top_rated
        history_text = self._history_context_for_query(query, recent, top_rated)
        context = await self._retrieve_context(query, user_id, filters)

        if not self.provider.supports_chat:
            response = self._static_fallback(history, query)
            if self.obs:
                await self.obs.log_event("recommendation", {"citations": []})
            return response, []

        if self.obs:
            self.obs.start_timer("llm")

        user_content = f"Query: {query}\n\n{history_text}\n\nProvide thoughtful recommendations."
        if context:
            user_content = (
                f"Query: {query}\n\nRetrieved context:\n{context}\n\n"
                f"{history_text}\n\nProvide thoughtful recommendations."
            )

        try:
            resp = await self.provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are CineGraph, a movie recommendation assistant. Ground answers in the user's "
                            "actual viewing history. Write a complete answer in markdown: explain patterns you see, "
                            "cite specific films they watched by title, and suggest what to watch next with brief reasons. "
                            "Format each new recommendation as a numbered list item: "
                            "1. **Movie Title (Year):** reason. Do not output JSON or code blocks."
                        ),
                    },
                    {"role": "user", "content": user_content},
                ],
                max_tokens=settings.chat_max_output_tokens,
            )
        except Exception as exc:
            logger.warning("%s chat failed (%s)", self.provider.name, exc)
            if self.obs:
                await self.obs.log_event(
                    "recommendation_fallback",
                    {"reason": str(exc), "citations": []},
                )
            if not allow_fallback:
                raise
            return self._static_fallback(history, query), []

        text = resp.content or ""
        if not text.strip():
            logger.warning("%s chat returned empty content", self.provider.name)
            if not allow_fallback:
                raise RuntimeError(f"{self.provider.name} returned empty content")
            return self._static_fallback(history, query), []

        clean_text = self._strip_citations_json(text)
        extracted = self._extract_citations(text, user_id)
        validated = await self._validate_citations(extracted, user_id)
        citations = validated or await self._citations_from_recommendations(clean_text, user_id)

        if self.obs:
            await self.obs.log_event(
                "llm_call",
                {"provider": self.provider.name},
                latency_ms=self.obs.elapsed_ms("llm"),
                tokens_in=resp.usage.prompt_tokens if resp.usage else None,
                tokens_out=resp.usage.completion_tokens if resp.usage else None,
            )
            await self.obs.log_event(
                "recommendation",
                {"citations": [c.model_dump() for c in citations]},
            )

        return clean_text, citations

    async def quick_fallback(self, user_id: int, query: str) -> tuple[str, list[Citation]]:
        """Instant response when the full pipeline would exceed hosting timeouts."""
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
            .order_by(UserMovie.rating.desc())
            .limit(5)
        )
        history = result.all()
        citations = [
            Citation(
                movie_id=m.id,
                title=m.title,
                rating=um.rating,
                watched_date=str(um.watched_date) if um.watched_date else None,
            )
            for um, m in history[:3]
        ]
        if not history:
            return (
                "I couldn't finish a full analysis in time. Import or load sample data, then try again.",
                [],
            )
        favorites = ", ".join(m.title for _, m in history[:3])
        response = (
            f"I ran out of time for a deep answer, but based on your highest-rated films "
            f"({favorites}), try something in a similar vein for: {query}"
        )
        if self.obs:
            await self.obs.log_event("recommendation_fallback", {"citations": [c.model_dump() for c in citations]})
        return response, citations

    def _strip_citations_json(self, text: str) -> str:
        """Remove a trailing citations JSON block without touching the main prose."""
        stripped = re.sub(
            r'```json\s*\{["\']citations["\'].*?\}\s*```\s*$',
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        return re.sub(
            r'\{["\']citations["\']\s*:\s*\[.*?\]\s*\}\s*$',
            "",
            stripped,
            flags=re.DOTALL,
        ).strip()

    def _extract_recommendation_titles(self, text: str, limit: int = 8) -> list[tuple[str, int | None]]:
        """Parse numbered list items from the model response into (title, year) pairs."""
        titles: list[tuple[str, int | None]] = []
        seen: set[str] = set()
        for line in text.splitlines():
            list_match = re.match(r"^\s*\d+\.\s+(.+)$", line.strip())
            if not list_match:
                continue
            title, year = parse_title_year_from_text(list_match.group(1))
            if len(title) > 80:
                continue
            if not title or len(title) < 2:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            titles.append((title, year))
            if len(titles) >= limit:
                break
        return titles

    async def _watched_title_keys(self, user_id: int) -> set[str]:
        result = await self.db.execute(
            select(Movie.title)
            .join(UserMovie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id)
        )
        return {row[0].lower() for row in result.all() if row[0]}

    async def _citations_from_recommendations(
        self, text: str, user_id: int, limit: int = 6
    ) -> list[Citation]:
        settings = get_settings()
        watched = await self._watched_title_keys(user_id)
        citations: list[Citation] = []
        seen_movie_ids: set[int] = set()

        for title, year in self._extract_recommendation_titles(text, limit=limit):
            if title.lower() in watched:
                continue
            try:
                if settings.tmdb_api_key:
                    movie = await self.tmdb_matcher.find_or_create_movie(title, year, None)
                    movie = await self.tmdb_matcher.enrich_movie(movie)
                else:
                    movie = await self._find_local_movie(title, year)
                    if not movie:
                        movie = Movie(title=title, year=year)
                        self.db.add(movie)
                        await self.db.flush()
            except Exception as exc:
                logger.warning("Could not resolve recommendation %s (%s): %s", title, year, exc)
                continue
            if movie.id in seen_movie_ids:
                continue
            chip_title = movie.title if len(movie.title) <= 80 else title
            citations.append(
                Citation(
                    movie_id=movie.id,
                    title=chip_title,
                    rating=None,
                    watched_date=None,
                )
            )
            seen_movie_ids.add(movie.id)
        return citations

    async def _find_local_movie(self, title: str, year: int | None) -> Movie | None:
        result = await self.db.execute(select(Movie).where(Movie.title.ilike(title)))
        for movie in result.scalars():
            if year is None or movie.year is None or abs(movie.year - year) <= 1:
                return movie
        return None

    def _extract_citations(self, text: str, user_id: int) -> list[Citation]:
        match = re.search(r'\{["\']citations["\']\s*:\s*\[.*?\]\s*\}', text, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group())
            return [Citation(**c) for c in data.get("citations", [])]
        except (json.JSONDecodeError, TypeError):
            return []

    async def _validate_citations(self, citations: list[Citation], user_id: int) -> list[Citation]:
        valid = []
        for c in citations:
            result = await self.db.execute(
                select(UserMovie, Movie)
                .join(Movie, UserMovie.movie_id == Movie.id)
                .where(UserMovie.user_id == user_id, UserMovie.movie_id == c.movie_id)
            )
            row = result.first()
            if row:
                um, m = row
                valid.append(
                    Citation(
                        movie_id=m.id,
                        title=m.title,
                        rating=um.rating,
                        watched_date=str(um.watched_date) if um.watched_date else None,
                    )
                )
        return valid
