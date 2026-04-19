"""
news_service.py — Unified news fetching: NewsAPI → RSS → CSV fallback.
Includes topic classification and mock noise emails.
"""
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import feedparser
import pandas as pd
import requests

from ..config import settings

# ── Constants ──────────────────────────────────────────────────────────────────

RSS_FEEDS = {
    "Reuters":      "https://feeds.reuters.com/reuters/businessNews",
    "CNBC":         "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
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

TOPIC_RULES: list[tuple[str, str]] = [
    ("AI & Tech",      r"NVIDIA|artificial intelligence|AI|chip|semiconductor|tech|Microsoft|Google|OpenAI|machine learning"),
    ("Energy",         r"oil|OPEC|crude|gas|refinery|energy|LNG|barrel|pipeline"),
    ("Central Banks",  r"Fed|Federal Reserve|rate|inflation|ECB|monetary|basis point|hawkish|dovish|hike|cut"),
    ("Equities",       r"stock|share|equity|rally|S&P|Nasdaq|Dow|earnings|IPO|dividend"),
    ("Commodities",    r"gold|silver|copper|wheat|corn|soy|commodity|futures|metals"),
    ("Macro",          r"GDP|recession|unemployment|jobs|economy|growth|fiscal|debt|deficit|tariff|trade"),
    ("Crypto",         r"Bitcoin|crypto|blockchain|Ethereum|token|DeFi|NFT|digital asset"),
    ("Retail",         r"retail|consumer|spending|sales|Amazon|Walmart|e-commerce|shopping"),
]

URGENCY_TIERS: list[tuple[int, str]] = [
    (9, r"breaking|emergency|crisis|crash|collapse|default|panic|meltdown"),
    (7, r"surge|plunge|soar|tumble|shock|unprecedented|record"),
    (5, r"rise|fall|gain|loss|report|announce|cut|hike|warning|concern"),
    (3, r"review|analysis|trend|outlook|forecast|update|plan"),
]

MOCK_NOISE_EMAILS = [
    {"ID": 9001, "Sender": "Amazon",      "Subject": "Your order #114-8732641 has shipped",         "Date": "2026-04-19", "Content": "Hi, your Kindle Paperwhite is on its way. Tracking: 1Z999AA10123456784. Estimated delivery Tuesday.",       "URL": ""},
    {"ID": 9002, "Sender": "LinkedIn",    "Subject": "7 people viewed your profile this week",       "Date": "2026-04-19", "Content": "Your profile is getting noticed! 7 people viewed it this week, including 3 recruiters.",                   "URL": ""},
    {"ID": 9003, "Sender": "HR Dept",     "Subject": "Q1 Performance Review — action required",      "Date": "2026-04-18", "Content": "Performance reviews are due by Friday. Complete your self-assessment in Workday under the Performance module.", "URL": ""},
    {"ID": 9004, "Sender": "Spotify",     "Subject": "Your 2026 listening stats are here",           "Date": "2026-04-18", "Content": "You listened to 312 hours of music this year. Your top genre was Jazz.",                                   "URL": ""},
    {"ID": 9005, "Sender": "GitHub",      "Subject": "PR #847 merged into main",                     "Date": "2026-04-17", "Content": "briefly-ai/briefly: feat: add multi-agent debate panel merged by FabrizioIacuzio.",                       "URL": ""},
]

# TTL cache
_cache: dict = {"data": None, "fetched_at": 0, "source": None}
CACHE_TTL = 300   # 5 minutes


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_rss_date(entry: dict) -> str:
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:3]).strftime("%Y-%m-%d")
            except Exception:
                pass
    return datetime.now().strftime("%Y-%m-%d")


def _parse_newsapi_date(published_at: str) -> str:
    try:
        return datetime.fromisoformat(published_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def get_topic(subject: str, content: str) -> str:
    combined = f"{subject} {content}"
    for topic, pattern in TOPIC_RULES:
        if re.search(pattern, combined, re.I):
            return topic
    return "Other"


def get_urgency(subject: str) -> int:
    for score, pattern in URGENCY_TIERS:
        if re.search(pattern, subject, re.I):
            return score
    return 2


def _is_financial(subject: str, content: str) -> bool:
    combined = f"{subject} {content}".lower()
    return any(kw.lower() in combined for kw in FINANCIAL_KEYWORDS)


def _enrich(rows: list[dict]) -> list[dict]:
    """Add topic, urgency, is_financial fields to each row."""
    for row in rows:
        subj = row.get("Subject", "")
        cont = row.get("Content", "")
        row["topic"] = get_topic(subj, cont)
        row["urgency_kw"] = get_urgency(subj)
        row["is_financial"] = _is_financial(subj, cont)
    return rows


def _from_newsapi(api_key: str) -> Optional[list[dict]]:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"category": "business", "language": "en", "pageSize": 30, "apiKey": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return None
        rows = []
        for i, art in enumerate(data.get("articles", [])):
            title = (art.get("title") or "").strip()
            if not title or title == "[Removed]":
                continue
            desc = (art.get("description") or "").strip()
            cont = re.sub(r"\s*\[[\+\d]+ chars?\]$", "", (art.get("content") or "")).strip()
            content = f"{desc} {cont}".strip()[:1400]
            rows.append({
                "ID": i + 1, "Sender": (art.get("source") or {}).get("name") or "NewsAPI",
                "Subject": title[:220], "Date": _parse_newsapi_date(art.get("publishedAt", "")),
                "Content": content, "URL": art.get("url", ""),
            })
        return rows or None
    except Exception:
        return None


def _from_rss() -> Optional[list[dict]]:
    rows, email_id = [], 1
    for sender, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers={
                "User-Agent": "briefly-ai/2.0",
                "Accept": "application/rss+xml,application/xml,text/xml",
            })
            for entry in feed.entries[:6]:
                title = _clean_html(entry.get("title", ""))
                if not title:
                    continue
                content = ""
                for field in ("summary", "description"):
                    raw = entry.get(field, "")
                    if raw:
                        content = _clean_html(raw)
                        break
                if not content:
                    cl = entry.get("content", [])
                    if cl:
                        content = _clean_html(cl[0].get("value", ""))
                rows.append({
                    "ID": email_id, "Sender": sender, "Subject": title[:220],
                    "Date": _parse_rss_date(entry), "Content": content[:1400],
                    "URL": entry.get("link", ""),
                })
                email_id += 1
        except Exception:
            continue
    return rows or None


