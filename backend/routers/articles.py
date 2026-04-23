import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import get_current_user, get_google_access_token
from ..config import settings
from ..services.news_service import get_articles, apply_filter
from ..services.gmail_service import fetch_gmail_inbox

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("")
def list_articles(user: str = Depends(get_current_user)):
    articles, source = get_articles()
    return {"articles": articles, "source": source}


@router.get("/refresh")
@limiter.limit("5/minute")
def refresh_articles(request: Request, user: str = Depends(get_current_user)):
    """Force a cache refresh — rate limited to prevent NewsAPI quota exhaustion."""
    articles, source = get_articles(force_refresh=True)
    return {"articles": articles, "source": source}


@router.get("/gmail")
@limiter.limit("10/minute")
async def list_gmail_articles(request: Request, user: str = Depends(get_current_user)):
    """Return the user's Gmail inbox in article format, or demo inbox for demo users."""
    if settings.demo_user and user == settings.demo_user:
        from ..services.demo_inbox import get_demo_inbox
        return {"articles": get_demo_inbox(), "source": "Demo Inbox"}

    token = get_google_access_token(user)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Gmail not connected. Please sign out and sign in again with Google."
        )
    try:
        articles = await fetch_gmail_inbox(token, max_results=50)
        return {"articles": articles, "source": "Gmail Inbox"}
    except PermissionError:
        raise HTTPException(status_code=401, detail="Gmail access expired. Please sign in again.")
    except Exception as e:
        logger.error("Gmail fetch error for %s: %s", user, e)
        raise HTTPException(status_code=500, detail="Failed to fetch Gmail inbox.")


@router.get("/filter/{filter_name}")
def filter_articles(filter_name: str, user: str = Depends(get_current_user)):
    # filter_name is used only as a lookup key, never executed or reflected
    articles, _ = get_articles()
    ids = apply_filter(articles, filter_name)
    return {"selected_ids": ids}
