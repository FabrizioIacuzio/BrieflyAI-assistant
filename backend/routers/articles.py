import logging

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..auth import get_current_user
from ..services.news_service import get_articles, apply_filter

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


@router.get("/filter/{filter_name}")
def filter_articles(filter_name: str, user: str = Depends(get_current_user)):
    # filter_name is used only as a lookup key, never executed or reflected
    articles, _ = get_articles()
    ids = apply_filter(articles, filter_name)
    return {"selected_ids": ids}
