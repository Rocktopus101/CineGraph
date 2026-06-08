from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base

_EMBEDDING_DIM = get_settings().embedding_dim


class UserContentEmbedding(Base):
    __tablename__ = "user_content_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector(_EMBEDDING_DIM))
    text_chunk: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
