from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class UserMovie(Base):
    __tablename__ = "user_movies"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", "diary_uri", name="uq_user_movie_diary"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    watched_date: Mapped[date | None] = mapped_column(Date, index=True)
    rating: Mapped[float | None] = mapped_column(Float)
    rewatch: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[str | None] = mapped_column(String(512))
    review_text: Mapped[str | None] = mapped_column(Text)
    diary_uri: Mapped[str | None] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32), default="watched")
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_movies")
    movie = relationship("Movie", back_populates="user_movies")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserList(Base):
    __tablename__ = "user_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(256))
    list_type: Mapped[str] = mapped_column(String(32), default="taste_generated")
    description: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items = relationship("UserListItem", back_populates="list", cascade="all, delete-orphan")


class UserListItem(Base):
    __tablename__ = "user_list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("user_lists.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)

    list = relationship("UserList", back_populates="items")
