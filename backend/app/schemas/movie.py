from pydantic import BaseModel


class MovieSearchResult(BaseModel):
    id: int
    tmdb_id: int | None
    title: str
    year: int | None
    poster_path: str | None
    vote_average: float | None
    overview: str | None = None

    model_config = {"from_attributes": True}


class MovieDetail(BaseModel):
    id: int
    tmdb_id: int | None
    title: str
    original_title: str | None
    year: int | None
    runtime: int | None
    overview: str | None
    poster_path: str | None
    backdrop_path: str | None
    release_date: str | None
    vote_average: float | None
    letterboxd_uri: str | None
    metadata_json: dict | None
    user_rating: float | None = None
    user_review: str | None = None
    watched_date: str | None = None
    in_watchlist: bool = False

    model_config = {"from_attributes": True}


class SimilarMovie(BaseModel):
    id: int
    title: str
    year: int | None
    poster_path: str | None
    score: float

    model_config = {"from_attributes": True}
