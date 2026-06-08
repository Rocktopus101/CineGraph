from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.base import Base

_EMBEDDING_DIM = get_settings().embedding_dim


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    original_title: Mapped[str | None] = mapped_column(String(512))
    year: Mapped[int | None] = mapped_column(Integer)
    runtime: Mapped[int | None] = mapped_column(Integer)
    overview: Mapped[str | None] = mapped_column(String)
    poster_path: Mapped[str | None] = mapped_column(String(512))
    backdrop_path: Mapped[str | None] = mapped_column(String(512))
    release_date: Mapped[str | None] = mapped_column(String(32))
    vote_average: Mapped[float | None] = mapped_column(Float)
    letterboxd_uri: Mapped[str | None] = mapped_column(String(256), index=True)
    letterboxd_slug: Mapped[str | None] = mapped_column(String(256))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    embeddings = relationship("MovieEmbedding", back_populates="movie")
    user_movies = relationship("UserMovie", back_populates="movie")


class TmdbCache(Base):
    __tablename__ = "tmdb_cache"

    cache_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    response_json: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MovieEmbedding(Base):
    __tablename__ = "movie_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    embedding = mapped_column(Vector(_EMBEDDING_DIM))
    content_type: Mapped[str] = mapped_column(String(32), default="combined")
    content_hash: Mapped[str | None] = mapped_column(String(64))

    movie = relationship("Movie", back_populates="embeddings")
