"""
auth.py — Login routes: demo credentials + Google OAuth 2.0.

Google OAuth flow:
  1. GET /api/auth/google          → redirect to Google consent screen
  2. GET /api/auth/google/callback → exchange code, upsert User row, issue token
  3. Redirect to {frontend}/oauth-callback?token=…&username=…&picture=…

Extension flow (token exchange):
  POST /api/auth/google-token — accepts a Google access token obtained by the
  Chrome extension via chrome.identity.getAuthToken(), verifies it with Google's
  userinfo endpoint, upserts the User row, and returns a Briefly session token.
"""
import logging
import re
from datetime import datetime
from pydantic import BaseModel

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_user, revoke_token
from ..config import settings
from ..database import get_db
from ..models import LoginRequest, LoginResponse, User

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")

router = APIRouter(prefix="/auth", tags=["auth"])

# ── OAuth client (initialised once at import time) ────────────────────────────

_oauth = OAuth()
_oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ── Demo / password login ─────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest):
    if body.username == settings.demo_user and body.password == settings.demo_password:
        token = create_token(body.username)
        logger.info("Login success: %s", body.username)
        return LoginResponse(token=token, username=body.username)
    logger.warning("Login failed for username: %s", body.username)
    raise HTTPException(status_code=401, detail="Invalid username or password")


@router.post("/logout")
def logout(authorization: str = Header(default="")):
    """Revoke the caller's session token. Always returns 200 to avoid oracle attacks."""
    token = authorization.removeprefix("Bearer ").strip()
    if token:
        revoke_token(token)
    return {"ok": True}


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
async def google_login(request: Request):
    """Redirect the browser to Google's consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured.")
    redirect_uri = f"{request.base_url}api/auth/google/callback"
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google redirects here after the user grants access.
    We exchange the code, upsert the User row, create a session token,
    then send the browser back to the React frontend.
    """
    try:
        token_data = await _oauth.google.authorize_access_token(request)
    except Exception as exc:
        logger.error("Google OAuth callback error: %s", exc)
        raise HTTPException(status_code=400, detail="OAuth authentication failed")

    info = token_data.get("userinfo") or {}
    google_id = info.get("sub")
    email     = info.get("email", "")
    name      = info.get("name") or email.split("@")[0]
    # Sanitise picture URL — must be https
    raw_picture = info.get("picture", "")
    picture = raw_picture if raw_picture.startswith("https://") else ""

    if not google_id or not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid identity from Google")

    user = db.query(User).filter(User.google_id == google_id).first()
    if user is None:
        user = User(google_id=google_id, email=email, name=name, picture=picture)
        db.add(user)
    else:
        user.name       = name
        user.picture    = picture
        user.last_login = datetime.utcnow()
    db.commit()

    session_token = create_token(email)
    logger.info("Google OAuth login: %s", email)

    import urllib.parse
    params = urllib.parse.urlencode({
        "token":    session_token,
        "username": name,
        "email":    email,
        "picture":  picture,
    })
    return RedirectResponse(url=f"{settings.frontend_origin}/oauth-callback?{params}")


# ── Chrome extension: token exchange ─────────────────────────────────────────

class GoogleTokenRequest(BaseModel):
    google_access_token: str


@router.post("/google-token")
@limiter.limit("20/minute")
async def google_token_exchange(request: Request, body: GoogleTokenRequest, db: Session = Depends(get_db)):
    """
    Chrome extension calls this with a Google access token
    (obtained via chrome.identity.getAuthToken).
    We verify it with Google, upsert the User row, and return a Briefly session token.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {body.google_access_token}"},
                timeout=10,
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach Google identity service")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")

    info = resp.json()
    google_id = info.get("sub")
    email     = info.get("email", "")
    name      = info.get("name") or email.split("@")[0]
    raw_picture = info.get("picture", "")
    picture = raw_picture if raw_picture.startswith("https://") else ""

    if not google_id or not email or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid identity from Google")

    user = db.query(User).filter(User.google_id == google_id).first()
    if user is None:
        user = User(google_id=google_id, email=email, name=name, picture=picture)
        db.add(user)
    else:
        user.name       = name
        user.picture    = picture
        user.last_login = datetime.utcnow()
    db.commit()

    session_token = create_token(email)
    logger.info("Extension token exchange: %s", email)
    return {"token": session_token, "username": name, "email": email, "picture": picture}


# ── Current user info (Google users only) ────────────────────────────────────

@router.get("/me")
def me(user_email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the DB profile for the logged-in Google user, or None for demo users."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"email": user_email, "name": user_email, "picture": None}
    return {
        "email":      user.email,
        "name":       user.name,
        "picture":    user.picture,
        "created_at": user.created_at.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
