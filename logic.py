"""
logic.py
────────
Two-step LLM briefing pipeline.

Step 1 — cluster_and_rank_emails()
    The LLM receives a list of article titles and is asked to:
      · Group them into thematic clusters (AI & Tech, Energy, Central Banks, …)
      · Assign a priority (1 = most important) to each cluster
      · Return a ranked list of all email IDs ordered by importance
    Output is a strict JSON schema; malformed responses trigger up to 3 retries
    with a correction prompt.  A safe fallback is used if all retries fail.

Step 2 — generate_briefing_script()
    The LLM receives the cluster structure from Step 1 (preserving topic order
    and key themes) together with the full article content, and generates a
    spoken-word briefing script of an exact target length.
    The prompt enforces broadcast-style prose (no bullets, no headers),
    specific opening/closing lines, and natural inter-topic transitions.

Orchestrator — process_reports_and_generate_audio()
    Calls Steps 1 and 2, then synthesises audio with gTTS.
    Returns (script, audio_path, clusters_data).
"""

import json
import os
import re

import streamlit as st
from groq import Groq
from gtts import gTTS

WORDS_PER_MINUTE = 140
CLUSTER_NAMES = [
    "AI & Tech", "Energy", "Central Banks",
    "Equities", "Commodities", "Macro", "Retail", "Other",
]


# ── Shared utilities ──────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


# ── Step 1: Cluster & rank ────────────────────────────────────────────────────

def _build_cluster_prompt(items_text: str, attempt: int) -> str:
    prefix = (
        "CORRECTION: Your last response was invalid JSON. "
        "Return ONLY the raw JSON object — no markdown, no explanation.\n\n"
        if attempt > 0 else ""
    )
    return f"""{prefix}You are a senior financial analyst. \
Group the news items below by topic and rank them by importance.

Return ONLY a valid JSON object in this exact format:
{{
    "clusters": [
        {{
            "cluster_name": "AI & Tech",
            "priority": 1,
            "email_ids": [1, 4],
            "key_theme": "NVIDIA rally driven by AI chip demand surge"
        }},
        {{
            "cluster_name": "Central Banks",
            "priority": 2,
            "email_ids": [9, 12],
            "key_theme": "Fed signals patience on rate cuts"
        }}
    ],
    "ranked_ids": [1, 4, 9, 12, 5]
}}

Rules:
- cluster_name: one of {CLUSTER_NAMES}
- priority: 1 = most important cluster; use consecutive integers
- email_ids: all IDs that belong to this cluster
- key_theme: ≤ 12 words capturing the cluster's story
- ranked_ids: ALL email IDs, most important first
- Every email ID must appear in exactly one cluster and in ranked_ids

News items:
{items_text}
"""


def cluster_and_rank_emails(client: Groq, emails_df) -> dict:
    """
    Step 1: ask the LLM to cluster and rank the selected emails.
    Validates that the JSON schema is complete and self-consistent.
    Auto-retries up to 3 times with an explicit correction prompt.
    Returns a safe fallback dict on total failure.
    """
    items_text = "\n".join(
        f"ID {row['ID']}: [{row['Sender']}] {row['Subject']}"
        for _, row in emails_df.iterrows()
    )
    all_ids = list(emails_df["ID"])

    for attempt in range(3):
        prompt = _build_cluster_prompt(items_text, attempt)
        try:
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.05,
            )
            raw  = _strip_fences(resp.choices[0].message.content)
            data = json.loads(raw)

            # Schema validation
            assert "clusters" in data and isinstance(data["clusters"], list)
            assert "ranked_ids" in data and isinstance(data["ranked_ids"], list)
            assert len(data["clusters"]) > 0

            # Every cluster must have required keys
            for c in data["clusters"]:
                assert "cluster_name" in c
                assert "email_ids" in c and isinstance(c["email_ids"], list)
                assert "priority" in c

            return data

        except Exception:
            continue

    # Safe fallback: single cluster containing all emails
    return {
        "clusters": [{
            "cluster_name": "Financial News",
            "priority":     1,
            "email_ids":    all_ids,
            "key_theme":    "General financial market updates",
        }],
        "ranked_ids": all_ids,
    }


# ── Step 2: Generate briefing script ─────────────────────────────────────────

def _build_briefing_prompt(context: str, target_words: int, duration_minutes: int) -> str:
    return f"""You are a professional financial news anchor writing a broadcast script for audio playback.

STRICT REQUIREMENTS:
1. Target length: {target_words} words (±10%). Count carefully — this controls audio duration.
2. Opening line (exact): "Good morning, here is your AI financial briefing."
3. Closing line (exact): "Stay informed and have a productive day."
4. Cover topics in the priority order provided — highest-priority cluster first.
5. Allocate airtime proportionally to the number of articles in each cluster.
6. Use natural spoken transitions between topics:
       "Turning now to markets…" / "In energy news…" / "On the monetary policy front…"
7. Prose only — no bullet points, no headers, no markdown.
8. Tone: authoritative, measured, professional broadcast voice.
9. Do NOT invent facts beyond what is given in the source material.

News clusters (in priority order — cover in this sequence):
{context}
"""


