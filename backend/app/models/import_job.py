from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    file_hash: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats_json: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="import_jobs")
    checkpoints = relationship("ImportCheckpoint", back_populates="job")


class ImportCheckpoint(Base):
    __tablename__ = "import_checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id"), index=True)
    source_file: Mapped[str] = mapped_column(String(128))
    last_row_hash: Mapped[str | None] = mapped_column(String(64))
    rows_processed: Mapped[int] = mapped_column(default=0)

    job = relationship("ImportJob", back_populates="checkpoints")
