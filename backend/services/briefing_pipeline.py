"""
briefing_pipeline.py — Ported from logic.py, refactored for FastAPI.
No Streamlit dependencies. Broken into 4 callable stages for SSE progress.
"""
import json
import os
import re
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from groq import Groq
from gtts import gTTS

from ..config import settings

WORDS_PER_MINUTE = 140
CLUSTER_NAMES = [
    "AI & Tech", "Energy", "Central Banks",
    "Equities", "Commodities", "Macro", "Retail", "Other",
]
VOICE_ACCENTS = {
    "American (en-US)":   "us",
    "British (en-GB)":    "co.uk",
    "Australian (en-AU)": "com.au",
    "Indian (en-IN)":     "co.in",
    "Irish (en-IE)":      "ie",
}

AUDIO_DIR = Path(__file__).parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _client() -> Groq:
    return Groq(api_key=settings.groq_api_key)


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


# ── Stage 1: Cluster & rank ────────────────────────────────────────────────────

def _build_cluster_prompt(items_text: str, attempt: int, preference_hint: str = "") -> str:
    prefix = (
        "CORRECTION: Your last response was invalid JSON. "
        "Return ONLY the raw JSON object — no markdown, no explanation.\n\n"
        if attempt > 0 else ""
    )
    preference_section = (
        f"\nUser preference signal (adjust ranking accordingly): {preference_hint}\n"
        if preference_hint else ""
    )
    return f"""{prefix}You are a senior financial analyst. Group the news items below by topic and rank them by importance.
{preference_section}
Return ONLY a valid JSON object in this exact format:
{{
    "clusters": [
        {{"cluster_name": "AI & Tech", "priority": 1, "email_ids": [1, 4], "key_theme": "NVIDIA rally on AI chip demand"}},
        {{"cluster_name": "Central Banks", "priority": 2, "email_ids": [9, 12], "key_theme": "Fed signals patience on rate cuts"}}
    ],
    "ranked_ids": [1, 4, 9, 12, 5]
}}

Rules:
- cluster_name: one of {CLUSTER_NAMES}
- priority: 1 = most important; consecutive integers
- key_theme: ≤ 12 words
- ranked_ids: ALL IDs, most important first
- Every ID in exactly one cluster and in ranked_ids

News items:
{items_text}
"""


def cluster_and_rank(articles: list[dict], preference_hint: str = "") -> dict:
    """Stage 1: cluster and rank articles. Returns clusters_data dict."""
    items_text = "\n".join(
        f"ID {a['ID']}: [{a['Sender']}] {a['Subject']}"
        for a in articles
    )
    all_ids = [a["ID"] for a in articles]
    client = _client()

    for attempt in range(3):
        prompt = _build_cluster_prompt(items_text, attempt, preference_hint)
        try:
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.05,
            )
            raw = _strip_fences(resp.choices[0].message.content)
            data = json.loads(raw)
            assert "clusters" in data and isinstance(data["clusters"], list)
            assert "ranked_ids" in data and isinstance(data["ranked_ids"], list)
            assert len(data["clusters"]) > 0
            for c in data["clusters"]:
                assert "cluster_name" in c and "email_ids" in c and "priority" in c
            return data
        except Exception:
            continue

    return {
        "clusters": [{"cluster_name": "Financial News", "priority": 1,
                      "email_ids": all_ids, "key_theme": "General financial market updates"}],
        "ranked_ids": all_ids,
    }


# ── Stage 2: Generate briefing script ─────────────────────────────────────────

def generate_script(clusters_data: dict, articles: list[dict], duration_minutes: int) -> str:
    """Stage 2: generate spoken-word briefing script from cluster structure."""
    target_words = duration_minutes * WORDS_PER_MINUTE
    articles_map = {a["ID"]: a for a in articles}

    context_parts = []
    for cluster in sorted(clusters_data.get("clusters", []), key=lambda c: c.get("priority", 99)):
        context_parts.append(
            f"\n### Cluster: {cluster['cluster_name']} "
            f"(Priority {cluster.get('priority', '?')}) — {cluster.get('key_theme', '')}"
        )
        for eid in cluster.get("email_ids", []):
            a = articles_map.get(eid)
            if a:
                context_parts.append(
                    f"  · [{a['Sender']}] {a['Subject']}\n"
                    f"    {str(a.get('Content', ''))[:350]}"
                )

    context = "\n".join(context_parts)
    prompt = f"""You are a professional financial news anchor writing a broadcast script for audio playback.

STRICT REQUIREMENTS:
1. Target length: {target_words} words (±10%).
2. Opening line (exact): "Good morning, here is your AI financial briefing."
3. Closing line (exact): "Stay informed and have a productive day."
4. Cover topics in the priority order provided.
5. Prose only — no bullet points, no headers, no markdown.
6. Tone: authoritative, measured, professional broadcast voice.
7. Do NOT invent facts beyond what is given in the source material.

News clusters (in priority order):
{context}
"""

    client = _client()
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.65,
    )
    return resp.choices[0].message.content.strip()


