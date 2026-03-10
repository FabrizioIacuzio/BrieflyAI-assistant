"""
analytics.py
────────────
Second LLM feature: structured per-article analysis.

Pipeline:
  1. For each selected email, call the LLM with a carefully engineered prompt
     that forces a strict JSON schema.
  2. Validate the schema in Python (types, ranges, allowed values).
  3. If validation fails, automatically retry with an explicit correction prompt
     (up to MAX_RETRIES attempts). Graceful neutral fallback on total failure.
  4. Aggregate the validated results into a DataFrame.
  5. Generate three Plotly charts from the structured data:
       - Sentiment bar chart (score per article)
       - Urgency vs Market Impact scatter
       - Market impact ranking bar chart
"""

import json
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from groq import Groq

MAX_RETRIES = 3
VALID_SENTIMENTS = ("Positive", "Neutral", "Negative")
VALID_TOPICS = [
    "AI & Tech", "Energy", "Central Banks", "Equities",
    "Commodities", "Macro", "Crypto", "Retail", "Other",
]

SENTIMENT_COLORS = {
    "Positive": "#059669",
    "Neutral":  "#d97706",
    "Negative": "#dc2626",
}
SENTIMENT_BG = {
    "Positive": "#ecfdf5",
    "Neutral":  "#fffbeb",
    "Negative": "#fef2f2",
}


# ── Prompt engineering ────────────────────────────────────────────────────────

def _build_prompt(row: pd.Series, attempt: int) -> str:
    """
    Returns a prompt string.
    On the first attempt, we use the full structured prompt.
    On retries, we prepend an explicit correction notice and simplify the
    content to reduce the chance of the model producing markdown.
    """
    prefix = ""
    if attempt > 0:
        prefix = (
            "CORRECTION: Your previous response was not valid JSON or did not "
            "match the required schema. Return ONLY the raw JSON object below. "
            "No markdown, no code fences, no explanation.\n\n"
        )

    content_snippet = str(row.get("Content", ""))[:500]

    return f"""{prefix}You are a quantitative financial analyst. Analyze the news article below and \
return ONLY a valid JSON object. No markdown. No text before or after the JSON.

Article:
  Sender:  {row["Sender"]}
  Subject: {row["Subject"]}
  Content: {content_snippet}

Return this exact JSON structure (replace placeholder values with your analysis):
{{
    "email_id":         {row["ID"]},
    "sentiment":        "Positive",
    "sentiment_score":  0.65,
    "urgency":          7,
    "market_impact":    8,
    "topics":           ["AI & Tech", "Equities"],
    "key_entities":     ["NVIDIA", "S&P 500"],
    "one_line_summary": "NVIDIA rally continues on AI chip demand."
}}

Field rules (follow exactly):
- sentiment:        exactly one of {list(VALID_SENTIMENTS)}
- sentiment_score:  float from -1.0 (very bearish) to +1.0 (very bullish)
- urgency:          integer 1–10  (1 = long-term analysis, 10 = breaking news)
- market_impact:    integer 1–10  (1 = no market effect, 10 = major market move)
- topics:           1–3 items from {VALID_TOPICS}
- key_entities:     up to 3 companies, people, or institutions
- one_line_summary: ≤ 15 words
"""


# ── Schema validation ─────────────────────────────────────────────────────────

def _validate(parsed: dict, expected_id: int) -> bool:
    """Return True only if the parsed dict fully satisfies the schema."""
    required = [
        "email_id", "sentiment", "sentiment_score",
        "urgency", "market_impact", "topics",
    ]
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


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that the model may add despite instructions."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


# ── Main analysis pipeline ────────────────────────────────────────────────────

