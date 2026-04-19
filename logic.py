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

# Maps user-friendly accent names to gTTS tld values.
# Use "us" for American (not "com" — com redirects by geo and often sounds British).
VOICE_ACCENTS = {
    "American (en-US)":    "us",
    "British (en-GB)":     "co.uk",
    "Australian (en-AU)":  "com.au",
    "Indian (en-IN)":      "co.in",
    "Irish (en-IE)":       "ie",
}


def process_reports_and_generate_audio(
    selected_reports,
    duration_minutes: int = 3,
    voice_accent: str = "us",
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
    RAG-style chatbot: answers follow-up questions about articles in the inbox.
    Uses the briefing script (if any) and ALL articles as context.
    Only draws on provided context — does not invent facts.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    articles_ctx = "\n\n".join(
        f"[{r['Sender']}] {r['Subject']}: {str(r.get('Content', ''))[:400]}"
        for _, r in emails_df.iterrows()
    )

    script_part = ""
    if briefing_script and briefing_script.strip():
        script_part = "LATEST BRIEFING SCRIPT (synthesis of selected articles):\n" + briefing_script[:2000] + "\n\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise financial analyst assistant. The user can ask about "
                "any article in their inbox. Answer their question accurately and briefly "
                "(2–4 sentences), drawing ONLY on the briefing script and ALL articles "
                "below. If the answer is not in the provided context, say so clearly. "
                "Use plain text only — no markdown, bold, italics, or headers.\n\n"
                + script_part +
                "ALL ARTICLES IN INBOX:\n" + articles_ctx[:6000]
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


def multi_agent_debate(script: str, emails_df, analytics_df) -> dict:
    """
    Runs a multi-agent evaluation where three personas debate the briefing:
      · Chief Risk Officer (CRO) — risk-focused, conservative
      · Trader — opportunity-focused, actionable
      · Analyst — balanced, data-driven
    Returns a dict with keys: "cro", "trader", "analyst", "consensus"
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # Build a compact context: script excerpt + top analytics data
    script_excerpt = script[:1500] if script else ""

    articles_summary = ""
    if analytics_df is not None and not (hasattr(analytics_df, "empty") and analytics_df.empty):
        rows = []
        for _, r in analytics_df.iterrows():
            sentiment = r.get("sentiment", "Neutral")
            urgency = r.get("urgency", 5)
            impact = r.get("market_impact", 5)
            summary = str(r.get("one_line_summary", ""))[:80]
            rows.append(f"  - {summary} [Sentiment: {sentiment}, Urgency: {urgency}/10, Impact: {impact}/10]")
        articles_summary = "\n".join(rows[:10])

    prompt = f"""You are simulating a financial war room debate. Three experts have just heard this briefing and must evaluate it.

BRIEFING EXCERPT:
{script_excerpt}

ARTICLE ANALYTICS:
{articles_summary}

Give each expert's reaction in 2-3 sentences from their specific perspective. Then write a one-sentence consensus.

Return ONLY a valid JSON object in this exact format:
{{
    "cro": "...",
    "trader": "...",
    "analyst": "...",
    "consensus": "..."
}}

Expert roles:
- cro: Chief Risk Officer. Focuses on downside risks, tail risks, portfolio protection. Identifies what could go wrong.
- trader: Active Trader. Focuses on actionable opportunities, entry/exit signals, sector rotations from this news.
- analyst: Research Analyst. Gives a balanced data-driven view, questions assumptions, contextualises the data.
- consensus: One sentence that all three could agree on.

Return ONLY the JSON object."""

    for attempt in range(3):
        if attempt > 0:
            prompt = "CORRECTION: Return ONLY valid JSON, no markdown fences.\n\n" + prompt
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

    return {
        "cro": "Unable to generate risk assessment at this time.",
        "trader": "Unable to generate trading perspective at this time.",
        "analyst": "Unable to generate analyst view at this time.",
        "consensus": "Analysis temporarily unavailable.",
    }


def detect_briefing_trends(archive: list) -> str:
    """
    Analyses archived briefings using CONTENT (scripts, topics, article subjects)
    that the chart cannot show. Returns insights on thematic shifts, topic evolution,
    and narrative comparison — not just restating the numeric metrics.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    rows = []
    for i, entry in enumerate(archive[:6]):   # cap at 6 to fit more content per briefing
        ts = entry["timestamp"].strftime("%d %b %Y %H:%M")
        adf = entry.get("analytics_df")
        clusters = entry.get("clusters") or {}
        emails_df = entry.get("emails_df")

        # Content the chart cannot show
        script = (entry.get("script") or "")[:500]
        cluster_info = []
        for c in sorted(clusters.get("clusters", []), key=lambda x: x.get("priority", 99)):
            theme = c.get("key_theme", "")
            cluster_info.append(f"{c.get('cluster_name', '')}: {theme}")

        article_subjects = []
        if emails_df is not None and hasattr(emails_df, "iterrows"):
            for _, r in emails_df.iterrows():
                article_subjects.append(str(r.get("Subject", ""))[:80])

        topics_entities = []
        if adf is not None and not (hasattr(adf, "empty") and adf.empty):
            for _, r in adf.iterrows():
                topics = r.get("topics") or []
                entities = r.get("key_entities") or []
                summary = str(r.get("one_line_summary", ""))[:120]
                topics_entities.append(f"  - {topics}; {entities}; {summary}")

        parts = [f"Briefing {i+1} ({ts})"]
        if script:
            parts.append(f"Script excerpt: {script}...")
        if cluster_info:
            parts.append("Clusters/themes: " + " | ".join(cluster_info))
        if article_subjects:
            parts.append("Article subjects: " + "; ".join(article_subjects[:6]))
        if topics_entities:
            parts.append("Per-article (topics, entities, summary):\n" + "\n".join(topics_entities[:5]))

        rows.append("\n".join(parts))

    if not rows:
        return "Not enough archived briefings to detect trends."

    context = "\n\n---\n\n".join(rows)
    prompt = (
        "You are a financial markets analyst comparing multiple briefings over time. "
        "The chart already shows sentiment, urgency, and impact numbers. Your job is to add "
        "insights the chart CANNOT show.\n\n"
        "Analyse the CONTENT below — scripts, themes, article subjects, topics, entities. "
        "Identify 4–6 concrete insights such as:\n"
        "• Thematic shifts: which topics emerged, faded, or recurred across briefings\n"
        "• Narrative comparison: how did coverage of the same theme (e.g. Fed, energy) differ between briefings\n"
        "• Contradictions or tensions: opposing views on a sector or asset across briefings\n"
        "• Story evolution: how a topic (e.g. inflation, tech) was framed over time\n"
        "• Dominant vs marginal themes: what drove each briefing's narrative\n\n"
        "Do NOT simply restate the numeric metrics (sentiment/urgency/impact). Focus on "
        "what the content says, not what the numbers say.\n\n"
        f"{context}\n\n"
        "Write your analysis in 4–6 concise bullet points. Be specific about topics and briefings."
    )

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()
