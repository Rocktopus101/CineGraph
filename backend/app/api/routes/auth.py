from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_firebase_token
from app.models.user import User
from app.schemas.auth import AuthSyncRequest, UserResponse
from app.services.import_service import ImportService
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


@router.post("/sync", response_model=UserResponse)
async def sync_user(
    body: AuthSyncRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    claims = verify_firebase_token(credentials.credentials)
    result = await db.execute(select(User).where(User.firebase_uid == claims["uid"]))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            firebase_uid=claims["uid"],
            email=claims.get("email"),
            display_name=body.display_name or claims.get("name"),
        )
        db.add(user)
        await db.flush()
    else:
        if body.display_name:
            user.display_name = body.display_name

    import_svc = ImportService(db)
    has_import = await import_svc.has_completed_import(user.id)
    return UserResponse(
        id=user.id,
        firebase_uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        letterboxd_username=user.letterboxd_username,
        is_admin=user.is_admin,
        has_completed_import=has_import,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    import_svc = ImportService(db)
    has_import = await import_svc.has_completed_import(user.id)
    return UserResponse(
        id=user.id,
        firebase_uid=user.firebase_uid,
        email=user.email,
        display_name=user.display_name,
        letterboxd_username=user.letterboxd_username,
        is_admin=user.is_admin,
        has_completed_import=has_import,
        created_at=user.created_at,
    )
