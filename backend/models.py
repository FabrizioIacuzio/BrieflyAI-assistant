"""
models.py — SQLAlchemy ORM models + Pydantic schemas.
All Pydantic schemas include strict input validation to prevent abuse.
"""
import json
import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from .database import Base

# ── Allowed values ─────────────────────────────────────────────────────────────
_VALID_VOICE_ACCENTS = {"us", "co.uk", "com.au", "co.in", "ie"}
_EMAIL_RE            = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")
# Reject RFC-1918 and link-local ranges to prevent SSRF via smtp_host
_PRIVATE_IP_RE       = re.compile(
    r"^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|127\.|169\.254\.|::1|localhost)",
    re.I,
)


# ── ORM models ─────────────────────────────────────────────────────────────────

class User(Base):
    """Persisted Google-authenticated users."""
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    google_id  = Column(String, unique=True, nullable=False, index=True)
    email      = Column(String, unique=True, nullable=False)
    name       = Column(String, nullable=False)
    picture    = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)


class Briefing(Base):
    __tablename__ = "briefings"

    id               = Column(Integer, primary_key=True, index=True)
    created_at       = Column(DateTime, default=datetime.utcnow, index=True)
    script           = Column(Text, nullable=False)
    audio_filename   = Column(String, nullable=True)
    duration_minutes = Column(Integer)
    filter_used      = Column(String)
    sources_count    = Column(Integer)
    clusters_json    = Column(Text)
    analytics_json   = Column(Text)
    articles_json    = Column(Text)
    feedback         = Column(String, nullable=True)
    feedback_note    = Column(Text, nullable=True)
    scheduled        = Column(Boolean, default=False)
    debate_json      = Column(Text, nullable=True)

    def clusters(self) -> dict:
        return json.loads(self.clusters_json or "{}")

    def analytics(self) -> list[dict]:
        return json.loads(self.analytics_json or "[]")

    def articles(self) -> list[dict]:
        return json.loads(self.articles_json or "[]")

    def debate(self) -> Optional[dict]:
        return json.loads(self.debate_json) if self.debate_json else None


class Schedule(Base):
    __tablename__ = "schedules"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String, nullable=False)
    cron_expression  = Column(String, nullable=False)
    filter_preset    = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=3)
    voice_accent     = Column(String, default="us")
    email_on_done    = Column(Boolean, default=True)
    enabled          = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    last_run_at      = Column(DateTime, nullable=True)
    last_briefing_id = Column(Integer, ForeignKey("briefings.id"), nullable=True)


class EmailConfig(Base):
    __tablename__ = "email_config"

    id            = Column(Integer, primary_key=True, index=True)
    smtp_host     = Column(String, default="smtp.gmail.com")
    smtp_port     = Column(Integer, default=587)
    smtp_user     = Column(String, default="")
    smtp_password = Column(String, default="")
    from_address  = Column(String, default="")
    to_address    = Column(String, default="")


# ── Pydantic request schemas ───────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=1024)

class LoginResponse(BaseModel):
    token: str
    username: str

class GenerateRequest(BaseModel):
    article_ids:      list[int] = Field(..., min_length=1, max_length=200)
    duration_minutes: int       = Field(3,  ge=1, le=20)
    voice_accent:     str       = Field("us", max_length=20)
    filter_used:      str       = Field("Manual Selection", max_length=100)

    @field_validator("voice_accent")
    @classmethod
    def validate_accent(cls, v: str) -> str:
        if v not in _VALID_VOICE_ACCENTS:
            raise ValueError(f"voice_accent must be one of {_VALID_VOICE_ACCENTS}")
        return v

    @field_validator("article_ids")
    @classmethod
    def validate_ids(cls, v: list[int]) -> list[int]:
        if any(i < 0 or i > 999_999 for i in v):
            raise ValueError("article_ids out of range")
        return list(set(v))   # deduplicate

class GenerateRawRequest(BaseModel):
    articles:         list[dict] = Field(..., min_length=1, max_length=100)
    duration_minutes: int        = Field(5,  ge=1, le=20)
    voice_accent:     str        = Field("us", max_length=20)

    @field_validator("voice_accent")
    @classmethod
    def validate_accent(cls, v: str) -> str:
        if v not in _VALID_VOICE_ACCENTS:
            raise ValueError(f"voice_accent must be one of {_VALID_VOICE_ACCENTS}")
        return v

    @field_validator("articles")
    @classmethod
    def sanitise_articles(cls, v: list[dict]) -> list[dict]:
        cleaned = []
        for art in v:
            cleaned.append({
                "ID":          str(art.get("ID", ""))[:64],
                "title":       str(art.get("title", ""))[:500],
                "description": str(art.get("description", ""))[:1000],
                "content":     str(art.get("content", ""))[:3000],
                "source":      str(art.get("source", ""))[:200],
                "publishedAt": str(art.get("publishedAt", ""))[:50],
                "url":         str(art.get("url", ""))[:500],
            })
        return cleaned