def generate_briefing_script(client: Groq, clusters_data: dict, emails_df, duration_minutes: int) -> str:
    """
    Step 2: generate a spoken-word briefing from the cluster structure
    produced in Step 1.  The prompt is deliberately detailed to enforce
    length control, broadcast prose style, and cluster-priority ordering.
    """
    target_words = duration_minutes * WORDS_PER_MINUTE

    # Build context in cluster-priority order
    context_parts = []
    for cluster in sorted(clusters_data.get("clusters", []), key=lambda c: c.get("priority", 99)):
        context_parts.append(
            f"\n### Cluster: {cluster['cluster_name']} "
            f"(Priority {cluster.get('priority', '?')}) — "
            f"{cluster.get('key_theme', '')}"
        )
        for eid in cluster.get("email_ids", []):
            match = emails_df[emails_df["ID"] == eid]
            if not match.empty:
                r = match.iloc[0]
                context_parts.append(
                    f"  · [{r['Sender']}] {r['Subject']}\n"
                    f"    {str(r.get('Content', ''))[:350]}"
                )

    context = "\n".join(context_parts)
    prompt  = _build_briefing_prompt(context, target_words, duration_minutes)

    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.65,
    )
    return resp.choices[0].message.content.strip()


# ── Orchestrator ──────────────────────────────────────────────────────────────

# Maps user-friendly accent names to gTTS tld values
VOICE_ACCENTS = {
    "American (en-US)":    "com",
    "British (en-GB)":     "co.uk",
    "Australian (en-AU)":  "com.au",
    "Indian (en-IN)":      "co.in",
    "Irish (en-IE)":       "ie",
}


def process_reports_and_generate_audio(
    selected_reports,
    duration_minutes: int = 3,
    voice_accent: str = "com",
):
    """
    Full pipeline:
      1. Cluster & rank emails (structured JSON, validated, retried)
      2. Generate briefing script from cluster context
      3. Synthesise MP3 audio with gTTS (accent controlled by voice_accent tld)
    Returns (script: str, audio_path: str, clusters_data: dict)
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    clusters_data = cluster_and_rank_emails(client, selected_reports)
    script        = generate_briefing_script(client, clusters_data, selected_reports, duration_minutes)

    audio_path = "briefing.mp3"
    if os.path.exists(audio_path):
        os.remove(audio_path)

    tts = gTTS(text=script, lang="en", tld=voice_accent)
    tts.save(audio_path)

    return script, audio_path, clusters_data


def answer_briefing_question(briefing_script: str, emails_df, question: str) -> str:
    """
    RAG-style chatbot: answers follow-up questions about the latest briefing.
    Uses the script and source article summaries as context.
    Only draws on provided context — does not invent facts.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    articles_ctx = "\n\n".join(
        f"[{r['Sender']}] {r['Subject']}: {str(r.get('Content', ''))[:300]}"
        for _, r in emails_df.iterrows()
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise financial analyst assistant. The user has just listened "
                "to an AI-generated financial briefing. Answer their follow-up question "
                "accurately and briefly (2–4 sentences), drawing ONLY on the briefing "
                "script and source articles below. If the answer is not in the provided "
                "context, say so clearly.\n\n"
                "BRIEFING SCRIPT:\n" + briefing_script[:2500] +
                "\n\nSOURCE ARTICLES:\n" + articles_ctx[:2500]
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


def detect_briefing_trends(archive: list) -> str:
    """
    Analyses the last N archived briefings and returns an LLM-generated
    trend summary covering sentiment shifts, urgency patterns, and topic frequency.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    rows = []
    for i, entry in enumerate(archive[:8]):   # cap at 8 briefings
        ts  = entry["timestamp"].strftime("%d %b %Y %H:%M")
        adf = entry.get("analytics_df")
        if adf is None or (hasattr(adf, "empty") and adf.empty):
            continue
        avg_sent   = float(adf["sentiment_score"].mean())
        avg_urg    = float(adf["urgency"].mean())
        avg_impact = float(adf["market_impact"].mean())
        sentiments = adf["sentiment"].value_counts().to_dict()
        clusters   = entry.get("clusters") or {}
        topics     = [c["cluster_name"] for c in clusters.get("clusters", [])]
        rows.append(
            f"Briefing {i+1} ({ts}): avg_sentiment={avg_sent:+.2f}, "
            f"avg_urgency={avg_urg:.1f}, avg_impact={avg_impact:.1f}, "
            f"sentiment_breakdown={sentiments}, topics={topics}"
        )

    if not rows:
        return "Not enough archived briefings with analytics data to detect trends."

    context = "\n".join(rows)
    prompt  = (
        "You are a financial markets analyst reviewing a series of AI briefings over time.\n"
        "Below is a summary of each briefing's analytics. Identify 3–5 concrete trends "
        "or patterns, such as: sentiment shifts, rising urgency, dominant or recurring topics, "
        "or any notable changes between briefings. Be specific and quantitative where possible.\n\n"
        f"{context}\n\n"
        "Write your trend analysis in 4–6 concise bullet points."
    )

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=500,
    )
    return resp.choices[0].message.content.strip()
