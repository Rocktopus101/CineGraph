from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.movie import MovieDetail, MovieSearchResult, SimilarMovie
from app.services.movie_service import MovieService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=list[MovieSearchResult])
async def search_movies(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, le=50),
):
    svc = MovieService(db)
    movies = await svc.search(q, limit)
    return [MovieSearchResult.model_validate(m) for m in movies]


@router.get("/{movie_id}", response_model=MovieDetail)
async def get_movie(
    movie_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MovieService(db)
    movie = await svc.get_detail(movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    ctx = await svc.get_user_context(movie_id, user.id)
    return MovieDetail(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        original_title=movie.original_title,
        year=movie.year,
        runtime=movie.runtime,
        overview=movie.overview,
        poster_path=movie.poster_path,
        backdrop_path=movie.backdrop_path,
        release_date=movie.release_date,
        vote_average=movie.vote_average,
        letterboxd_uri=movie.letterboxd_uri,
        metadata_json=movie.metadata_json,
        **ctx,
    )


@router.get("/{movie_id}/similar", response_model=list[SimilarMovie])
async def get_similar(
    movie_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, le=20),
):
    svc = MovieService(db)
    similar = await svc.get_similar(movie_id, limit)
    return [SimilarMovie(**s) for s in similar]
