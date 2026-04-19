"""
database.py — Sync SQLAlchemy engine + session factory.

SQLite is configured with:
  - WAL journal mode   → better concurrent read/write, no full-table locks
  - Foreign key checks → enforced at the SQLite level
  - check_same_thread=False → required for FastAPI thread-pool usage
"""
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path(__file__).parent / "briefly.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    """Apply safety and performance pragmas on every new SQLite connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")      # Write-Ahead Logging
    cursor.execute("PRAGMA foreign_keys=ON")        # Enforce FK constraints
    cursor.execute("PRAGMA synchronous=NORMAL")     # Safe with WAL
    cursor.execute("PRAGMA temp_store=MEMORY")      # Temp tables in RAM
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
