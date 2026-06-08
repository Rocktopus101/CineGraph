import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.demo_movies import DEMO_MOVIES, DEMO_REVIEWS
from app.models.import_job import ImportJob
from app.models.movie import Movie, MovieEmbedding
from app.models.user import User
from app.models.user_content import UserContentEmbedding
from app.models.user_data import UserMovie
from app.services.embedding_service import EmbeddingService, _zero_embedding
from app.services.list_generator_service import ListGeneratorService
from app.services.taste_profile_service import TasteProfileService


class DemoDataService:
    """Load prebaked watch history without calling embedding APIs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_for_user(self, user: User) -> ImportJob:
        movies = await self._ensure_movies()
        await self._seed_user_movies(user.id, movies)

        embedder = EmbeddingService(self.db)
        await self._apply_zero_embeddings(embedder, user.id, [m.id for m in movies])

        taste = TasteProfileService(self.db)
        await taste.compute_profile(user.id, use_llm=False)

        lists = ListGeneratorService(self.db)
        await lists.generate_lists(user.id)

        if not user.letterboxd_username:
            user.letterboxd_username = "demo"

        job = ImportJob(
            user_id=user.id,
            status="complete",
            file_hash="demo",
            completed_at=datetime.now(timezone.utc),
            stats_json={
                "stage": "complete",
                "progress": 100,
                "source": "demo",
                "movies": len(movies),
                "note": "Sample data — no embedding API calls",
            },
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def _ensure_movies(self) -> list[Movie]:
        movies: list[Movie] = []
        for spec in DEMO_MOVIES:
            result = await self.db.execute(select(Movie).where(Movie.tmdb_id == spec["tmdb_id"]))
            movie = result.scalar_one_or_none()
            if not movie:
                movie = Movie(
                    tmdb_id=spec["tmdb_id"],
                    title=spec["title"],
                    year=spec["year"],
                    overview=spec["overview"],
                    poster_path=spec["poster_path"],
                    metadata_json={"genres": spec["genres"], "cast": [], "directors": []},
                )
                self.db.add(movie)
            movies.append(movie)
        await self.db.flush()
        return movies

    async def _seed_user_movies(self, user_id: int, movies: list[Movie]) -> None:
        base_date = date.today() - timedelta(days=365)
        for i, movie in enumerate(movies):
            result = await self.db.execute(
                select(UserMovie.id).where(
                    UserMovie.user_id == user_id,
                    UserMovie.movie_id == movie.id,
                ).limit(1)
            )
            if result.scalar_one_or_none():
                continue

            watched = base_date + timedelta(days=random.randint(0, 350))
            rating = round(random.uniform(2.5, 5.0) * 2) / 2
            review = random.choice(DEMO_REVIEWS) if random.random() > 0.6 else None
            self.db.add(
                UserMovie(
                    user_id=user_id,
                    movie_id=movie.id,
                    watched_date=watched,
                    rating=rating,
                    review_text=review,
                    source="demo",
                )
            )
        await self.db.flush()

    async def _apply_zero_embeddings(
        self,
        embedder: EmbeddingService,
        user_id: int,
        movie_ids: list[int],
    ) -> None:
        zero = _zero_embedding(embedder.embedding_dim)

        result = await self.db.execute(select(Movie).where(Movie.id.in_(movie_ids)))
        for movie in result.scalars():
            chunk = embedder._movie_chunk(movie)
            content_hash = embedder._content_hash(chunk)
            await self.db.execute(delete(MovieEmbedding).where(MovieEmbedding.movie_id == movie.id))
            self.db.add(
                MovieEmbedding(
                    movie_id=movie.id,
                    embedding=zero,
                    content_type="combined",
                    content_hash=content_hash,
                )
            )

        result = await self.db.execute(
            select(UserMovie, Movie)
            .join(Movie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user_id)
        )
        for um, movie in result.all():
            source_type, chunk = embedder._user_chunk(um, movie)
            content_hash = embedder._content_hash(chunk)
            await self.db.execute(
                delete(UserContentEmbedding).where(
                    UserContentEmbedding.user_id == user_id,
                    UserContentEmbedding.source_id == um.id,
                )
            )
            self.db.add(
                UserContentEmbedding(
                    user_id=user_id,
                    source_type=source_type,
                    source_id=um.id,
                    embedding=zero,
                    text_chunk=chunk,
                    content_hash=content_hash,
                )
            )
