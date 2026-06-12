"""
Circle database model — schema v2 (inversive coordinates).

Reference: REVAMP_BLUEPRINT.md Milestone 2.

Circles are stored in the engine's native representation:

- ``word``: the circle's reduced word in the Apollonian group ('S0'..'S3' for
  the four seed circles, generator digits '0'-'3' otherwise). Unique per
  gasket — the word IS the circle's identity, so re-generation deduplicates
  via the UNIQUE constraint instead of hashes/tolerances.
- Exact inversive coordinates (cocurvature, curvature, kx = b·x, ky = b·y)
  as canonical exact strings ('6', '-3/2', or a SymPy expression string).
  These are the lossless source of truth.
- Float mirrors (b_f, x_f, y_f, r_f) computed incrementally by the walk —
  indexed for viewport (bbox) and resolution queries; presentation only.

This replaces the v1 dual INTEGER-num/denom + tagged-TEXT layout
(migrations/002_inversive_schema.py).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.base import Base


class Circle(Base):
    """A circle (or line) of an Apollonian packing in inversive coordinates."""

    __tablename__ = "circles"
    __table_args__ = (
        UniqueConstraint("gasket_id", "word", name="uq_circles_gasket_word"),
        Index("ix_circles_gasket_generation", "gasket_id", "generation"),
        Index("ix_circles_gasket_radius", "gasket_id", "r_f"),
        Index("ix_circles_gasket_x", "gasket_id", "x_f"),
        Index("ix_circles_gasket_y", "gasket_id", "y_f"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gasket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gaskets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Provenance
    generation: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    word: Mapped[str] = mapped_column(String(64), nullable=False)
    is_line: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Exact inversive coordinates (lossless)
    cocurvature_exact: Mapped[str] = mapped_column(Text, nullable=False)
    curvature_exact: Mapped[str] = mapped_column(Text, nullable=False)
    kx_exact: Mapped[str] = mapped_column(Text, nullable=False)
    ky_exact: Mapped[str] = mapped_column(Text, nullable=False)

    # Float mirrors (lossy, for queries and rendering); NULL center/radius for lines
    b_f: Mapped[float] = mapped_column(Float, nullable=False)
    x_f: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    y_f: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    r_f: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gasket: Mapped["Gasket"] = relationship("Gasket", back_populates="circles")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"Circle(id={self.id}, gasket={self.gasket_id}, word='{self.word}', "
            f"k={self.curvature_exact}, gen={self.generation})"
        )
