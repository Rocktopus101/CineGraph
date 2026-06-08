import json
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.core.config import get_settings

_firebase_initialized = False


def init_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return
    settings = get_settings()
    if settings.dev_mode and not settings.firebase_project_id:
        _firebase_initialized = True
        return
    if not settings.firebase_project_id:
        return
    private_key = settings.firebase_private_key.replace("\\n", "\n")
    cred = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "private_key": private_key,
            "client_email": settings.firebase_client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    firebase_admin.initialize_app(cred)
    _firebase_initialized = True


def verify_firebase_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.dev_mode and not settings.firebase_project_id:
        return {
            "uid": settings.dev_firebase_uid,
            "email": "dev@cinegraph.local",
            "name": "Dev User",
        }
    init_firebase()
    decoded = firebase_auth.verify_id_token(token)
    return decoded
