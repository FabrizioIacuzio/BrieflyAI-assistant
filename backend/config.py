"""
config.py — Application settings read from .env / environment variables.
Validates critical settings at startup and warns about insecure defaults.
"""
import logging
import secrets
import sys

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_KEY = "briefly-change-me-in-production"


class Settings(BaseSettings):
    groq_api_key: str = ""
    newsapi_key:  str = ""

    # Auth — demo credentials (disable in production by leaving demo_user empty)
    demo_user:     str = ""
    demo_password: str = ""

    # Auth — Google OAuth
    google_client_id:     str = ""
    google_client_secret: str = ""

    # SessionMiddleware secret — MUST be set in production
    secret_key: str = _INSECURE_DEFAULT_KEY

    # Where to redirect after Google login (frontend)
    frontend_origin: str = "http://localhost:5173"

    # Runtime flag
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


def validate_settings() -> None:
    """
    Called at startup. Logs warnings for insecure configuration.
    In non-debug mode, exits on critical misconfigurations.
    """
    issues = []

    if settings.secret_key == _INSECURE_DEFAULT_KEY:
        if settings.debug:
            logger.warning(
                "SECRET_KEY is set to the insecure default. "
                "Set SECRET_KEY in .env before deploying to production."
            )
        else:
            issues.append("SECRET_KEY must be changed from the default value in production.")

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY is not set — briefing generation will fail.")

    if settings.debug and settings.demo_user:
        logger.info("Demo login is enabled (DEMO_USER=%s).", settings.demo_user)

    if not settings.debug and settings.demo_user:
        logger.warning(
            "Demo credentials are active in non-debug mode. "
            "Clear DEMO_USER and DEMO_PASSWORD in production."
        )

    if issues:
        for msg in issues:
            logger.critical("SECURITY: %s", msg)
        sys.exit(1)
