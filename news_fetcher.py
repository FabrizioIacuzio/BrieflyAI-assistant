"""
news_fetcher.py
───────────────
Primary data source: NewsAPI (newsapi.org) top business headlines.

Free tier: 100 requests / day, article content truncated to ~200 chars.
We combine `description` + truncated `content` for a richer body.

Requires NEWSAPI_KEY in .streamlit/secrets.toml.
Falls back gracefully (returns None) on any error so the caller can
try the RSS feed or CSV fallback.
"""

import re
from datetime import datetime

import pandas as pd
import requests


def _clean_content(description: str, content: str) -> str:
    """
    NewsAPI truncates content with '... [+N chars]'.
    Combine description + content into the richest body possible.
    """
    content = re.sub(r"\s*\[[\+\d]+ chars?\]$", "", (content or "")).strip()
    description = (description or "").strip()

    if not description:
        return content[:1400]
    if not content or content in description:
        return description[:1400]

    combined = f"{description} {content}"
    return combined[:1400]


def _parse_date(published_at: str) -> str:
    try:
        return datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def fetch_newsapi_articles(api_key: str, max_articles: int = 30) -> "pd.DataFrame | None":
    """
    Fetch top business headlines from NewsAPI.
    Returns a DataFrame with columns matching the rest of the app,
    or None if the request fails or returns no usable articles.
    """
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "category": "business",
        "language": "en",
        "pageSize": min(max_articles, 100),
        "apiKey": api_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return None

        rows = []
        for i, article in enumerate(data.get("articles", [])):
            title = (article.get("title") or "").strip()
            if not title or title == "[Removed]":
                continue

            source  = (article.get("source") or {}).get("name") or "NewsAPI"
            content = _clean_content(
                article.get("description", ""),
                article.get("content", ""),
            )

            rows.append({
                "ID":      i + 1,
                "Sender":  source,
                "Subject": title[:220],
                "Date":    _parse_date(article.get("publishedAt", "")),
                "Content": content,
                "URL":     article.get("url", ""),
            })

        if not rows:
            return None

        df = pd.DataFrame(rows)
        df = df.sort_values(["Date", "ID"], ascending=[False, True]).reset_index(drop=True)
        return df

    except Exception:
        return None


def refresh_csv_from_newsapi(api_key: str, path: str = "data.csv") -> bool:
    """
    Fetch real articles from NewsAPI and save them to the CSV fallback.
    Returns True on success, False on failure.
    """
    df = fetch_newsapi_articles(api_key, max_articles=30)
    if df is None or df.empty:
        return False

    # Drop URL column so it matches the original CSV schema expected everywhere
    df_save = df.drop(columns=["URL"], errors="ignore")
    df_save.to_csv(path, index=False)
    return True
