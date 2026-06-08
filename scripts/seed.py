#!/usr/bin/env python3
"""Seed dev data for CineGraph."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.ai import AIQuery, AIQueryEvent
from app.models.movie import Movie
from app.models.user import User
from app.models.user_data import UserMovie
from app.services.demo_data_service import DemoDataService
from app.services.embedding_service import EmbeddingService
from app.services.list_generator_service import ListGeneratorService
from app.services.taste_profile_service import TasteProfileService


async def seed():
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.firebase_uid == settings.dev_firebase_uid))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                firebase_uid=settings.dev_firebase_uid,
                email="dev@cinegraph.local",
                display_name="Dev User",
                letterboxd_username="devuser",
                is_admin=settings.dev_admin,
            )
            db.add(user)
            await db.flush()

        demo = DemoDataService(db)
        job = await demo.load_for_user(user)
        movies_result = await db.execute(
            select(Movie)
            .join(UserMovie, UserMovie.movie_id == Movie.id)
            .where(UserMovie.user_id == user.id)
        )
        movies = list(movies_result.scalars().all())

        embedder = EmbeddingService(db)
        await embedder.embed_all_movies([m.id for m in movies])
        await embedder.embed_user_history(user.id)

        taste = TasteProfileService(db)
        await taste.compute_profile(user.id)
        lists = ListGeneratorService(db)
        await lists.generate_lists(user.id)

        ai_q = AIQuery(
            user_id=user.id,
            query_text="What sci-fi films should I watch next?",
            response_text="Based on your love of Interstellar and Arrival, I'd recommend Blade Runner 2049.",
        )
        db.add(ai_q)
        await db.flush()
        db.add(AIQueryEvent(
            query_id=ai_q.id,
            event_type="retrieval",
            payload_json={"docs": [{"movie_id": movies[0].id, "score": 0.89}]},
            latency_ms=120,
        ))
        db.add(AIQueryEvent(
            query_id=ai_q.id,
            event_type="llm_call",
            payload_json={"model": settings.chat_model},
            latency_ms=450,
            tokens_in=500,
            tokens_out=150,
        ))

        await db.commit()
        print(f"Seeded {len(movies)} movies for user {user.id} ({user.firebase_uid})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(seed())