def _from_csv() -> list[dict]:
    csv_path = Path(__file__).parent.parent.parent / "data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df.to_dict("records")
    # Ultimate fallback: hand-coded samples
    return [
        {"ID": 1, "Sender": "Reuters", "Subject": "Fed signals patience on rate cuts amid sticky inflation", "Date": "2026-04-19", "Content": "The Federal Reserve signaled it will keep rates higher for longer as inflation remains above the 2% target.", "URL": ""},
        {"ID": 2, "Sender": "Bloomberg", "Subject": "NVIDIA beats earnings expectations on AI chip demand surge", "Date": "2026-04-19", "Content": "NVIDIA reported quarterly earnings that exceeded analyst expectations, driven by unprecedented demand for AI chips.", "URL": ""},
        {"ID": 3, "Sender": "CNBC", "Subject": "Oil prices slip as OPEC+ mulls output increase", "Date": "2026-04-18", "Content": "Crude oil prices fell after reports that OPEC+ members are considering raising production targets.", "URL": ""},
    ]


def get_articles(force_refresh: bool = False) -> tuple[list[dict], str]:
    """
    Returns (articles, source_label) — uses TTL cache.
    source_label is one of: "NewsAPI", "Live RSS", "Sample Data"
    Articles include both financial and noise emails.
    """
    now = time.time()
    if not force_refresh and _cache["data"] and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["data"], _cache["source"]

    financial_rows = None
    source = "Sample Data"

    if settings.newsapi_key:
        financial_rows = _from_newsapi(settings.newsapi_key)
        if financial_rows:
            source = "NewsAPI"

    if financial_rows is None:
        financial_rows = _from_rss()
        if financial_rows:
            source = "Live RSS"

    if financial_rows is None:
        financial_rows = _from_csv()

    all_rows = _enrich(financial_rows) + list(MOCK_NOISE_EMAILS)

    _cache["data"] = all_rows
    _cache["fetched_at"] = now
    _cache["source"] = source
    return all_rows, source


def apply_filter(articles: list[dict], filter_name: str) -> list[int]:
    """Return IDs of articles that match the given filter preset."""
    fin = [a for a in articles if a.get("is_financial")]
    today = datetime.now().strftime("%Y-%m-%d")

    MAJOR_SOURCES = {"Bloomberg", "Reuters", "CNBC", "Wall Street Journal", "Financial Times",
                     "Forbes", "MarketWatch", "Yahoo Finance", "BBC Business", "AP News"}

    if filter_name == "Market Volatility":
        kws = r"surge|plunge|volatility|spike|crash|meltdown|soar|tumble"
        return [a["ID"] for a in fin if re.search(kws, f"{a['Subject']} {a['Content']}", re.I)]
    elif filter_name == "Tech & AI Sector":
        kws = r"NVIDIA|chip|semiconductor|artificial intelligence|\bAI\b|tech|OpenAI"
        return [a["ID"] for a in fin if re.search(kws, f"{a['Subject']} {a['Content']}", re.I)]
    elif filter_name == "Bullish Sentiment":
        kws = r"growth|higher|positive|beat|record|surge|rally|gains"
        return [a["ID"] for a in fin if re.search(kws, f"{a['Subject']} {a['Content']}", re.I)]
    elif filter_name == "Central Banks & Rates":
        kws = r"Fed|Federal Reserve|rate|ECB|central bank|inflation|basis point|hike|cut"
        return [a["ID"] for a in fin if re.search(kws, f"{a['Subject']} {a['Content']}", re.I)]
    elif filter_name == "Global Energy":
        kws = r"oil|OPEC|crude|gas|energy|refinery|LNG|barrel"
        return [a["ID"] for a in fin if re.search(kws, f"{a['Subject']} {a['Content']}", re.I)]
    elif filter_name == "Last 24 Hours":
        return [a["ID"] for a in fin if a.get("Date", "") >= today]
    elif filter_name == "Major Sources Only":
        return [a["ID"] for a in fin if a.get("Sender", "") in MAJOR_SOURCES]
    else:   # Manual Selection — return all financial IDs
        return [a["ID"] for a in fin]
