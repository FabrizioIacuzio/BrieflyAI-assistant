"""
analytics_service.py — Ported from analytics.py, returns pure dicts (no Plotly, no Streamlit).
"""
import json
import re

from groq import Groq

from ..config import settings

MAX_RETRIES = 3
VALID_SENTIMENTS = ("Positive", "Neutral", "Negative")
VALID_TOPICS = [
    "AI & Tech", "Energy", "Central Banks", "Equities",
    "Commodities", "Macro", "Crypto", "Retail", "Other",
]


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _build_prompt(article: dict, attempt: int) -> str:
    prefix = (
        "CORRECTION: Your previous response was not valid JSON or did not match the schema. "
        "Return ONLY the raw JSON object — no markdown, no code fences.\n\n"
        if attempt > 0 else ""
    )
    content_snippet = str(article.get("Content", ""))[:500]
    return f"""{prefix}You are a quantitative financial analyst. Analyze the news article below and \
return ONLY a valid JSON object. No markdown. No text before or after the JSON.

Article:
  Sender:  {article['Sender']}
  Subject: {article['Subject']}
  Content: {content_snippet}

Return this exact JSON structure:
{{
    "sentiment":        "Positive",
    "sentiment_score":  0.65,
    "urgency":          7,
    "market_impact":    8,
    "topics":           ["AI & Tech", "Equities"],
    "key_entities":     ["NVIDIA", "S&P 500"],
    "one_line_summary": "NVIDIA rally continues on AI chip demand."
}}

Field rules:
- sentiment:        exactly one of {list(VALID_SENTIMENTS)}
- sentiment_score:  float from -1.0 (very bearish) to +1.0 (very bullish)
- urgency:          integer 1–10  (1 = long-term, 10 = breaking)
- market_impact:    integer 1–10  (1 = minimal, 10 = major move)
- topics:           1–3 items from {VALID_TOPICS}
- key_entities:     up to 3 companies, people, or institutions
- one_line_summary: ≤ 15 words
"""


def _validate(parsed: dict, expected_id) -> bool:
    required = ["sentiment", "sentiment_score", "urgency", "market_impact", "topics"]
    if not all(k in parsed for k in required):
        return False
    if parsed["sentiment"] not in VALID_SENTIMENTS:
        return False
    try:
        if not (-1.0 <= float(parsed["sentiment_score"]) <= 1.0):
            return False
        if not (1 <= int(parsed["urgency"]) <= 10):
            return False
        if not (1 <= int(parsed["market_impact"]) <= 10):
            return False
    except (TypeError, ValueError):
        return False
    if not isinstance(parsed.get("topics"), list) or len(parsed["topics"]) == 0:
        return False
    return True


def analyze_articles(articles: list[dict]) -> list[dict]:
    """
    Analyse each article and return a list of analytics dicts.
    Falls back to neutral defaults on failure.
    """
    client = Groq(api_key=settings.groq_api_key)
    results = []

    for article in articles:
        success = False
        for attempt in range(MAX_RETRIES):
            prompt = _build_prompt(article, attempt)
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.05,
                )
                raw = _strip_fences(response.choices[0].message.content)
                parsed = json.loads(raw)
                if _validate(parsed, article["ID"]):
                    parsed["sentiment_score"] = float(parsed["sentiment_score"])
                    parsed["urgency"] = int(parsed["urgency"])
                    parsed["market_impact"] = int(parsed["market_impact"])
                    parsed["email_id"] = article["ID"]
                    parsed["subject"] = article.get("Subject", "")
                    parsed["sender"] = article.get("Sender", "")
                    results.append(parsed)
                    success = True
                    break
            except Exception:
                pass

        if not success:
            results.append({
                "email_id": article["ID"],
                "subject": article.get("Subject", "")[:80],
                "sender": article.get("Sender", ""),
                "sentiment": "Neutral",
                "sentiment_score": 0.0,
                "urgency": 5,
                "market_impact": 5,
                "topics": ["Other"],
                "key_entities": [],
                "one_line_summary": article.get("Subject", "")[:80],
            })

    return results