# ── Stage 3: Synthesise audio ─────────────────────────────────────────────────

def synthesise_audio(script: str, audio_filename: str, voice_tld: str = "us") -> Path:
    """Stage 3: convert script to MP3. Returns the saved file path."""
    # Validate filename to prevent path traversal
    if not re.match(r"^[\w\-]+\.mp3$", audio_filename):
        raise ValueError(f"Invalid audio filename: {audio_filename!r}")
    audio_path = AUDIO_DIR / audio_filename
    if not audio_path.resolve().is_relative_to(AUDIO_DIR.resolve()):
        raise ValueError("Path traversal detected in audio filename")
    tts = gTTS(text=script, lang="en", tld=voice_tld)
    tts.save(str(audio_path))
    return audio_path


# ── Chatbot ───────────────────────────────────────────────────────────────────

def answer_question(briefing_script: str, articles: list[dict], question: str) -> str:
    """RAG-style Q&A over the briefing context."""
    client = _client()

    articles_ctx = "\n\n".join(
        f"[{a['Sender']}] {a['Subject']}: {str(a.get('Content', ''))[:400]}"
        for a in articles
    )
    script_part = ""
    if briefing_script and briefing_script.strip():
        script_part = "LATEST BRIEFING SCRIPT:\n" + briefing_script[:2000] + "\n\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise financial analyst assistant. Answer in 2–4 sentences, "
                "drawing ONLY on the briefing script and articles below. If the answer is "
                "not in the context, say so. Use plain text only.\n\n"
                + script_part
                + "ALL ARTICLES IN INBOX:\n" + articles_ctx[:6000]
            ),
        },
        {"role": "user", "content": question},
    ]

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=350,
    )
    return resp.choices[0].message.content.strip()


# ── Multi-agent debate ─────────────────────────────────────────────────────────

def multi_agent_debate(script: str, analytics_rows: list[dict]) -> dict:
    """Three expert personas debate the briefing."""
    client = _client()

    script_excerpt = script[:1500] if script else ""
    articles_summary = "\n".join(
        f"  - {r.get('one_line_summary', '')} "
        f"[Sentiment: {r.get('sentiment','?')}, Urgency: {r.get('urgency','?')}/10, "
        f"Impact: {r.get('market_impact','?')}/10]"
        for r in analytics_rows[:10]
    )

    prompt = f"""Simulate a financial war-room debate. Three experts have just heard this briefing.

BRIEFING EXCERPT:
{script_excerpt}

ARTICLE ANALYTICS:
{articles_summary}

Return ONLY a valid JSON object:
{{
    "cro": "...",
    "trader": "...",
    "analyst": "...",
    "consensus": "..."
}}

Expert roles (2-3 sentences each):
- cro: Chief Risk Officer. Downside risks, tail risks, portfolio protection.
- trader: Active Trader. Actionable opportunities, entry/exit signals, sector rotations.
- analyst: Research Analyst. Balanced, data-driven, questions assumptions.
- consensus: One sentence all three can agree on."""

    for attempt in range(3):
        if attempt > 0:
            prompt = "CORRECTION: Return ONLY valid JSON.\n\n" + prompt
        try:
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=500,
            )
            raw = _strip_fences(resp.choices[0].message.content)
            data = json.loads(raw)
            assert all(k in data for k in ("cro", "trader", "analyst", "consensus"))
            return data
        except Exception:
            continue

    return {"cro": "Analysis unavailable.", "trader": "Analysis unavailable.",
            "analyst": "Analysis unavailable.", "consensus": "Analysis temporarily unavailable."}


# ── Trend detection ────────────────────────────────────────────────────────────

def detect_trends(briefings: list[dict]) -> str:
    """Analyse content across multiple archived briefings."""
    client = _client()
    rows = []
    for i, b in enumerate(briefings[:6]):
        clusters = b.get("clusters") or {}
        cluster_info = " | ".join(
            f"{c.get('cluster_name')}: {c.get('key_theme', '')}"
            for c in sorted(clusters.get("clusters", []), key=lambda x: x.get("priority", 99))
        )
        script = (b.get("script") or "")[:400]
        parts = [f"Briefing {i+1} ({b.get('created_at', '')[:10]})"]
        if script:
            parts.append(f"Script excerpt: {script}...")
        if cluster_info:
            parts.append(f"Clusters: {cluster_info}")
        rows.append("\n".join(parts))

    if not rows:
        return "Not enough briefings for trend analysis."

    prompt = (
        "You are a financial analyst comparing multiple briefings over time. "
        "The numeric metrics are already shown in charts. Focus on CONTENT insights:\n\n"
        "- Thematic shifts: which topics emerged, faded, or recurred\n"
        "- Narrative comparison: how coverage of the same theme differed\n"
        "- Contradictions or tensions across briefings\n"
        "- Story evolution and framing changes\n\n"
        "Do NOT restate numeric metrics. Write 4–6 concise bullet points.\n\n"
        + "\n\n---\n\n".join(rows)
    )

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()
