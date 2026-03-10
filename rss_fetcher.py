import feedparser
import pandas as pd
from datetime import datetime
import re

RSS_FEEDS = {
    "Reuters":      "https://feeds.reuters.com/reuters/businessNews",
    "CNBC":         "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "Yahoo Finance":"https://finance.yahoo.com/news/rssindex",
    "The Guardian": "https://www.theguardian.com/uk/business/rss",
    "MarketWatch":  "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadline",
}

FINANCIAL_KEYWORDS = [
    "Fed", "Market", "Earnings", "NVIDIA", "Crude", "Oil", "OPEC", "Inflation",
    "Rate", "ECB", "Rally", "Volatility", "Bond", "Yield", "Stock", "Revenue",
    "Analyst", "Investor", "Treasury", "Central Bank", "Shares", "Trading",
    "Energy", "Growth", "Economy", "Investment", "Equity", "GDP",
    "Recession", "S&P", "Nasdaq", "Dow", "Bitcoin", "Crypto", "Dollar",
    "Commodity", "Futures", "Hedge", "Interest", "Deficit", "Tariff",
]


def _clean_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(entry: dict) -> str:
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:3]).strftime("%Y-%m-%d")
            except Exception:
                pass
    return datetime.now().strftime("%Y-%m-%d")


def _is_financial(subject: str, content: str) -> bool:
    combined = f"{subject} {content}".lower()
    return any(kw.lower() in combined for kw in FINANCIAL_KEYWORDS)


def fetch_live_emails(max_per_feed: int = 6) -> "pd.DataFrame | None":
    """
    Fetch recent news from RSS feeds.
    Returns a DataFrame, or None if all feeds fail (triggers CSV fallback).
    """
    rows = []
    email_id = 1

    for sender, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(
                url,
                request_headers={"User-Agent": "briefly-ai/2.0", "Accept": "application/rss+xml,application/xml,text/xml"},
            )
            if not feed.entries:
                continue

            for entry in feed.entries[:max_per_feed]:
                title = _clean_html(entry.get("title", ""))
                if not title:
                    continue

                # Try multiple fields for body content
                content = ""
                for field in ("summary", "description"):
                    raw = entry.get(field, "")
                    if raw:
                        content = _clean_html(raw)
                        break
                if not content:
                    content_list = entry.get("content", [])
                    if content_list:
                        content = _clean_html(content_list[0].get("value", ""))

                rows.append({
                    "ID":      email_id,
                    "Sender":  sender,
                    "Subject": title[:220],
                    "Date":    _parse_date(entry),
                    "Content": content[:1400],
                    "URL":     entry.get("link", ""),
                })
                email_id += 1

        except Exception:
            continue

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = df.sort_values(["Date", "ID"], ascending=[False, True]).reset_index(drop=True)
    return df
