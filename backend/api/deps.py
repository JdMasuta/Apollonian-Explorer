"""
API dependencies for dependency injection.

Reference: .DESIGN_SPEC.md section 5 (API Endpoints)

This module provides FastAPI dependencies for database sessions
and other shared resources.
"""

from typing import Generator
from sqlalchemy.orm import Session

from db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Provides a SQLAlchemy session for the request lifecycle.
    Automatically closes the session after the request completes.

    Yields:
        SQLAlchemy Session object

    Usage:
        @app.get("/gaskets/{gasket_id}")
        def get_gasket(gasket_id: int, db: Session = Depends(get_db)):
            gasket = db.query(Gasket).filter(Gasket.id == gasket_id).first()
            return gasket

    Reference:
        FastAPI dependency injection:
        https://fastapi.tiangolo.com/tutorial/dependencies/
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
