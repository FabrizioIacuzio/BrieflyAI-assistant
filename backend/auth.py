"""
auth.py — In-memory token authentication with expiry.
Tokens expire after TOKEN_TTL_HOURS; server restart invalidates all sessions.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header, HTTPException, Query

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 24

# token -> {"username": str, "expires_at": datetime}
_active_tokens: dict[str, dict] = {}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    _active_tokens[token] = {
        "username": username,
        "expires_at": _now() + timedelta(hours=TOKEN_TTL_HOURS),
    }
    _purge_expired()
    return token


def revoke_token(token: str) -> None:
    _active_tokens.pop(token, None)


def _purge_expired() -> None:
    """Remove expired tokens to prevent unbounded memory growth."""
    now = _now()
    expired = [t for t, v in _active_tokens.items() if v["expires_at"] < now]
    for t in expired:
        _active_tokens.pop(t, None)


def get_user_from_token(token: str) -> Optional[str]:
    entry = _active_tokens.get(token)
    if entry is None:
        return None
    if entry["expires_at"] < _now():
        _active_tokens.pop(token, None)
        return None
    return entry["username"]


def get_current_user(authorization: str = Header(default="")) -> str:
    """FastAPI dependency for Bearer-token protected routes."""
    token = authorization.removeprefix("Bearer ").strip()
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


# ── Google access token store (in-memory, lost on restart) ────────────────────
_google_tokens: dict[str, str] = {}  # email -> google_access_token

def store_google_access_token(email: str, token: str) -> None:
    _google_tokens[email] = token

def get_google_access_token(email: str) -> Optional[str]:
    return _google_tokens.get(email)


def get_current_user_query(token: str = Query(default="")) -> str:
    """FastAPI dependency for SSE endpoints (token passed as ?token=xxx query param)."""
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
