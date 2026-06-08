from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    summary_text: Mapped[str | None] = mapped_column(Text)
    insights_json: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TasteStat(Base):
    __tablename__ = "taste_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stat_type: Mapped[str] = mapped_column(String(64))
    stat_key: Mapped[str] = mapped_column(String(256))
    stat_value: Mapped[float] = mapped_column(default=0.0)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
