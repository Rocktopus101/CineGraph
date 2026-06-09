import asyncio
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.core.config import get_settings
from app.models.movie import Movie
from app.models.user_data import UserMovie
from app.retrieval.retrieval_service import RetrievalService
from app.schemas.recommendation import Citation
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: AsyncSession, obs: ObservabilityService | None = None):
        self.db = db
        self.provider = get_llm_provider()
        self.retrieval = RetrievalService(db)
        self.obs = obs

    async def _load_history(self, user_id: int) -> tuple[list, list[Citation]]:
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id, UserMovie.rating.isnot(None))
            .order_by(UserMovie.rating.desc())
            .limit(10)
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
        return history, citations

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
        history, citations = await self._load_history(user_id)
        history_text = "\n".join(
            f"- {m.title} ({m.year}): rated {um.rating}" for um, m in history
        )
        context = await self._retrieve_context(query, user_id, filters)

        if not self.provider.supports_chat:
            response = self._static_fallback(history, query)
            if self.obs:
                await self.obs.log_event("recommendation", {"citations": [c.model_dump() for c in citations]})
            return response, citations

        if self.obs:
            self.obs.start_timer("llm")

        user_content = f"Query: {query}\n\nUser history:\n{history_text}\n\nProvide recommendations with citations."
        if context:
            user_content = (
                f"Query: {query}\n\nRetrieved context:\n{context}\n\n"
                f"User history:\n{history_text}\n\nProvide recommendations with citations."
            )

        try:
            resp = await self.provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a movie recommendation assistant. Ground all recommendations in the user's "
                            "viewing history. Include a JSON block at the end with citations: "
                            '{"citations": [{"movie_id": N, "title": "...", "rating": N, "watched_date": "..."}]}'
                        ),
                    },
                    {"role": "user", "content": user_content},
                ],
                max_tokens=800,
            )
        except Exception as exc:
            logger.warning("%s chat failed (%s)", self.provider.name, exc)
            if self.obs:
                await self.obs.log_event(
                    "recommendation_fallback",
                    {"reason": str(exc), "citations": [c.model_dump() for c in citations]},
                )
            if not allow_fallback:
                raise
            return self._static_fallback(history, query), citations

        text = resp.content or ""
        if not text.strip():
            logger.warning("%s chat returned empty content", self.provider.name)
            if not allow_fallback:
                raise RuntimeError(f"{self.provider.name} returned empty content")
            return self._static_fallback(history, query), citations

        extracted = self._extract_citations(text, user_id)
        validated = await self._validate_citations(extracted, user_id)
        if validated:
            citations = validated
        clean_text = re.sub(r'\{["\']citations["\'].*\}', "", text, flags=re.DOTALL).strip()

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
