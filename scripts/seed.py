#!/usr/bin/env python3
"""Seed dev data for CineGraph."""

import asyncio
import logging
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.ai import AIQuery, AIQueryEvent
from app.models.import_job import ImportJob
from app.models.movie import Movie
from app.models.taste import TasteProfile
from app.models.user import User
from app.models.user_data import UserMovie
from app.services.embedding_service import EmbeddingService
from app.services.list_generator_service import ListGeneratorService
from app.services.taste_profile_service import TasteProfileService

SEED_MOVIES = [
    {"tmdb_id": 157336, "title": "Interstellar", "year": 2014, "genres": ["Adventure", "Drama", "Sci-Fi"],
     "overview": "A team of explorers travel through a wormhole in space.", "poster_path": "/gEU2QziWnFjIEieqNC9r9xCp0WL.jpg"},
    {"tmdb_id": 329865, "title": "Arrival", "year": 2016, "genres": ["Drama", "Sci-Fi", "Mystery"],
     "overview": "A linguist works with the military to communicate with aliens.", "poster_path": "/x2FJ2tDRlD18x5iZpWkM7q25vjs.jpg"},
    {"tmdb_id": 335984, "title": "Blade Runner 2049", "year": 2017, "genres": ["Sci-Fi", "Thriller"],
     "overview": "Young Blade Runner K discovers a secret that could plunge society into chaos.", "poster_path": "/gajva2L0rPYkEWjzgFl3X0bLm1e.jpg"},
    {"tmdb_id": 603, "title": "The Matrix", "year": 1999, "genres": ["Action", "Sci-Fi"],
     "overview": "A computer hacker learns about the true nature of reality.", "poster_path": "/f89U3ADr1oiB1sbeGbd5ig5s8je.jpg"},
    {"tmdb_id": 78, "title": "Blade Runner", "year": 1982, "genres": ["Sci-Fi", "Thriller"],
     "overview": "A blade runner must pursue and terminate replicants.", "poster_path": "/63N9uy8nd9D7o1IeBk2iVgL/l.jpg"},
    {"tmdb_id": 27205, "title": "Inception", "year": 2010, "genres": ["Action", "Sci-Fi", "Thriller"],
     "overview": "A thief who steals corporate secrets through dream-sharing technology.", "poster_path": "/9oGK7exLM8Mlohow1aFOTfp74K.jpg"},
    {"tmdb_id": 693134, "title": "Dune: Part Two", "year": 2024, "genres": ["Sci-Fi", "Adventure"],
     "overview": "Paul Atreides unites with Chani and the Fremen.", "poster_path": "/1pdf1fbYNW503VPsrK2vEJiWk24.jpg"},
    {"tmdb_id": 438631, "title": "Dune", "year": 2021, "genres": ["Sci-Fi", "Adventure"],
     "overview": "Paul Atreides leads nomadic tribes in a war for Arrakis.", "poster_path": "/d5NXSklXo0bdINEVxBR6p7j1Q3p.jpg"},
    {"tmdb_id": 872585, "title": "Oppenheimer", "year": 2023, "genres": ["Drama", "History"],
     "overview": "The story of American scientist J. Robert Oppenheimer.", "poster_path": "/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg"},
    {"tmdb_id": 346698, "title": "Barbie", "year": 2023, "genres": ["Comedy", "Adventure"],
     "overview": "Barbie suffers a crisis that leads her to question her world.", "poster_path": "/iuFNMS7U3cb2HziBSsdGha4t0c5.jpg"},
    {"tmdb_id": 496243, "title": "Parasite", "year": 2019, "genres": ["Comedy", "Drama", "Thriller"],
     "overview": "Greed and class discrimination threaten a newly formed symbiotic relationship.", "poster_path": "/7IiTTgloJzvGI1EAYfywP7M4ENM.jpg"},
    {"tmdb_id": 475557, "title": "Joker", "year": 2019, "genres": ["Crime", "Drama", "Thriller"],
     "overview": "During the 1980s, a failed comedian is driven insane.", "poster_path": "/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg"},
    {"tmdb_id": 399566, "title": "Godzilla vs. Kong", "year": 2021, "genres": ["Action", "Sci-Fi"],
     "overview": "Godzilla and Kong clash in a battle for the ages.", "poster_path": "/pgq8z5Yp3maEwqVzsdxidht9v37.jpg"},
    {"tmdb_id": 361743, "title": "Top Gun: Maverick", "year": 2022, "genres": ["Action", "Drama"],
     "overview": "After thirty years, Maverick is still pushing the envelope.", "poster_path": "/62HCnUTziyWcpDaBO2i1DX17ljH.jpg"},
    {"tmdb_id": 414906, "title": "The Batman", "year": 2022, "genres": ["Crime", "Drama", "Action"],
     "overview": "Batman ventures into Gotham's underworld.", "poster_path": "/b0PlSFxDwVz4cVFEARJa2lO1bTb.jpg"},
    {"tmdb_id": 680, "title": "Pulp Fiction", "year": 1994, "genres": ["Crime", "Drama"],
     "overview": "The lives of two mob hitmen, a boxer, and more intertwine.", "poster_path": "/d5iIlFn5s0ImszYzBPb8JzfbjAJ.jpg"},
    {"tmdb_id": 155, "title": "The Dark Knight", "year": 2008, "genres": ["Action", "Crime", "Drama"],
     "overview": "Batman raises the stakes in his war on crime.", "poster_path": "/qJ2tW6WMUDux911r6m7dRef8WHk.jpg"},
    {"tmdb_id": 238, "title": "The Godfather", "year": 1972, "genres": ["Crime", "Drama"],
     "overview": "The aging patriarch of an organized crime dynasty transfers control.", "poster_path": "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg"},
    {"tmdb_id": 13, "title": "Forrest Gump", "year": 1994, "genres": ["Drama", "Romance"],
     "overview": "The presidencies of Kennedy and Johnson unfold through the perspective of an Alabama man.", "poster_path": "/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg"},
    {"tmdb_id": 550, "title": "Fight Club", "year": 1999, "genres": ["Drama"],
     "overview": "An insomniac office worker forms an underground fight club.", "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3mJKl.jpg"},
]

