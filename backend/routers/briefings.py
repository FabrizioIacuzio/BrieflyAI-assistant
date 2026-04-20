"""
briefings.py — Briefing generation, retrieval, feedback, chat, debate, trend analysis.
"""
import asyncio
import json
import queue
import threading
import uuid
from pathlib import Path

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import get_current_user

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
from ..database import get_db
from ..models import (
    Briefing, BriefingOut, ChatRequest, ChatResponse,
    FeedbackRequest, GenerateRequest, GenerateRawRequest,
)
from ..services.briefing_pipeline import (
    AUDIO_DIR, answer_question, cluster_and_rank,
    detect_trends, generate_script, multi_agent_debate, synthesise_audio,
)
from ..services.analytics_service import analyze_articles
from ..services.news_service import get_articles

router = APIRouter(prefix="/briefings", tags=["briefings"])

# In-memory job registry: job_id -> queue.Queue of SSE events
_jobs: dict[str, queue.Queue] = {}


def _get_articles_by_ids(article_ids: list[int]) -> list[dict]:
    articles, _ = get_articles()
    return [a for a in articles if a["ID"] in article_ids]


def _pipeline_worker(job_id: str, selected: list[dict], duration: int,
                     voice_accent: str, filter_used: str, db_session_factory) -> None:
    """Run in a background thread; puts SSE events into the job queue."""
    q = _jobs[job_id]

    def emit(step: int | str, status: str, **extra):
        q.put({"step": step, "status": status, **extra})

    try:
        # Stage 1 — Cluster & rank
        emit(0, "running", title="Clustering & ranking articles")
        clusters_data = cluster_and_rank(selected)
        emit(0, "done")

        # Stage 2 — Generate script
        emit(1, "running", title="Generating briefing script")
        script = generate_script(clusters_data, selected, duration)
        emit(1, "done")

        # Stage 3 — Synthesise audio (temp filename, renamed after DB insert)
        emit(2, "running", title="Synthesising audio")
        temp_filename = f"briefing_tmp_{job_id}.mp3"
        synthesise_audio(script, temp_filename, voice_accent)
        emit(2, "done")

        # Stage 4 — Analytics
        emit(3, "running", title="Running AI analysis")
        analytics = analyze_articles(selected)
        emit(3, "done")

        # Persist to DB
        db = db_session_factory()
        try:
            briefing = Briefing(
                script=script,
                audio_filename=temp_filename,
                duration_minutes=duration,
                filter_used=filter_used,
                sources_count=len(selected),
                clusters_json=json.dumps(clusters_data),
                analytics_json=json.dumps(analytics),
                articles_json=json.dumps(selected),
                scheduled=False,
            )
            db.add(briefing)
            db.flush()

            # Rename audio file to include briefing ID
            old_path = AUDIO_DIR / temp_filename
            new_filename = f"briefing_{briefing.id}.mp3"
            new_path = AUDIO_DIR / new_filename
            if old_path.exists():
                old_path.rename(new_path)
            briefing.audio_filename = new_filename

            db.commit()
            emit("complete", "done", briefing_id=briefing.id)
        finally:
            db.close()

    except Exception as exc:
        # Log the real error server-side; send a generic message to the client
        import logging as _log
        _log.getLogger(__name__).error("Pipeline error in job %s: %s", job_id, exc)
        q.put({"step": "error", "status": "error", "message": "Briefing generation failed. Please try again."})
    finally:
        q.put(None)   # sentinel: stream is over


