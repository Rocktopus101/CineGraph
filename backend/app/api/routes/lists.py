from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.movie import MovieSearchResult
from app.schemas.user_data import ListDetail, ListSummary
from app.services.list_generator_service import ListGeneratorService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("/", response_model=list[ListSummary])
async def get_lists(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ListGeneratorService(db)
    data = await svc.get_lists(user.id)
    return [ListSummary(**d) for d in data]


@router.get("/{list_id}", response_model=ListDetail)
async def get_list(
    list_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ListGeneratorService(db)
    data = await svc.get_list_detail(user.id, list_id)
    if not data:
        raise HTTPException(404, "List not found")
    return ListDetail(
        id=data["id"],
        name=data["name"],
        list_type=data["list_type"],
        description=data["description"],
        items=[MovieSearchResult.model_validate(m) for m in data["items"]],
    )