REVIEWS = [
    "A masterpiece of science fiction that left me thinking for days.",
    "Visually stunning but the pacing dragged in the middle.",
    "One of the best films I've seen this year. Absolutely loved it.",
    "Great performances all around. The score was incredible.",
    "Didn't quite live up to the hype for me, but still solid.",
]


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

        movies: list[Movie] = []
        for m in SEED_MOVIES:
            result = await db.execute(select(Movie).where(Movie.tmdb_id == m["tmdb_id"]))
            movie = result.scalar_one_or_none()
            if not movie:
                movie = Movie(
                    tmdb_id=m["tmdb_id"],
                    title=m["title"],
                    year=m["year"],
                    overview=m["overview"],
                    poster_path=m["poster_path"],
                    metadata_json={"genres": m["genres"], "cast": [], "directors": []},
                )
                db.add(movie)
            movies.append(movie)
        await db.flush()

        base_date = date.today() - timedelta(days=365)
        for i, movie in enumerate(movies):
            watched = base_date + timedelta(days=random.randint(0, 350))
            rating = round(random.uniform(2.5, 5.0) * 2) / 2
            review = random.choice(REVIEWS) if random.random() > 0.6 else None
            result = await db.execute(
                select(UserMovie).where(UserMovie.user_id == user.id, UserMovie.movie_id == movie.id)
            )
            if not result.scalar_one_or_none():
                db.add(UserMovie(
                    user_id=user.id,
                    movie_id=movie.id,
                    watched_date=watched,
                    rating=rating,
                    review_text=review,
                    source="seed",
                ))

        job = ImportJob(
            user_id=user.id,
            status="complete",
            file_hash="seed",
            completed_at=datetime.now(timezone.utc),
            stats_json={"stage": "complete", "progress": 100, "source": "seed.py"},
        )
        db.add(job)

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
