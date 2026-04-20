"""
main.py — FastAPI application entry point.
"""
import html
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from .auth import get_current_user
from .config import settings, validate_settings
from .database import Base, engine
from .routers import articles, auth, briefings, email_config, schedules
from .services.scheduler import get_scheduler, load_all_schedules_from_db

logger = logging.getLogger(__name__)

# ── Rate limiter (shared instance used by routers) ────────────────────────────
limiter = Limiter(key_func=get_remote_address)

AUDIO_DIR = Path(__file__).parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_SAFE_AUDIO_RE = re.compile(r"^briefing_[\w\-]+\.mp3$")


def _seed_demo_user():
    pass   # Auth is config-driven; no DB user table required for the prototype


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    validate_settings()
    Base.metadata.create_all(bind=engine)
    _seed_demo_user()
    load_all_schedules_from_db()
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()

    yield

    # ── Shutdown ──
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Briefly AI",
    description="AI-powered financial briefing API",
    version="2.0.0",
    lifespan=lifespan,
    # Disable API docs in production to reduce attack surface
    openapi_url="/openapi.json" if settings.debug else None,
    docs_url="/docs"            if settings.debug else None,
    redoc_url="/redoc"          if settings.debug else None,
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ────────────────────────────────────────────────────────────────
# SessionMiddleware must be added before CORSMiddleware so authlib can read/write
# the session cookie during the OAuth redirect ↔ callback round-trip.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # Only allow the specific installed extension ID, not all chrome-extension:// origins.
    # Update this when deploying the extension to the Chrome Web Store.
    allow_origin_regex=r"chrome-extension://dhekfikliidfopcllbkdgpekepnipcli",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # HSTS — only add in production (HTTPS). Safe to add now for future-proofing.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Protected audio endpoint (replaces unauthenticated StaticFiles mount) ─────
@app.get("/audio/{filename}")
def serve_audio(
    filename: str,
    request: Request,
    token: str = "",
    authorization: str = Header(default=""),
):
    """
    Serve audio files only to authenticated users.
    Validates filename format to prevent directory traversal.
    """
    from .auth import get_user_from_token
    bearer = authorization.removeprefix("Bearer ").strip()
    if not get_user_from_token(bearer or token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not _SAFE_AUDIO_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid audio filename")

    audio_path = AUDIO_DIR / filename
    # Double-check resolved path stays inside AUDIO_DIR (defence-in-depth)
    if not audio_path.resolve().is_relative_to(AUDIO_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid audio path")

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api")
app.include_router(articles.router,     prefix="/api")
app.include_router(briefings.router,    prefix="/api")
app.include_router(schedules.router,    prefix="/api")
app.include_router(email_config.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
