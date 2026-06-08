#!/usr/bin/env python3
"""CLI script to import a Letterboxd export ZIP."""

import argparse
import asyncio
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.import_service import ImportService


async def import_export(export_path: Path, user_uid: str | None = None):
    settings = get_settings()
    uid = user_uid or settings.dev_firebase_uid

    if export_path.is_dir():
        # Create temp zip from directory
        import tempfile
        import shutil
        zip_path = Path(tempfile.mktemp(suffix=".zip"))
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", export_path)
        content = zip_path.read_bytes()
        filename = zip_path.name
    else:
        content = export_path.read_bytes()
        filename = export_path.name

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.firebase_uid == uid))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                firebase_uid=uid,
                email="dev@cinegraph.local",
                display_name="Dev User",
                is_admin=settings.dev_admin,
            )
            db.add(user)
            await db.flush()

        svc = ImportService(db)
        print(f"Importing {export_path} for user {uid}...")
        job = await svc.create_job(user, content, filename)
        await db.flush()
        await svc.process_job(job.id, user.id, content, filename)
        await db.commit()
        await db.refresh(job)
        print(f"Import complete! Job ID: {job.id}, Status: {job.status}")
        if job.stats_json:
            print(f"Stats: {job.stats_json}")
        if job.error:
            print(f"Error: {job.error}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Import Letterboxd export")
    parser.add_argument(
        "path",
        nargs="?",
        default="letterboxd-rocktopus101-2026-06-07-04-56-utc",
        help="Path to ZIP file or export directory",
    )
    parser.add_argument("--user", help="Firebase UID (default: DEV_FIREBASE_UID)")
    args = parser.parse_args()

    export_path = Path(args.path)
    if not export_path.exists():
        # Try relative to project root
        export_path = Path(__file__).parent.parent / args.path
    if not export_path.exists():
        print(f"Export not found: {args.path}")
        sys.exit(1)

    asyncio.run(import_export(export_path, args.user))


if __name__ == "__main__":
    main()
