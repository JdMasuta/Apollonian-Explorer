"""
Gasket database model.

Reference: .DESIGN_SPEC.md section 4.1 (Database Schema - Gaskets Table)

This module defines the SQLAlchemy ORM model for storing Apollonian gaskets
with their metadata, caching information, and relationships to circles.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.base import Base


class Gasket(Base):
    """
    Apollonian gasket with metadata and caching information.

    Attributes:
        id: Primary key
        hash: SHA-256 hash of sorted initial curvatures (for cache lookup)
        initial_curvatures: JSON string of curvature list (e.g., '["1", "1", "1"]')
        num_circles: Total number of circles in this gasket
        max_depth_cached: Maximum generation depth cached in database
        created_at: Timestamp when gasket was first generated
        last_accessed_at: Timestamp of last access (for cache eviction)
        access_count: Number of times this gasket has been accessed
        circles: Relationship to Circle objects (one-to-many)

    Reference:
        .DESIGN_SPEC.md section 4.1 - Gaskets table schema
        .DESIGN_SPEC.md section 9.1 - Caching strategy with SHA-256 hashes
    """

    __tablename__ = "gaskets"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Cache key (unique hash of initial curvatures)
    hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    # Initial configuration (stored as JSON string)
    initial_curvatures: Mapped[str] = mapped_column(Text, nullable=False)

    # Statistics
    num_circles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_depth_cached: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # Access tracking (for cache eviction policy)
    access_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    circles: Mapped[List["Circle"]] = relationship(
        "Circle",
        back_populates="gasket",
        cascade="all, delete-orphan",
        lazy="selectin",  # Load circles with gasket by default
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Gasket(id={self.id}, hash={self.hash[:8]}..., "
            f"curvatures={self.initial_curvatures}, "
            f"num_circles={self.num_circles}, "
            f"max_depth={self.max_depth_cached})>"
        )


# Import Circle here to avoid circular imports (will be defined in circle.py)
# This is imported at the bottom to ensure Gasket is defined first
from db.models.circle import Circle  # noqa: E402, F811
