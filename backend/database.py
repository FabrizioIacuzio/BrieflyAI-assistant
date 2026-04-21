"""
database.py — Sync SQLAlchemy engine + session factory.

Supports SQLite (local dev) and PostgreSQL (production via DATABASE_URL env var).
SQLite is configured with WAL mode for better concurrency.
"""
import os
from pathlib import Path

from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_DB_PATH = Path(__file__).parent / "briefly.db"
_DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{_DB_PATH}"

# Heroku/some providers use postgres:// — SQLAlchemy requires postgresql://
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = _DATABASE_URL.startswith("sqlite")

engine = create_engine(
    _DATABASE_URL,
    # SQLite requires check_same_thread=False for FastAPI's thread pool
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Connection pooling for PostgreSQL
    pool_pre_ping=True,
)


if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
