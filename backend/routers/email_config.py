import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import EmailConfig, EmailConfigUpdate

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/email-config", tags=["email"])


@router.get("")
def get_email_config(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(EmailConfig).first()
    if not cfg:
        return {
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "smtp_user": "", "smtp_password": "",
            "from_address": "", "to_address": "",
        }
    return {
        "smtp_host":     cfg.smtp_host,
        "smtp_port":     cfg.smtp_port,
        "smtp_user":     cfg.smtp_user,
        # Never return real password — return masked placeholder
        "smtp_password": "********" if cfg.smtp_password else "",
        "from_address":  cfg.from_address,
        "to_address":    cfg.to_address,
    }


@router.put("")
def save_email_config(
    body: EmailConfigUpdate,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = db.query(EmailConfig).first()
    if cfg is None:
        cfg = EmailConfig()
        db.add(cfg)

    cfg.smtp_host    = body.smtp_host
    cfg.smtp_port    = body.smtp_port
    cfg.smtp_user    = body.smtp_user
    cfg.from_address = body.from_address
    cfg.to_address   = body.to_address

    # Only update password if a real value was provided (not the masked placeholder)
    if body.smtp_password and body.smtp_password != "********":
        cfg.smtp_password = body.smtp_password

    db.commit()
    return {"ok": True}


@router.post("/test")
@limiter.limit("3/minute")
def test_email(
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.email_service import send_briefing_email

    cfg = db.query(EmailConfig).first()
    if not cfg or not cfg.smtp_user or not cfg.to_address:
        raise HTTPException(400, "Email not fully configured")

    test_briefing = {
        "created_at":       "2026-04-19T07:00",
        "script":           "This is a test email from Briefly AI. Your email configuration is working correctly.",
        "audio_filename":   None,
        "sources_count":    0,
        "duration_minutes": 1,
        "clusters":         {"clusters": [{"cluster_name": "Test", "priority": 1, "key_theme": "Email test", "email_ids": []}]},
        "analytics":        [],
    }

    try:
        send_briefing_email(
            test_briefing,
            cfg.smtp_host, cfg.smtp_port,
            cfg.smtp_user, cfg.smtp_password,
            cfg.from_address, cfg.to_address,
        )
    except Exception:
        logger.error("Test email failed for user %s", user, exc_info=True)
        raise HTTPException(500, "Failed to send test email. Check your SMTP settings.")

    return {"ok": True}
