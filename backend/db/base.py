"""
SQLAlchemy database base configuration.

Reference: .DESIGN_SPEC.md section 4 (Database Schema)

This module provides:
- SQLAlchemy declarative base
- Database engine creation
- Session factory
- Table creation utility
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# Create SQLAlchemy declarative base
Base = declarative_base()

# Create database engine
# - connect_args for SQLite: check_same_thread=False allows FastAPI async
# - echo=True in debug mode for SQL logging
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=settings.DEBUG,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Tune every new SQLite connection for safe concurrent access.

    The WebSocket persistence worker thread and the FastAPI request threadpool
    write the SAME database file. Default SQLite (rollback journal,
    ``busy_timeout=0``) fails a competing writer *immediately* with
    "database is locked" — which surfaced as a cascade of HTTP 500s during
    viewport deepening (DEBUG_LOG ERR-015). The fix is per-connection:

    - ``journal_mode=WAL``: readers never block the single writer (a viewport
      query can run while a persist commits), and writers serialize cleanly.
    - ``busy_timeout=5000``: a competing writer WAITS up to 5s for the lock
      instead of erroring — our contention windows are sub-second.
    - ``synchronous=NORMAL``: the safe, faster WAL companion (durable across
      application crashes; only an OS/power crash can drop the last
      transactions, and the database stays consistent regardless).

    WAL is a no-op for in-memory databases; the guard keeps non-SQLite
    backends (e.g. a future PostgreSQL) untouched.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()

# Create session factory
# - autocommit=False: require explicit commit()
# - autoflush=False: require explicit flush()
# - bind=engine: attach to our engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def create_tables():
    """
    Create all database tables.

    Should be called once during application startup to ensure
    all tables exist. Safe to call multiple times (idempotent).

    Reference: .DESIGN_SPEC.md sections 4.1-4.4 for table schemas
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.

    WARNING: This will delete all data. Only use in development/testing.
    """
    Base.metadata.drop_all(bind=engine)
