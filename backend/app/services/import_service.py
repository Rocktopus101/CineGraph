import hashlib
import logging
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.letterboxd_parser import LetterboxdParser
from app.ingestion.tmdb_matcher import TmdbMatcher
from app.models.import_job import ImportJob
from app.models.movie import Movie
from app.models.user import User
from app.models.user_data import UserMovie, WatchlistItem
from app.services.embedding_service import EmbeddingService
from app.services.list_generator_service import ListGeneratorService
from app.services.taste_profile_service import TasteProfileService
from app.services.tmdb_service import TmdbService

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = LetterboxdParser()

    async def _save_progress(
        self,
        job: ImportJob,
        *,
        status: str | None = None,
        stage: str,
        progress: int,
        **extra: object,
    ) -> None:
        if status:
            job.status = status
        job.stats_json = {"stage": stage, "progress": progress, **extra}
        await self.db.commit()

    async def create_job(self, user: User, file_content: bytes, filename: str) -> ImportJob:
        """Create a pending import job and return immediately (processing runs in background)."""
        file_hash = hashlib.sha256(file_content).hexdigest()
        job = ImportJob(
            user_id=user.id,
            status="pending",
            file_hash=file_hash,
            stats_json={"stage": "pending", "progress": 0},
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def process_job(
        self, job_id: int, user_id: int, file_content: bytes, filename: str
    ) -> None:
        result = await self.db.execute(select(ImportJob).where(ImportJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("Import job %s not found", job_id)
            return

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            job.status = "failed"
            job.error = "User not found"
            await self.db.commit()
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / filename
            zip_path.write_bytes(file_content)
            export_dir = Path(tmpdir) / "export"
            export_dir.mkdir()
            self.parser.extract_zip(zip_path, export_dir)
            await self._process_export(user, job, export_dir)

    async def _process_export(self, user: User, job: ImportJob, export_dir: Path) -> None:
        try:
            await self._save_progress(job, status="parsing", stage="parsing", progress=10)

            parsed = self.parser.parse(export_dir)
            if parsed.username:
                user.letterboxd_username = parsed.username

            tmdb = TmdbService(self.db)
            matcher = TmdbMatcher(self.db, tmdb)
            films_parsed = 0
            imported_movie_ids: set[int] = set()
            total_films = max(len(parsed.films), 1)

            for film in parsed.films.values():
                movie = await matcher.find_or_create_movie(
                    film.name, film.year, film.letterboxd_uri
                )
                imported_movie_ids.add(movie.id)
                watched = None
                if film.watched_date:
                    try:
                        watched = date.fromisoformat(film.watched_date)
                    except ValueError:
                        pass

                result = await self.db.execute(
                    select(UserMovie).where(
                        UserMovie.user_id == user.id,
                        UserMovie.movie_id == movie.id,
                        UserMovie.diary_uri == film.diary_uri,
                    )
                )
                um = result.scalar_one_or_none()
                if um:
                    um.rating = film.rating if film.rating is not None else um.rating
                    um.review_text = film.review_text or um.review_text
                    um.watched_date = watched or um.watched_date
                    um.rewatch = film.rewatch
                    um.tags = film.tags
                    um.source = film.source
                else:
                    um = UserMovie(
                        user_id=user.id,
                        movie_id=movie.id,
                        watched_date=watched,
                        rating=film.rating,
                        rewatch=film.rewatch,
                        tags=film.tags,
                        review_text=film.review_text,
                        diary_uri=film.diary_uri,
                        source=film.source,
                    )
                    self.db.add(um)
                films_parsed += 1

                if films_parsed % 15 == 0 or films_parsed == total_films:
                    progress = 10 + int(40 * films_parsed / total_films)
                    await self._save_progress(
                        job,
                        status="enriching",
                        stage="enriching",
                        progress=progress,
                        films_parsed=films_parsed,
                        films_total=total_films,
                    )

            await self._save_progress(
                job,
                status="enriching",
                stage="enriching",
                progress=55,
                films_parsed=films_parsed,
            )

            for wl in parsed.watchlist:
                movie = await matcher.find_or_create_movie(
                    wl.name, wl.year, wl.letterboxd_uri
                )
                imported_movie_ids.add(movie.id)
                result = await self.db.execute(
                    select(WatchlistItem).where(
                        WatchlistItem.user_id == user.id,
                        WatchlistItem.movie_id == movie.id,
                    )
                )
                if not result.scalar_one_or_none():
                    self.db.add(WatchlistItem(user_id=user.id, movie_id=movie.id))

            await self._save_progress(job, status="embedding", stage="embedding", progress=70)

            embedder = EmbeddingService(self.db)
            movie_id_list = list(imported_movie_ids)

            async def on_movie_embed(done: int, total: int) -> None:
                await self.db.commit()
                progress = 70 + int(12 * done / max(total, 1))
                await self._save_progress(
                    job,
                    status="embedding",
                    stage="embedding",
                    progress=progress,
                    movies_embedded=done,
                    movies_total=total,
                )

            movies_embedded = await embedder.embed_movies_for_import(
                movie_id_list,
                on_progress=on_movie_embed,
            )
            await self.db.commit()

            async def on_user_embed(done: int, total: int) -> None:
                await self.db.commit()
                progress = 82 + int(8 * done / max(total, 1))
                await self._save_progress(
                    job,
                    status="embedding",
                    stage="embedding",
                    progress=progress,
                    user_embedded=done,
                    user_total=total,
                )

            user_embedded = await embedder.embed_user_history_for_import(
                user.id,
                on_progress=on_user_embed,
            )
            await self.db.commit()

            await self._save_progress(
                job,
                status="profiling",
                stage="profiling",
                progress=90,
                profiling_step="taste_stats",
                movies_embedded=movies_embedded,
                user_embedded=user_embedded,
            )

            taste = TasteProfileService(self.db)
            # Skip LLM during import — avoids free-tier chat rate limits / hangs.
            # Users can refresh the narrative summary from Profile later.
            await taste.compute_profile(user.id, use_llm=False)
            await self.db.commit()
            await self._save_progress(
                job,
                status="profiling",
                stage="profiling",
                progress=95,
                profiling_step="lists",
            )

            lists = ListGeneratorService(self.db)
            await lists.generate_lists(user.id)
            await self.db.commit()

            job.completed_at = datetime.now(timezone.utc)
            await self._save_progress(
                job,
                status="complete",
                stage="complete",
                progress=100,
                films_parsed=films_parsed,
                movies_embedded=movies_embedded,
                user_embedded=user_embedded,
            )
            logger.info("Import job %s complete for user %s", job.id, user.id)
        except Exception as exc:
            logger.exception("Import job %s failed", job.id)
            job.status = "failed"
            job.error = str(exc)
            await self.db.commit()
            raise

    async def get_jobs(self, user_id: int) -> list[ImportJob]:
        result = await self.db.execute(
            select(ImportJob).where(ImportJob.user_id == user_id).order_by(ImportJob.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_job(self, user_id: int, job_id: int) -> ImportJob | None:
        result = await self.db.execute(
            select(ImportJob).where(ImportJob.id == job_id, ImportJob.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def has_completed_import(self, user_id: int) -> bool:
        result = await self.db.execute(
            select(ImportJob).where(
                ImportJob.user_id == user_id,
                ImportJob.status == "complete",
            )
        )
        return result.scalar_one_or_none() is not None
