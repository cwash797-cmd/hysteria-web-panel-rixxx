from datetime import datetime, timedelta, UTC
from secrets import token_urlsafe
import hmac
from fastapi import HTTPException, Header
from typing import Dict, Optional, Tuple

from .config import get_settings


_token_store: Dict[str, datetime] = {}


def login(username: str, password: str) -> Tuple[str, int]:
    settings = get_settings()
    user_ok = hmac.compare_digest(username, settings.admin_user)
    pass_ok = hmac.compare_digest(password, settings.admin_password)
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = token_urlsafe(32)
    expiry = datetime.now(UTC) + timedelta(minutes=settings.token_ttl_minutes)
    _token_store[token] = expiry
    return token, settings.token_ttl_minutes * 60


def _is_token_valid(token: str) -> bool:
    expiry = _token_store.get(token)
    if not expiry:
        return False

    if datetime.now(UTC) >= expiry:
        _token_store.pop(token, None)
        return False
    return True


def require_bearer(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not _is_token_valid(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    settings = get_settings()
    keys = settings.api_keys
    if not keys:
        raise HTTPException(status_code=503, detail="API keys are not configured")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    if not any(hmac.compare_digest(x_api_key, key) for key in keys):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
