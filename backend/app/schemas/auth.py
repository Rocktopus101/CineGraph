from datetime import datetime

from pydantic import BaseModel


class AuthSyncRequest(BaseModel):
    display_name: str | None = None


class UserResponse(BaseModel):
    id: int
    firebase_uid: str
    email: str | None
    display_name: str | None
    letterboxd_username: str | None
    is_admin: bool
    has_completed_import: bool
    created_at: datetime

    model_config = {"from_attributes": True}
