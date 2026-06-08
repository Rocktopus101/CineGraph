"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("display_name", sa.String(255)),
        sa.Column("letterboxd_username", sa.String(128)),
        sa.Column("is_admin", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"])

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("original_title", sa.String(512)),
        sa.Column("year", sa.Integer()),
        sa.Column("runtime", sa.Integer()),
        sa.Column("overview", sa.Text()),
        sa.Column("poster_path", sa.String(512)),
        sa.Column("backdrop_path", sa.String(512)),
        sa.Column("release_date", sa.String(32)),
        sa.Column("vote_average", sa.Float()),
        sa.Column("letterboxd_uri", sa.String(256)),
        sa.Column("letterboxd_slug", sa.String(256)),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB()),
    )
    op.create_index("ix_movies_tmdb_id", "movies", ["tmdb_id"])
    op.create_index("ix_movies_title", "movies", ["title"])
    op.create_index("ix_movies_letterboxd_uri", "movies", ["letterboxd_uri"])

    op.create_table(
        "tmdb_cache",
        sa.Column("cache_key", sa.String(512), primary_key=True),
        sa.Column("response_json", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("file_hash", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("stats_json", sa.dialects.postgresql.JSONB()),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"])

    op.create_table(
        "import_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("import_jobs.id"), nullable=False),
        sa.Column("source_file", sa.String(128), nullable=False),
        sa.Column("last_row_hash", sa.String(64)),
        sa.Column("rows_processed", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "user_movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("watched_date", sa.Date()),
        sa.Column("rating", sa.Float()),
        sa.Column("rewatch", sa.Boolean(), server_default="false"),
        sa.Column("tags", sa.String(512)),
        sa.Column("review_text", sa.Text()),
        sa.Column("diary_uri", sa.String(256)),
        sa.Column("source", sa.String(32), server_default="watched"),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "movie_id", "diary_uri", name="uq_user_movie_diary"),
    )
    op.create_index("ix_user_movies_user_id", "user_movies", ["user_id"])
    op.create_index("ix_user_movies_movie_id", "user_movies", ["movie_id"])
    op.create_index("ix_user_movies_watched_date", "user_movies", ["watched_date"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),
    )

    op.create_table(
        "user_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("list_type", sa.String(32), server_default="taste_generated"),
        sa.Column("description", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("user_lists.id"), nullable=False),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("rank", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "movie_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536)),
        sa.Column("content_type", sa.String(32), server_default="combined"),
        sa.Column("content_hash", sa.String(64)),
    )
    op.create_index("ix_movie_embeddings_movie_id", "movie_embeddings", ["movie_id"])
    op.execute(
        "CREATE INDEX ix_movie_embeddings_hnsw ON movie_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "user_content_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Integer()),
        sa.Column("embedding", Vector(1536)),
        sa.Column("text_chunk", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64)),
    )
    op.create_index("ix_user_content_embeddings_user_id", "user_content_embeddings", ["user_id"])
    op.execute(
        "CREATE INDEX ix_user_content_embeddings_hnsw ON user_content_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "taste_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("summary_text", sa.Text()),
        sa.Column("insights_json", sa.dialects.postgresql.JSONB()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "taste_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("stat_type", sa.String(64), nullable=False),
        sa.Column("stat_key", sa.String(256), nullable=False),
        sa.Column("stat_value", sa.Float(), server_default="0"),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB()),
    )

    op.create_table(
        "ai_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ai_query_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_id", sa.Integer(), sa.ForeignKey("ai_queries.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.dialects.postgresql.JSONB()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("tokens_in", sa.Integer()),
        sa.Column("tokens_out", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("ai_query_events")
    op.drop_table("ai_queries")
    op.drop_table("taste_stats")
    op.drop_table("taste_profiles")
    op.drop_table("user_content_embeddings")
    op.drop_table("movie_embeddings")
    op.drop_table("user_list_items")
    op.drop_table("user_lists")
    op.drop_table("watchlist_items")
    op.drop_table("user_movies")
    op.drop_table("import_checkpoints")
    op.drop_table("import_jobs")
    op.drop_table("tmdb_cache")
    op.drop_table("movies")
    op.drop_table("users")
