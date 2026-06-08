from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie, MovieEmbedding
from app.models.user_content import UserContentEmbedding
from app.models.user_data import UserMovie
from app.services.embedding_service import EmbeddingService


@dataclass
class RetrievedDoc:
    source_type: str
    movie_id: int | None
    score: float
    citation_text: str
    text_chunk: str


class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedder = EmbeddingService(db)

    def _rrf_merge(self, lists: list[list[RetrievedDoc]], k: int = 60) -> list[RetrievedDoc]:
        scores: dict[str, float] = {}
        docs: dict[str, RetrievedDoc] = {}
        for result_list in lists:
            for rank, doc in enumerate(result_list):
                key = f"{doc.source_type}:{doc.movie_id}:{doc.text_chunk[:50]}"
                scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
                docs[key] = doc
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        result = []
        for key in sorted_keys:
            doc = docs[key]
            doc.score = scores[key]
            result.append(doc)
        return result

    async def retrieve(
        self,
        query: str,
        user_id: int,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[RetrievedDoc]:
        filters = filters or {}
        query_embedding = await self.embedder.embed_query(query)
        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        user_docs = await self._search_user_content(user_id, emb_str, filters, limit)
        movie_docs = await self._search_movies(emb_str, filters, limit)
        merged = self._rrf_merge([user_docs, movie_docs])
        return merged[:limit]

    async def _search_user_content(
        self, user_id: int, emb_str: str, filters: dict, limit: int
    ) -> list[RetrievedDoc]:
        sql = f"""
            SELECT uce.id, uce.source_type, uce.source_id, uce.text_chunk,
                   um.movie_id, m.title,
                   1 - (uce.embedding <=> '{emb_str}'::vector) as score
            FROM user_content_embeddings uce
            LEFT JOIN user_movies um ON uce.source_id = um.id
            LEFT JOIN movies m ON um.movie_id = m.id
            WHERE uce.user_id = :user_id
        """
        params: dict = {"user_id": user_id}
        if filters.get("min_rating"):
            sql += " AND um.rating >= :min_rating"
            params["min_rating"] = filters["min_rating"]
        if filters.get("date_from"):
            sql += " AND um.watched_date >= :date_from"
            params["date_from"] = filters["date_from"]
        if filters.get("date_to"):
            sql += " AND um.watched_date <= :date_to"
            params["date_to"] = filters["date_to"]
        sql += f" ORDER BY uce.embedding <=> '{emb_str}'::vector LIMIT :limit"
        params["limit"] = limit

        result = await self.db.execute(text(sql), params)
        docs = []
        for row in result:
            docs.append(
                RetrievedDoc(
                    source_type=row.source_type,
                    movie_id=row.movie_id,
                    score=float(row.score or 0),
                    citation_text=row.text_chunk[:200],
                    text_chunk=row.text_chunk,
                )
            )
        return docs

    async def _search_movies(self, emb_str: str, filters: dict, limit: int) -> list[RetrievedDoc]:
        sql = f"""
            SELECT me.movie_id, m.title, m.overview,
                   1 - (me.embedding <=> '{emb_str}'::vector) as score
            FROM movie_embeddings me
            JOIN movies m ON me.movie_id = m.id
            WHERE 1=1
        """
        params: dict = {"limit": limit}
        if filters.get("genre"):
            sql += " AND m.metadata_json->'genres' ? :genre"
            params["genre"] = filters["genre"]
        sql += f" ORDER BY me.embedding <=> '{emb_str}'::vector LIMIT :limit"

        result = await self.db.execute(text(sql), params)
        docs = []
        for row in result:
            docs.append(
                RetrievedDoc(
                    source_type="movie",
                    movie_id=row.movie_id,
                    score=float(row.score or 0),
                    citation_text=f"{row.title}: {(row.overview or '')[:150]}",
                    text_chunk=row.overview or row.title,
                )
            )
        return docs

    async def find_similar_movies(self, movie_id: int, limit: int = 10) -> list[RetrievedDoc]:
        result = await self.db.execute(
            select(MovieEmbedding).where(MovieEmbedding.movie_id == movie_id)
        )
        emb_row = result.scalar_one_or_none()
        if not emb_row:
            return []

        emb = emb_row.embedding
        emb_str = "[" + ",".join(str(x) for x in emb) + "]"
        sql = f"""
            SELECT me.movie_id, m.title, m.year, m.poster_path,
                   1 - (me.embedding <=> '{emb_str}'::vector) as score
            FROM movie_embeddings me
            JOIN movies m ON me.movie_id = m.id
            WHERE me.movie_id != :movie_id
            ORDER BY me.embedding <=> '{emb_str}'::vector
            LIMIT :limit
        """
        result = await self.db.execute(text(sql), {"movie_id": movie_id, "limit": limit})
        return [
            RetrievedDoc(
                source_type="similar",
                movie_id=row.movie_id,
                score=float(row.score or 0),
                citation_text=row.title,
                text_chunk=row.title,
            )
            for row in result
        ]
