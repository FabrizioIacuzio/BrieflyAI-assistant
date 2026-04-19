"""
scheduler.py — APScheduler integration for scheduled briefing generation.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _run_scheduled_briefing(schedule_id: int) -> None:
    """
    Async job: fetches articles, runs pipeline, persists briefing, optionally sends email.
    Uses asyncio.to_thread for the blocking LLM/gTTS calls.
    """
    # Import here to avoid circular imports at module load time
    from ..database import SessionLocal
    from ..models import Briefing, Schedule, EmailConfig
    from .news_service import get_articles, apply_filter
    from .briefing_pipeline import cluster_and_rank, generate_script, synthesise_audio
    from .analytics_service import analyze_articles
    from .email_service import send_briefing_email

    db = SessionLocal()
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule or not schedule.enabled:
            return

        logger.info(f"Scheduled briefing starting for schedule {schedule_id}: {schedule.name}")

        # 1. Fetch articles
        articles, source = await asyncio.to_thread(get_articles)
        selected_ids = apply_filter(articles, schedule.filter_preset)
        selected = [a for a in articles if a["ID"] in selected_ids]

        if not selected:
            logger.warning(f"Schedule {schedule_id}: no articles matched filter '{schedule.filter_preset}'")
            return

        # 2. Cluster & rank
        clusters_data = await asyncio.to_thread(cluster_and_rank, selected)

        # 3. Generate script
        script = await asyncio.to_thread(
            generate_script, clusters_data, selected, schedule.duration_minutes
        )

        # 4. Synthesise audio
        temp_filename = f"briefing_sched_{schedule_id}_{int(datetime.utcnow().timestamp())}.mp3"
        await asyncio.to_thread(synthesise_audio, script, temp_filename, schedule.voice_accent)

        # 5. Run analytics
        analytics = await asyncio.to_thread(analyze_articles, selected)

        # 6. Persist briefing
        briefing = Briefing(
            script=script,
            audio_filename=temp_filename,
            duration_minutes=schedule.duration_minutes,
            filter_used=schedule.filter_preset,
            sources_count=len(selected),
            clusters_json=json.dumps(clusters_data),
            analytics_json=json.dumps(analytics),
            articles_json=json.dumps(selected),
            scheduled=True,
        )
        db.add(briefing)
        db.flush()   # get briefing.id

        # Rename audio to include briefing id
        from .briefing_pipeline import AUDIO_DIR
        old_path = AUDIO_DIR / temp_filename
        new_filename = f"briefing_{briefing.id}.mp3"
        new_path = AUDIO_DIR / new_filename
        if old_path.exists():
            old_path.rename(new_path)
        briefing.audio_filename = new_filename

        schedule.last_run_at = datetime.utcnow()
        schedule.last_briefing_id = briefing.id
        db.commit()
        logger.info(f"Scheduled briefing {briefing.id} saved for schedule {schedule_id}")

        # 7. Send email if configured
        if schedule.email_on_done:
            email_cfg = db.query(EmailConfig).first()
            if email_cfg and email_cfg.smtp_user and email_cfg.to_address:
                briefing_dict = {
                    "created_at": briefing.created_at.isoformat(),
                    "script": script,
                    "audio_filename": new_filename,
                    "sources_count": len(selected),
                    "duration_minutes": schedule.duration_minutes,
                    "clusters": clusters_data,
                    "analytics": analytics,
                }
                try:
                    await asyncio.to_thread(
                        send_briefing_email,
                        briefing_dict,
                        email_cfg.smtp_host,
                        email_cfg.smtp_port,
                        email_cfg.smtp_user,
                        email_cfg.smtp_password,
                        email_cfg.from_address,
                        email_cfg.to_address,
                    )
                    logger.info(f"Email sent for briefing {briefing.id}")
                except Exception as e:
                    logger.error(f"Email failed for briefing {briefing.id}: {e}")

    except Exception as e:
        logger.error(f"Scheduled briefing failed for schedule {schedule_id}: {e}")
        db.rollback()
    finally:
        db.close()


def add_job(schedule_id: int, cron_expression: str) -> None:
    scheduler = get_scheduler()
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        scheduler.add_job(
            _run_scheduled_briefing,
            trigger=trigger,
            id=str(schedule_id),
            kwargs={"schedule_id": schedule_id},
            replace_existing=True,
            misfire_grace_time=120,
        )
    except Exception as e:
        logger.error(f"Failed to add job for schedule {schedule_id}: {e}")


def remove_job(schedule_id: int) -> None:
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(str(schedule_id))
    except Exception:
        pass


def load_all_schedules_from_db() -> None:
    """Call at startup to register all enabled schedules into APScheduler."""
    from ..database import SessionLocal
    from ..models import Schedule

    db = SessionLocal()
    try:
        schedules = db.query(Schedule).filter(Schedule.enabled == True).all()
        for s in schedules:
            add_job(s.id, s.cron_expression)
        logger.info(f"Loaded {len(schedules)} schedule(s) into APScheduler")
    finally:
        db.close()
