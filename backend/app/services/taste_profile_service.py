import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.models.movie import Movie
from app.models.taste import TasteProfile, TasteStat
from app.models.user_data import UserMovie

logger = logging.getLogger(__name__)


class TasteProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_llm_provider()

    async def compute_profile(self, user_id: int, *, use_llm: bool = True) -> TasteProfile:
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id)
        )
        rows = result.all()

        genre_scores: dict[str, float] = defaultdict(float)
        genre_counts: dict[str, int] = defaultdict(int)
        decade_counts: dict[str, int] = defaultdict(int)
        director_scores: dict[str, float] = defaultdict(float)
        monthly: dict[str, int] = defaultdict(int)
        ratings_by_genre: dict[str, list[float]] = defaultdict(list)

        for um, movie in rows:
            genres = (movie.metadata_json or {}).get("genres", [])
            directors = (movie.metadata_json or {}).get("directors", [])
            weight = (um.rating or 3.0) * 1.0
            for g in genres:
                genre_scores[g] += weight
                genre_counts[g] += 1
                if um.rating:
                    ratings_by_genre[g].append(um.rating)
            for d in directors:
                director_scores[d] += weight
            if movie.year:
                decade = f"{(movie.year // 10) * 10}s"
                decade_counts[decade] += 1
            if um.watched_date:
                monthly[um.watched_date.strftime("%Y-%m")] += 1

        top_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        top_directors = sorted(director_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        avg_by_genre = [
            {"genre": g, "avg_rating": sum(rs) / len(rs)}
            for g, rs in ratings_by_genre.items()
            if rs
        ]
        all_genres = set(genre_counts.keys())
        catalog_genres = {"Drama", "Comedy", "Action", "Thriller", "Horror", "Sci-Fi", "Romance", "Documentary"}
        avoided = [
            {"genre": g, "count": genre_counts.get(g, 0)}
            for g in catalog_genres - all_genres
        ]

        insights = {
            "top_genres": [{"genre": g, "score": s} for g, s in top_genres],
            "top_directors": [{"director": d, "score": s} for d, s in top_directors],
            "decades": [{"decade": d, "count": c} for d, c in sorted(decade_counts.items())],
            "monthly_activity": [{"month": m, "count": c} for m, c in sorted(monthly.items())],
            "avg_rating_by_genre": avg_by_genre,
            "avoided_genres": avoided,
        }

        summary = await self._generate_summary(insights, use_llm=use_llm)

        await self.db.execute(delete(TasteStat).where(TasteStat.user_id == user_id))
        for g, s in top_genres:
            self.db.add(TasteStat(user_id=user_id, stat_type="genre", stat_key=g, stat_value=s))
        for d, s in top_directors:
            self.db.add(TasteStat(user_id=user_id, stat_type="director", stat_key=d, stat_value=s))

        result = await self.db.execute(
            select(TasteProfile).where(TasteProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.summary_text = summary
            profile.insights_json = insights
            profile.computed_at = datetime.now(timezone.utc)
        else:
            profile = TasteProfile(
                user_id=user_id,
                summary_text=summary,
                insights_json=insights,
            )
            self.db.add(profile)
        await self.db.flush()
        return profile

    def _fallback_summary(self, insights: dict) -> str:
        genres = insights.get("top_genres", [])[:3]
        names = ", ".join(g["genre"] for g in genres)
        return (
            f"You enjoy films across many genres, with particular affinity for "
            f"{names or 'cinematic storytelling'}."
        )

    def _compact_insights(self, insights: dict) -> dict:
        return {
            "top_genres": insights.get("top_genres", [])[:5],
            "top_directors": insights.get("top_directors", [])[:5],
            "decades": insights.get("decades", [])[:5],
            "avg_rating_by_genre": insights.get("avg_rating_by_genre", [])[:5],
        }

    async def _generate_summary(self, insights: dict, *, use_llm: bool = True) -> str:
        if not use_llm or not self.provider.supports_chat:
            return self._fallback_summary(insights)
        try:
            compact = self._compact_insights(insights)
            prompt = (
                "Write a 3-5 sentence taste profile summary based on these stats: "
                f"{compact}"
            )
            resp = await asyncio.wait_for(
                self.provider.chat_completion(
                    messages=[
                        {"role": "system", "content": "You summarize movie taste profiles concisely."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=200,
                ),
                timeout=30.0,
            )
            return resp.content or self._fallback_summary(insights)
        except Exception as exc:
            logger.warning(
                "%s taste summary failed (%s); using fallback text",
                self.provider.name,
                exc,
            )
            return self._fallback_summary(insights)

    async def get_profile(self, user_id: int) -> TasteProfile | None:
        result = await self.db.execute(
            select(TasteProfile).where(TasteProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_analytics(self, user_id: int) -> dict:
        profile = await self.get_profile(user_id)
        if not profile or not profile.insights_json:
            return {
                "genres": [],
                "decades": [],
                "monthly_activity": [],
                "top_directors": [],
                "average_rating_by_genre": [],
                "avoided_genres": [],
            }
        ins = profile.insights_json
        return {
            "genres": ins.get("top_genres", []),
            "decades": ins.get("decades", []),
            "monthly_activity": ins.get("monthly_activity", []),
            "top_directors": ins.get("top_directors", []),
            "average_rating_by_genre": ins.get("avg_rating_by_genre", []),
            "avoided_genres": ins.get("avoided_genres", []),
        }
