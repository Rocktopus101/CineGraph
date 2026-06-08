import hashlib
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_llm_provider
from app.ai.rate_limiter import is_rate_limit_error
from app.core.config import get_settings
from app.models.movie import Movie, MovieEmbedding
from app.models.user_content import UserContentEmbedding
from app.models.user_data import UserMovie

logger = logging.getLogger(__name__)


def _zero_embedding(dim: int) -> list[float]:
    return [0.0] * dim


class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_llm_provider()
        self.settings = get_settings()

    @property
    def embedding_dim(self) -> int:
        return self.provider.embedding_dim

    def _content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _truncate(self, text: str) -> str:
        limit = self.settings.embedding_max_chunk_chars
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def embed_text(self, text: str) -> list[float]:
        if not self.provider.is_available or self.provider.name == "local":
            return _zero_embedding(self.embedding_dim)
        try:
            return await self.provider.embed_text(self._truncate(text))
        except Exception as exc:
            if is_rate_limit_error(exc):
                raise
            logger.warning(
                "%s embedding failed (%s); using zero-vector fallback",
                self.provider.name,
                exc,
            )
            return _zero_embedding(self.embedding_dim)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.provider.is_available or self.provider.name == "local":
            return [_zero_embedding(self.embedding_dim) for _ in texts]
        try:
            truncated = [self._truncate(t) for t in texts]
            return await self.provider.embed_batch(truncated)
        except Exception as exc:
            if is_rate_limit_error(exc):
                raise
            logger.warning(
                "%s batch embedding failed (%s); using zero-vector fallback",
                self.provider.name,
                exc,
            )
            return [_zero_embedding(self.embedding_dim) for _ in texts]

    def _movie_chunk(self, movie: Movie) -> str:
        genres = (movie.metadata_json or {}).get("genres", [])
        cast = (movie.metadata_json or {}).get("cast", [])
        return self._truncate(
            f"{movie.title} ({movie.year or 'unknown'}). "
            f"Genres: {', '.join(genres)}. Cast: {', '.join(cast[:5])}. "
            f"{movie.overview or ''}"
        )

    def _user_chunk(self, um: UserMovie, movie: Movie) -> tuple[str, str]:
        if um.review_text:
            return (
                "review",
                self._truncate(f"Review of {movie.title}: {um.review_text}"),
            )
        return (
            "history",
            self._truncate(
                f"Watched {movie.title} ({movie.year}) — "
                f"rated {um.rating} on {um.watched_date}"
            ),
        )

    async def _embed_in_batches(
        self,
        items: list[tuple[str, Callable[[list[float]], Awaitable[None]]]],
        on_batch: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> int:
        """Embed many items using batched API calls to conserve free-tier RPM."""
        if not items:
            return 0

        batch_size = self.settings.embedding_batch_size
        embedded = 0

        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            texts = [text for text, _ in batch]
            vectors = await self.embed_batch(texts)

            for (_, saver), vector in zip(batch, vectors):
                await saver(vector)
                embedded += 1

            if on_batch:
                await on_batch(embedded, len(items))

        return embedded

    async def embed_movies_for_import(
        self,
        movie_ids: list[int],
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> int:
        if not movie_ids:
            return 0

        result = await self.db.execute(select(Movie).where(Movie.id.in_(movie_ids)))
        movies = {m.id: m for m in result.scalars().all()}

        pending: list[tuple[str, Callable[[list[float]], Awaitable[None]]]] = []

        for movie_id in movie_ids:
            movie = movies.get(movie_id)
            if not movie:
                continue
            chunk = self._movie_chunk(movie)
            content_hash = self._content_hash(chunk)
            existing = await self.db.execute(
                select(MovieEmbedding).where(
                    MovieEmbedding.movie_id == movie.id,
                    MovieEmbedding.content_hash == content_hash,
                )
            )
            if existing.scalar_one_or_none():
                continue

            async def save_movie(
                vector: list[float],
                *,
                m: Movie = movie,
                h: str = content_hash,
                c: str = chunk,
            ) -> None:
                await self.db.execute(delete(MovieEmbedding).where(MovieEmbedding.movie_id == m.id))
                self.db.add(
                    MovieEmbedding(
                        movie_id=m.id,
                        embedding=vector,
                        content_type="combined",
                        content_hash=h,
                    )
                )

            pending.append((chunk, save_movie))

        return await self._embed_in_batches(pending, on_batch=on_progress)

    async def embed_user_history_for_import(
        self,
        user_id: int,
        on_progress: Callable[[int, int], Awaitable[None]] | None = None,
    ) -> int:
        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id)
        )
        rows = result.all()
        pending: list[tuple[str, Callable[[list[float]], Awaitable[None]]]] = []

        for um, movie in rows:
            source_type, chunk = self._user_chunk(um, movie)
            content_hash = self._content_hash(chunk)
            existing = await self.db.execute(
                select(UserContentEmbedding).where(
                    UserContentEmbedding.user_id == user_id,
                    UserContentEmbedding.source_id == um.id,
                    UserContentEmbedding.content_hash == content_hash,
                )
            )
            if existing.scalar_one_or_none():
                continue

            async def save_user(
                vector: list[float],
                *,
                u_id: int = user_id,
                s_type: str = source_type,
                s_id: int = um.id,
                h: str = content_hash,
                c: str = chunk,
            ) -> None:
                self.db.add(
                    UserContentEmbedding(
                        user_id=u_id,
                        source_type=s_type,
                        source_id=s_id,
                        embedding=vector,
                        text_chunk=c,
                        content_hash=h,
                    )
                )

            pending.append((chunk, save_user))

        return await self._embed_in_batches(pending, on_batch=on_progress)

    async def embed_movie(self, movie: Movie) -> None:
        chunk = self._movie_chunk(movie)
        content_hash = self._content_hash(chunk)
        result = await self.db.execute(
            select(MovieEmbedding).where(
                MovieEmbedding.movie_id == movie.id,
                MovieEmbedding.content_hash == content_hash,
            )
        )
        if result.scalar_one_or_none():
            return
        embedding = await self.embed_text(chunk)
        await self.db.execute(delete(MovieEmbedding).where(MovieEmbedding.movie_id == movie.id))
        self.db.add(
            MovieEmbedding(
                movie_id=movie.id,
                embedding=embedding,
                content_type="combined",
                content_hash=content_hash,
            )
        )

    async def embed_user_content(self, user_id: int, um: UserMovie, movie: Movie) -> None:
        source_type, chunk = self._user_chunk(um, movie)
        content_hash = self._content_hash(chunk)
        result = await self.db.execute(
            select(UserContentEmbedding).where(
                UserContentEmbedding.user_id == user_id,
                UserContentEmbedding.source_id == um.id,
                UserContentEmbedding.content_hash == content_hash,
            )
        )
        if result.scalar_one_or_none():
            return
        embedding = await self.embed_text(chunk)
        self.db.add(
            UserContentEmbedding(
                user_id=user_id,
                source_type=source_type,
                source_id=um.id,
                embedding=embedding,
                text_chunk=chunk,
                content_hash=content_hash,
            )
        )

    async def embed_all_movies(self, movie_ids: list[int] | None = None) -> int:
        if movie_ids:
            return await self.embed_movies_for_import(movie_ids)
        result = await self.db.execute(select(Movie.id))
        ids = [row[0] for row in result.all()]
        return await self.embed_movies_for_import(ids)

    async def embed_user_history(self, user_id: int) -> int:
        return await self.embed_user_history_for_import(user_id)
