"""add movie_embeddings foreign key

Revision ID: 002
Revises: 001
Create Date: 2026-06-06

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_movie_embeddings_movie_id_movies",
        "movie_embeddings",
        "movies",
        ["movie_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_movie_embeddings_movie_id_movies",
        "movie_embeddings",
        type_="foreignkey",
    )
