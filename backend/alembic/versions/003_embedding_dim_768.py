"""resize embedding vectors to 768 for Gemini

Revision ID: 003
Revises: 002
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_movie_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_user_content_embeddings_hnsw")
    op.execute("TRUNCATE movie_embeddings")
    op.execute("TRUNCATE user_content_embeddings")
    op.execute("ALTER TABLE movie_embeddings ALTER COLUMN embedding TYPE vector(768)")
    op.execute("ALTER TABLE user_content_embeddings ALTER COLUMN embedding TYPE vector(768)")
    op.execute(
        "CREATE INDEX ix_movie_embeddings_hnsw ON movie_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_user_content_embeddings_hnsw ON user_content_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_movie_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_user_content_embeddings_hnsw")
    op.execute("TRUNCATE movie_embeddings")
    op.execute("TRUNCATE user_content_embeddings")
    op.execute("ALTER TABLE movie_embeddings ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("ALTER TABLE user_content_embeddings ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        "CREATE INDEX ix_movie_embeddings_hnsw ON movie_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_user_content_embeddings_hnsw ON user_content_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )
