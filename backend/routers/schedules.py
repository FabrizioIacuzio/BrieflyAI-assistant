import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Schedule, ScheduleCreate, ScheduleOut
from ..services.scheduler import add_job, remove_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleOut])
def list_schedules(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    schedules = db.query(Schedule).order_by(Schedule.created_at.desc()).all()
    return [ScheduleOut.from_orm_row(s) for s in schedules]


@router.post("", response_model=ScheduleOut)
def create_schedule(body: ScheduleCreate, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validate cron expression (don't reflect input back to avoid injection via error msg)
    try:
        from apscheduler.triggers.cron import CronTrigger
        CronTrigger.from_crontab(body.cron_expression)
    except Exception:
        logger.warning("Invalid cron expression submitted: %r", body.cron_expression)
        raise HTTPException(400, "Invalid cron expression. Use standard crontab format: 'min hour dom mon dow'")

    s = Schedule(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)

    if s.enabled:
        add_job(s.id, s.cron_expression)

    return ScheduleOut.from_orm_row(s)


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, body: ScheduleCreate,
                    user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "Schedule not found")

    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)

    remove_job(schedule_id)
    if s.enabled:
        add_job(s.id, s.cron_expression)

    return ScheduleOut.from_orm_row(s)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "Schedule not found")
    remove_job(schedule_id)
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "Schedule not found")
    s.enabled = not s.enabled
    db.commit()
    if s.enabled:
        add_job(s.id, s.cron_expression)
    else:
        remove_job(s.id)
    return {"enabled": s.enabled}