@router.post("/generate")
@limiter.limit("10/minute")
def start_generation(request: Request, body: GenerateRequest, user: str = Depends(get_current_user)):
    selected = _get_articles_by_ids(body.article_ids)
    if not selected:
        raise HTTPException(400, "No valid article IDs provided")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = queue.Queue()

    from ..database import SessionLocal
    thread = threading.Thread(
        target=_pipeline_worker,
        args=(job_id, selected, body.duration_minutes,
              body.voice_accent, body.filter_used, SessionLocal),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


@router.get("/stream/{job_id}")
async def stream_job(job_id: str, token: str = ""):
    from sse_starlette.sse import EventSourceResponse
    from ..auth import get_user_from_token
    if not get_user_from_token(token):
        raise HTTPException(401, "Invalid token")

    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")

    q = _jobs[job_id]

    async def event_generator():
        while True:
            try:
                item = await asyncio.to_thread(q.get, True, 120)
                if item is None:
                    _jobs.pop(job_id, None)
                    break
                yield {"data": json.dumps(item)}
            except Exception:
                break

    return EventSourceResponse(event_generator())


@router.get("", response_model=list[BriefingOut])
def list_briefings(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    briefings = db.query(Briefing).order_by(Briefing.created_at.desc()).limit(50).all()
    return [BriefingOut.from_orm_row(b) for b in briefings]


@router.get("/{briefing_id}", response_model=BriefingOut)
def get_briefing(briefing_id: int, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.query(Briefing).filter(Briefing.id == briefing_id).first()
    if not b:
        raise HTTPException(404, "Briefing not found")
    return BriefingOut.from_orm_row(b)


@router.post("/{briefing_id}/feedback")
def submit_feedback(briefing_id: int, body: FeedbackRequest,
                    user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.query(Briefing).filter(Briefing.id == briefing_id).first()
    if not b:
        raise HTTPException(404, "Briefing not found")
    b.feedback = body.feedback
    b.feedback_note = body.note
    db.commit()
    return {"ok": True}


@router.post("/{briefing_id}/chat", response_model=ChatResponse)
def chat(briefing_id: int, body: ChatRequest,
         user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.query(Briefing).filter(Briefing.id == briefing_id).first()
    if not b:
        raise HTTPException(404, "Briefing not found")
    answer = answer_question(b.script, b.articles(), body.question)
    return ChatResponse(answer=answer)


@router.post("/{briefing_id}/debate")
def run_debate(briefing_id: int, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.query(Briefing).filter(Briefing.id == briefing_id).first()
    if not b:
        raise HTTPException(404, "Briefing not found")
    result = multi_agent_debate(b.script, b.analytics())
    b.debate_json = json.dumps(result)
    db.commit()
    return result


def _normalize_gmail_article(a: dict) -> dict:
    """Map Gmail extension fields (title/source/content) to pipeline fields (Subject/Sender/Content)."""
    return {
        "ID":          a.get("ID"),
        "Subject":     a.get("title")   or a.get("Subject", "(no subject)"),
        "Sender":      a.get("source")  or a.get("Sender",  "Unknown"),
        "Content":     a.get("content") or a.get("Content", ""),
        "description": a.get("description", ""),
        "publishedAt": a.get("publishedAt", ""),
        "url":         a.get("url", ""),
    }


@router.post("/generate-raw")
@limiter.limit("10/minute")
def start_generation_raw(
    request: Request,
    body: GenerateRawRequest,
    user: str = Depends(get_current_user),
):
    """
    Chrome extension variant of /generate.
    Accepts a raw list of articles (Gmail emails) instead of article IDs,
    so articles don't need to be in the Briefly news cache.
    """
    if not body.articles:
        raise HTTPException(400, "No articles provided")

    normalized = [_normalize_gmail_article(a) for a in body.articles]

    job_id = str(uuid.uuid4())
    _jobs[job_id] = queue.Queue()

    from ..database import SessionLocal
    thread = threading.Thread(
        target=_pipeline_worker,
        args=(job_id, normalized, body.duration_minutes,
              body.voice_accent, "gmail", SessionLocal),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@router.post("/trend-analysis")
def trend_analysis(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    briefings = db.query(Briefing).order_by(Briefing.created_at.desc()).limit(6).all()
    if len(briefings) < 2:
        raise HTTPException(400, "Need at least 2 archived briefings for trend analysis")
    rows = [{"created_at": b.created_at.isoformat(), "script": b.script,
              "clusters": b.clusters()} for b in briefings]
    result = detect_trends(rows)
    return {"analysis": result}


@router.post("/{briefing_id}/email")
def send_email(briefing_id: int, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    from ..models import EmailConfig
    from ..services.email_service import send_briefing_email

    b = db.query(Briefing).filter(Briefing.id == briefing_id).first()
    if not b:
        raise HTTPException(404, "Briefing not found")

    cfg = db.query(EmailConfig).first()
    if not cfg or not cfg.smtp_user or not cfg.to_address:
        raise HTTPException(400, "Email not configured. Go to Settings → Email to configure SMTP.")

    briefing_dict = {
        "created_at": b.created_at.isoformat(),
        "script": b.script,
        "audio_filename": b.audio_filename,
        "sources_count": b.sources_count,
        "duration_minutes": b.duration_minutes,
        "clusters": b.clusters(),
        "analytics": b.analytics(),
    }

    try:
        send_briefing_email(
            briefing_dict, cfg.smtp_host, cfg.smtp_port,
            cfg.smtp_user, cfg.smtp_password, cfg.from_address, cfg.to_address,
        )
    except Exception as e:
        raise HTTPException(500, f"Email failed: {e}")

    return {"ok": True}
