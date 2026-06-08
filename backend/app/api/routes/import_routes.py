import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.models.import_job import ImportJob
from app.models.user import User
from app.schemas.import_job import ImportJobResponse
from app.services.demo_data_service import DemoDataService
from app.services.import_service import ImportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/import", tags=["import"])


async def _run_import_in_background(
    job_id: int, user_id: int, content: bytes, filename: str
) -> None:
    # Brief retry — background task can start before the request transaction commits.
    for attempt in range(10):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
            if result.scalar_one_or_none():
                try:
                    svc = ImportService(db)
                    await svc.process_job(job_id, user_id, content, filename)
                    await db.commit()
                    return
                except Exception:
                    await db.rollback()
                    logger.exception("Background import job %s failed", job_id)
                    return
        await asyncio.sleep(0.3 * (attempt + 1))

    logger.error("Import job %s not found after retries — marking failed", job_id)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error = "Import worker could not start. Please try uploading again."
            await db.commit()


@router.post("/letterboxd", response_model=ImportJobResponse)
async def import_letterboxd(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    settings = get_settings()
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, "File must be a .zip archive")

    content = await file.read()
    max_bytes = settings.import_max_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.import_max_file_mb}MB limit")

    svc = ImportService(db)
    job = await svc.create_job(user, content, file.filename)
    # Commit before scheduling so the background worker can see the job row.
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(_run_import_in_background(job.id, user.id, content, file.filename))

    return ImportJobResponse.model_validate(job)


@router.post("/demo", response_model=ImportJobResponse)
async def load_demo_data(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Load sample watch history without embedding API calls."""
    try:
        import_svc = ImportService(db)
        await import_svc.cancel_active_jobs(user.id)

        svc = DemoDataService(db)
        job = await svc.load_for_user(user)
        await db.commit()
        await db.refresh(job)
        return ImportJobResponse.model_validate(job)
    except Exception as exc:
        await db.rollback()
        logger.exception("Demo data load failed for user %s", user.id)
        raise HTTPException(500, f"Failed to load sample data: {exc}") from exc


@router.post("/jobs/{job_id}/cancel", response_model=ImportJobResponse)
async def cancel_import_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ImportService(db)
    job = await svc.cancel_job(user.id, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    await db.commit()
    await db.refresh(job)
    return ImportJobResponse.model_validate(job)


@router.get("/jobs", response_model=list[ImportJobResponse])
async def list_jobs(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ImportService(db)
    jobs = await svc.get_jobs(user.id)
    return [ImportJobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_job(
    job_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ImportService(db)
    job = await svc.get_job(user.id, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return ImportJobResponse.model_validate(job)
