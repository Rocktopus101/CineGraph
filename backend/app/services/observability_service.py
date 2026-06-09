import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIQuery, AIQueryEvent


class ObservabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._query_id: int | None = None
        self._start_times: dict[str, float] = {}

    async def start_query(self, user_id: int, query_text: str) -> int:
        q = AIQuery(user_id=user_id, query_text=query_text)
        self.db.add(q)
        await self.db.flush()
        self._query_id = q.id
        return q.id

    async def log_event(
        self,
        event_type: str,
        payload: dict | None = None,
        latency_ms: int | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> None:
        if not self._query_id:
            return
        self.db.add(
            AIQueryEvent(
                query_id=self._query_id,
                event_type=event_type,
                payload_json=payload,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
        )
        await self.db.flush()

    def start_timer(self, key: str) -> None:
        self._start_times[key] = time.monotonic()

    def elapsed_ms(self, key: str) -> int:
        start = self._start_times.pop(key, None)
        if start is None:
            return 0
        return int((time.monotonic() - start) * 1000)

    async def complete_query(self, response_text: str) -> None:
        if not self._query_id:
            return
        result = await self.db.execute(select(AIQuery).where(AIQuery.id == self._query_id))
        q = result.scalar_one()
        q.response_text = response_text
        await self.db.flush()

    async def get_queries(self, page: int = 1, page_size: int = 20) -> list[AIQuery]:
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(AIQuery).order_by(AIQuery.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all())

    async def get_user_queries(
        self, user_id: int, *, limit: int = 50, offset: int = 0
    ) -> list[AIQuery]:
        result = await self.db.execute(
            select(AIQuery)
            .where(AIQuery.user_id == user_id, AIQuery.response_text.isnot(None))
            .order_by(AIQuery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_query(self, user_id: int, query_id: int) -> AIQuery | None:
        result = await self.db.execute(
            select(AIQuery).where(AIQuery.id == query_id, AIQuery.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_query_citations(self, query_id: int) -> list[dict]:
        result = await self.db.execute(
            select(AIQueryEvent)
            .where(
                AIQueryEvent.query_id == query_id,
                AIQueryEvent.event_type == "recommendation",
            )
            .order_by(AIQueryEvent.id.desc())
            .limit(1)
        )
        event = result.scalar_one_or_none()
        if event and event.payload_json:
            raw = event.payload_json.get("citations", [])
            return raw if isinstance(raw, list) else []
        return []

    async def delete_user_query(self, user_id: int, query_id: int) -> bool:
        query = await self.get_user_query(user_id, query_id)
        if not query:
            return False
        await self.db.delete(query)
        await self.db.flush()
        return True

    async def get_query_events(self, query_id: int) -> list[AIQueryEvent]:
        result = await self.db.execute(
            select(AIQueryEvent).where(AIQueryEvent.query_id == query_id)
        )
        return list(result.scalars().all())

    async def get_aggregate_stats(self) -> dict:
        result = await self.db.execute(
            select(
                func.count(AIQuery.id),
                func.avg(AIQueryEvent.latency_ms),
            )
            .select_from(AIQuery)
            .outerjoin(AIQueryEvent)
        )
        row = result.one()
        events_result = await self.db.execute(
            select(
                func.sum(AIQueryEvent.tokens_in),
                func.sum(AIQueryEvent.tokens_out),
            )
        )
        tokens = events_result.one()
        return {
            "total_queries": row[0] or 0,
            "avg_latency_ms": float(row[1] or 0),
            "total_tokens_in": tokens[0] or 0,
            "total_tokens_out": tokens[1] or 0,
        }
