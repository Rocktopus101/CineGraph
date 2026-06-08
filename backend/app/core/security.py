import json
import logging
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
_firebase_initialized = False


def normalize_firebase_private_key(key: str) -> str:
    """Normalize PEM keys from .env, Render, or pasted JSON."""
    key = key.strip()
    if not key:
        return key

    if key.startswith("{"):
        parsed = json.loads(key)
        return normalize_firebase_private_key(parsed.get("private_key", ""))

    if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
        key = key[1:-1].strip()

    key = key.replace("\\n", "\n")

    if "\n" not in key and "-----BEGIN PRIVATE KEY-----" in key:
        key = key.replace(
            "-----BEGIN PRIVATE KEY----- ",
            "-----BEGIN PRIVATE KEY-----\n",
        ).replace(
            " -----END PRIVATE KEY-----",
            "\n-----END PRIVATE KEY-----",
        )

    return key


def build_firebase_certificate_dict(settings: Settings) -> dict[str, Any]:
    raw_json = settings.firebase_service_account_json.strip()
    if raw_json:
        data = json.loads(raw_json)
        if isinstance(data, str):
            data = json.loads(data)
        private_key = data.get("private_key")
        if isinstance(private_key, str):
            data["private_key"] = normalize_firebase_private_key(private_key)
        return data

    if not settings.firebase_project_id or not settings.firebase_private_key:
        raise ValueError(
            "Firebase credentials missing. Set FIREBASE_SERVICE_ACCOUNT_JSON "
            "or FIREBASE_PROJECT_ID + FIREBASE_CLIENT_EMAIL + FIREBASE_PRIVATE_KEY."
        )

    return {
        "type": "service_account",
        "project_id": settings.firebase_project_id,
        "private_key": normalize_firebase_private_key(settings.firebase_private_key),
        "client_email": settings.firebase_client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }


def init_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return
    settings = get_settings()
    if settings.dev_mode and not settings.firebase_project_id and not settings.firebase_service_account_json:
        _firebase_initialized = True
        return
    if not settings.firebase_project_id and not settings.firebase_service_account_json:
        return

    try:
        cred = credentials.Certificate(build_firebase_certificate_dict(settings))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("Invalid Firebase credentials: %s", exc)
        raise ValueError(
            "Invalid Firebase credentials. On Render, prefer FIREBASE_SERVICE_ACCOUNT_JSON "
            "with the full downloaded service-account JSON."
        ) from exc

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
