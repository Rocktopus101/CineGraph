from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.movie import MovieSearchResult


class HistoryItem(BaseModel):
    id: int
    movie: MovieSearchResult
    watched_date: date | None
    rating: float | None
    review_text: str | None
    source: str

    model_config = {"from_attributes": True}


class ReviewItem(BaseModel):
    id: int
    movie: MovieSearchResult
    review_text: str | None
    rating: float | None
    watched_date: date | None

    model_config = {"from_attributes": True}


class WatchlistItemResponse(BaseModel):
    id: int
    movie: MovieSearchResult
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistCreateRequest(BaseModel):
    movie_id: int


class ListSummary(BaseModel):
    id: int
    name: str
    list_type: str
    description: str | None
    item_count: int = 0

    model_config = {"from_attributes": True}


class ListDetail(BaseModel):
    id: int
    name: str
    list_type: str
    description: str | None
    items: list[MovieSearchResult]

    model_config = {"from_attributes": True}