class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    note:   str = Field("", max_length=1000)

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

class ChatResponse(BaseModel):
    answer: str

class ScheduleCreate(BaseModel):
    name:             str  = Field(..., min_length=1, max_length=100)
    cron_expression:  str  = Field(..., min_length=5, max_length=100)
    filter_preset:    str  = Field(..., max_length=100)
    duration_minutes: int  = Field(3, ge=1, le=20)
    voice_accent:     str  = Field("us", max_length=20)
    email_on_done:    bool = True
    enabled:          bool = True

    @field_validator("voice_accent")
    @classmethod
    def validate_accent(cls, v: str) -> str:
        if v not in _VALID_VOICE_ACCENTS:
            raise ValueError(f"voice_accent must be one of {_VALID_VOICE_ACCENTS}")
        return v

    @field_validator("name")
    @classmethod
    def no_control_chars(cls, v: str) -> str:
        if re.search(r"[\x00-\x1f\x7f]", v):
            raise ValueError("name contains invalid characters")
        return v.strip()

class EmailConfigUpdate(BaseModel):
    smtp_host:     str = Field("smtp.gmail.com", max_length=253)
    smtp_port:     int = Field(587, ge=1, le=65535)
    smtp_user:     str = Field(..., max_length=255)
    smtp_password: str = Field(..., max_length=1024)
    from_address:  str = Field(..., max_length=320)
    to_address:    str = Field(..., max_length=320)

    @field_validator("smtp_host")
    @classmethod
    def no_ssrf(cls, v: str) -> str:
        v = v.strip().lower()
        if _PRIVATE_IP_RE.match(v):
            raise ValueError("smtp_host cannot be a private/loopback address")
        # Must look like a hostname or IP (no path/protocol)
        if "/" in v or ":" in v or "@" in v:
            raise ValueError("smtp_host must be a plain hostname or IP address")
        return v

    @field_validator("from_address", "to_address")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip()
        if v and not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("smtp_port")
    @classmethod
    def allowed_ports(cls, v: int) -> int:
        # Only allow standard mail submission ports
        if v not in (25, 465, 587, 2525):
            raise ValueError("smtp_port must be one of: 25, 465, 587, 2525")
        return v


# ── Pydantic response schemas ──────────────────────────────────────────────────

class BriefingOut(BaseModel):
    id:               int
    created_at:       str
    script:           str
    audio_url:        Optional[str]
    duration_minutes: int
    filter_used:      str
    sources_count:    int
    clusters:         dict
    analytics:        list[dict]
    articles:         list[dict]
    feedback:         Optional[int]
    feedback_note:    Optional[str]
    debate:           Optional[dict]
    scheduled:        bool

    @classmethod
    def from_orm_row(cls, b: Briefing) -> "BriefingOut":
        return cls(
            id=b.id,
            created_at=b.created_at.isoformat(),
            script=b.script,
            audio_url=f"/audio/{b.audio_filename}" if b.audio_filename else None,
            duration_minutes=b.duration_minutes or 3,
            filter_used=b.filter_used or "",
            sources_count=b.sources_count or 0,
            clusters=b.clusters(),
            analytics=b.analytics(),
            articles=b.articles(),
            feedback=int(b.feedback) if b.feedback and str(b.feedback).isdigit() else None,
            feedback_note=b.feedback_note,
            debate=b.debate(),
            scheduled=b.scheduled or False,
        )

class ScheduleOut(BaseModel):
    id:               int
    name:             str
    cron_expression:  str
    filter_preset:    str
    duration_minutes: int
    voice_accent:     str
    email_on_done:    bool
    enabled:          bool
    last_run_at:      Optional[str]
    last_briefing_id: Optional[int]

    @classmethod
    def from_orm_row(cls, s: Schedule) -> "ScheduleOut":
        return cls(
            id=s.id,
            name=s.name,
            cron_expression=s.cron_expression,
            filter_preset=s.filter_preset,
            duration_minutes=s.duration_minutes or 3,
            voice_accent=s.voice_accent or "us",
            email_on_done=s.email_on_done,
            enabled=s.enabled,
            last_run_at=s.last_run_at.isoformat() if s.last_run_at else None,
            last_briefing_id=s.last_briefing_id,
        )
