"""
Circle database model.

Reference: .DESIGN_SPEC.md section 4.2 (Database Schema - Circles Table)

This module defines the SQLAlchemy ORM model for storing circles in an
Apollonian gasket. Circles are stored with exact rational arithmetic using
separate numerator and denominator fields for curvature, center coordinates,
and radius.
"""

from datetime import datetime
from fractions import Fraction
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.base import Base


class Circle(Base):
    """
    Circle in an Apollonian gasket with exact rational coordinates.

    All geometric properties (curvature, center, radius) are stored as
    rational numbers using separate numerator/denominator integer fields
    to preserve exactness.

    Attributes:
        id: Primary key
        gasket_id: Foreign key to parent gasket
        generation: Recursion depth (0 for initial circles)
        curvature_num, curvature_denom: Curvature as rational (k = num/denom)
        center_x_num, center_x_denom: Center X coordinate as rational
        center_y_num, center_y_denom: Center Y coordinate as rational
        radius_num, radius_denom: Radius as rational (r = num/denom)
        parent_ids: JSON string of parent circle IDs (e.g., '[1, 2, 3]')
        tangent_ids: JSON string of tangent circle IDs (e.g., '[4, 5, 6]')
        created_at: Timestamp when circle was computed
        gasket: Relationship back to parent Gasket

    Hybrid Properties:
        curvature: Returns Fraction object from curvature_num/curvature_denom

    Reference:
        .DESIGN_SPEC.md section 4.2 - Circles table schema
        .DESIGN_SPEC.md section 8.1 - Exact rational arithmetic rationale
    """

    __tablename__ = "circles"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to gasket
    gasket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("gaskets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Generation (recursion depth)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Curvature as rational number (k = curvature_num / curvature_denom)
    curvature_num: Mapped[int] = mapped_column(Integer, nullable=False)
    curvature_denom: Mapped[int] = mapped_column(Integer, nullable=False)

    # Center X coordinate as rational number
    center_x_num: Mapped[int] = mapped_column(Integer, nullable=False)
    center_x_denom: Mapped[int] = mapped_column(Integer, nullable=False)

    # Center Y coordinate as rational number
    center_y_num: Mapped[int] = mapped_column(Integer, nullable=False)
    center_y_denom: Mapped[int] = mapped_column(Integer, nullable=False)

    # Radius as rational number (r = radius_num / radius_denom)
    radius_num: Mapped[int] = mapped_column(Integer, nullable=False)
    radius_denom: Mapped[int] = mapped_column(Integer, nullable=False)

    # Graph structure (stored as JSON strings)
    parent_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tangent_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to gasket
    gasket: Mapped["Gasket"] = relationship("Gasket", back_populates="circles")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_circles_gasket_generation", "gasket_id", "generation"),
        Index("ix_circles_curvature", "curvature_num", "curvature_denom"),
    )

    @hybrid_property
    def curvature(self) -> Fraction:
        """
        Get curvature as a Fraction object.

        Returns:
            Fraction representing the circle's curvature (k)

        Example:
            >>> circle.curvature_num = 3
            >>> circle.curvature_denom = 2
            >>> circle.curvature
            Fraction(3, 2)
        """
        return Fraction(self.curvature_num, self.curvature_denom)

    @curvature.setter
    def curvature(self, value: Fraction) -> None:
        """
        Set curvature from a Fraction object.

        Args:
            value: Fraction representing the curvature

        Example:
            >>> circle.curvature = Fraction(3, 2)
            >>> circle.curvature_num
            3
            >>> circle.curvature_denom
            2
        """
        self.curvature_num = value.numerator
        self.curvature_denom = value.denominator

    @hybrid_property
    def center_x(self) -> Fraction:
        """Get center X coordinate as Fraction."""
        return Fraction(self.center_x_num, self.center_x_denom)

    @center_x.setter
    def center_x(self, value: Fraction) -> None:
        """Set center X coordinate from Fraction."""
        self.center_x_num = value.numerator
        self.center_x_denom = value.denominator

    @hybrid_property
    def center_y(self) -> Fraction:
        """Get center Y coordinate as Fraction."""
        return Fraction(self.center_y_num, self.center_y_denom)

    @center_y.setter
    def center_y(self, value: Fraction) -> None:
        """Set center Y coordinate from Fraction."""
        self.center_y_num = value.numerator
        self.center_y_denom = value.denominator

    @hybrid_property
    def radius(self) -> Fraction:
        """Get radius as Fraction."""
        return Fraction(self.radius_num, self.radius_denom)

    @radius.setter
    def radius(self, value: Fraction) -> None:
        """Set radius from Fraction."""
        self.radius_num = value.numerator
        self.radius_denom = value.denominator

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Circle(id={self.id}, gasket_id={self.gasket_id}, "
            f"k={self.curvature}, gen={self.generation})>"
        )


# Import Gasket to avoid circular import issues
from db.models.gasket import Gasket  # noqa: E402, F811
