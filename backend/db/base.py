"""
SQLAlchemy database base configuration.

Reference: .DESIGN_SPEC.md section 4 (Database Schema)

This module provides:
- SQLAlchemy declarative base
- Database engine creation
- Session factory
- Table creation utility
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Use relative import to avoid "backend" module issues
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