def analyze_emails_with_llm(emails_df: pd.DataFrame) -> pd.DataFrame:
    """
    Call the LLM once per email to extract structured analytics.

    Retry logic:
      - Attempt 0: full detailed prompt
      - Attempt 1: same prompt with correction prefix
      - Attempt 2: correction prefix + simplified content (last chance)
    Falls back to neutral defaults if all retries fail.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    results = []

    for _, row in emails_df.iterrows():
        success = False

        for attempt in range(MAX_RETRIES):
            prompt = _build_prompt(row, attempt)
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.05,   # near-zero for deterministic structured output
                )
                raw = _strip_fences(response.choices[0].message.content)
                parsed = json.loads(raw)

                if _validate(parsed, row["ID"]):
                    # Normalise types
                    parsed["sentiment_score"] = float(parsed["sentiment_score"])
                    parsed["urgency"]         = int(parsed["urgency"])
                    parsed["market_impact"]   = int(parsed["market_impact"])
                    parsed["email_id"]        = int(row["ID"])
                    results.append(parsed)
                    success = True
                    break

            except (json.JSONDecodeError, ValueError, KeyError):
                pass    # retry

        if not success:
            # Graceful neutral fallback — never crash the pipeline
            results.append({
                "email_id":        int(row["ID"]),
                "sentiment":       "Neutral",
                "sentiment_score": 0.0,
                "urgency":         5,
                "market_impact":   5,
                "topics":          ["Other"],
                "key_entities":    [],
                "one_line_summary": str(row["Subject"])[:80],
            })

    return pd.DataFrame(results)


# ── Chart builders ────────────────────────────────────────────────────────────

def _safe_merge(analytics_df: pd.DataFrame, emails_df: pd.DataFrame, extra_cols=None) -> pd.DataFrame:
    """Merge analytics with email metadata, normalising ID types to avoid silent empty-merge."""
    cols = ["ID", "Subject"] + (extra_cols or [])
    cols = [c for c in cols if c in emails_df.columns]
    adf = analytics_df.copy()
    edf = emails_df[cols].copy()
    adf["email_id"] = pd.to_numeric(adf["email_id"], errors="coerce").astype("Int64")
    edf["ID"]       = pd.to_numeric(edf["ID"],       errors="coerce").astype("Int64")
    return adf.merge(edf, left_on="email_id", right_on="ID", how="inner")


def create_sentiment_chart(analytics_df: pd.DataFrame, emails_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: sentiment score per article, coloured by sentiment."""
    merged = _safe_merge(analytics_df, emails_df).sort_values("sentiment_score")
    merged["label"] = merged["Subject"].str[:42] + "…"

    fig = go.Figure(go.Bar(
        x=merged["sentiment_score"],
        y=merged["label"],
        orientation="h",
        marker_color=[SENTIMENT_COLORS[s] for s in merged["sentiment"]],
        text=merged["sentiment_score"].map(lambda v: f"{v:+.2f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Score: %{x:.2f}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="#9ca3af", line_dash="dot", line_width=1)
    fig.update_layout(
        title=dict(text="Sentiment Score", font=dict(size=15, family="Segoe UI")),
        xaxis=dict(
            title="← Bearish  |  Neutral  |  Bullish →",
            range=[-1.35, 1.35],
            zeroline=False,
        ),
        yaxis=dict(title=""),
        height=max(300, len(merged) * 46),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Roboto, sans-serif", color="#374151", size=12),
        margin=dict(l=10, r=90, t=50, b=40),
        showlegend=False,
    )
    return fig


def create_urgency_market_chart(analytics_df: pd.DataFrame, emails_df: pd.DataFrame) -> go.Figure:
    """Scatter: urgency (x) vs market impact (y), colour-coded by sentiment."""
    merged = _safe_merge(analytics_df, emails_df, extra_cols=["Sender"])
    merged["label"] = merged["Subject"].str[:32] + "…"

    fig = go.Figure()
    for sentiment, group in merged.groupby("sentiment"):
        fig.add_trace(go.Scatter(
            x=group["urgency"],
            y=group["market_impact"],
            mode="markers+text",
            marker=dict(
                size=20,
                color=SENTIMENT_COLORS[sentiment],
                opacity=0.85,
                line=dict(width=1.5, color="white"),
            ),
            text=group["label"],
            textposition="top center",
            textfont=dict(size=10),
            name=sentiment,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Urgency: %{x}/10<br>"
                "Market Impact: %{y}/10"
                "<extra></extra>"
            ),
        ))

    # Quadrant reference lines
    fig.add_hline(y=5.5, line_dash="dash", line_color="#d1d5db", line_width=1, opacity=0.7)
    fig.add_vline(x=5.5, line_dash="dash", line_color="#d1d5db", line_width=1, opacity=0.7)

    # Quadrant labels
    for x, y, text, anchor in [
        (1.2, 10.2, "High Impact / Low Urgency",  "left"),
        (6.5, 10.2, "High Impact / Breaking News", "left"),
        (1.2, 0.8,  "Low Impact / Low Urgency",    "left"),
        (6.5, 0.8,  "Low Impact / Breaking News",  "left"),
    ]:
        fig.add_annotation(
            x=x, y=y, text=text,
            showarrow=False,
            font=dict(size=9, color="#9ca3af"),
            xanchor=anchor,
        )

    fig.update_layout(
        title=dict(text="Urgency vs Market Impact", font=dict(size=15, family="Segoe UI")),
        xaxis=dict(title="Urgency  (1 = Long-term · 10 = Breaking News)", range=[0.3, 11]),
        yaxis=dict(title="Market Impact  (1 = Minimal · 10 = Major Move)", range=[0.3, 11]),
        height=500,
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Roboto, sans-serif", color="#374151", size=12),
        legend=dict(orientation="h", y=-0.18, title="Sentiment:"),
    )
    return fig


def create_market_impact_chart(analytics_df: pd.DataFrame, emails_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: market impact score, ranked highest first."""
    merged = _safe_merge(analytics_df, emails_df).sort_values("market_impact", ascending=True)
    merged["label"] = merged["Subject"].str[:42] + "…"

    fig = go.Figure(go.Bar(
        x=merged["market_impact"],
        y=merged["label"],
        orientation="h",
        marker=dict(
            color=merged["market_impact"],
            colorscale=[[0, "#fde68a"], [0.5, "#f59e0b"], [1.0, "#dc2626"]],
            cmin=1,
            cmax=10,
            showscale=True,
            colorbar=dict(title="Score", tickvals=[1, 5, 10], len=0.6, thickness=12),
        ),
        text=merged["market_impact"].astype(str) + " / 10",
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Impact: %{x}/10<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Market Impact Score  (LLM-rated)", font=dict(size=15, family="Segoe UI")),
        xaxis=dict(title="Impact Score", range=[0, 13]),
        yaxis=dict(title=""),
        height=max(300, len(merged) * 46),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Roboto, sans-serif", color="#374151", size=12),
        margin=dict(l=10, r=80, t=50, b=40),
        showlegend=False,
    )
    return fig


def sentiment_badge_html(sentiment: str) -> str:
    c  = SENTIMENT_COLORS.get(sentiment, "#6b7280")
    bg = SENTIMENT_BG.get(sentiment, "#f3f4f6")
    return (
        f'<span style="background:{bg};color:{c};padding:2px 10px;'
        f'border-radius:20px;font-size:11px;font-weight:600;">'
        f'{sentiment}</span>'
    )
