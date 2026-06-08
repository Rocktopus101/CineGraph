from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIQuery, AIQueryEvent
from app.models.user_data import UserMovie


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_metrics(self) -> dict:
        retrieval_result = await self.db.execute(
            select(AIQueryEvent).where(AIQueryEvent.event_type == "retrieval")
        )
        retrievals = retrieval_result.scalars().all()
        scores = []
        for ev in retrievals:
            payload = ev.payload_json or {}
            for doc in payload.get("docs", []):
                if doc.get("score"):
                    scores.append(doc["score"])

        avg_similarity = sum(scores) / len(scores) if scores else 0.0

        rec_result = await self.db.execute(
            select(AIQueryEvent).where(AIQueryEvent.event_type == "recommendation")
        )
        recs = rec_result.scalars().all()
        citation_total = 0
        citation_valid = 0
        for ev in recs:
            payload = ev.payload_json or {}
            citations = payload.get("citations", [])
            citation_total += len(citations)
            for c in citations:
                if c.get("movie_id"):
                    um_result = await self.db.execute(
                        select(UserMovie).where(UserMovie.movie_id == c["movie_id"]).limit(1)
                    )
                    if um_result.scalar_one_or_none():
                        citation_valid += 1

        coverage = (citation_valid / citation_total * 100) if citation_total else 0.0

        return {
            "avg_top_k_similarity": round(avg_similarity, 4),
            "retrieval_count": len(retrievals),
            "citation_coverage_pct": round(coverage, 2),
            "total_recommendations": len(recs),
        }

    async def get_recent_retrievals(self, limit: int = 20) -> list[dict]:
        result = await self.db.execute(
            select(AIQueryEvent)
            .where(AIQueryEvent.event_type == "retrieval")
            .order_by(AIQueryEvent.id.desc())
            .limit(limit)
        )
        output = []
        for ev in result.scalars().all():
            payload = ev.payload_json or {}
            output.append({
                "event_id": ev.id,
                "query_id": ev.query_id,
                "docs": payload.get("docs", [])[:5],
                "latency_ms": ev.latency_ms,
            })
        return output
