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
from typing import Optional, Union

import sympy as sp
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.base import Base
from core.exact_math import ExactNumber


class Circle(Base):
    """
    Circle in an Apollonian gasket with hybrid exact arithmetic support.

    Supports dual storage strategy for exact numbers (Phase 3-9):
    - INTEGER columns (num/denom pairs): Fast queries, lossy for irrationals
    - TEXT columns (tagged strings): Exact storage for int/Fraction/SymPy types

    Storage Columns:
        id: Primary key
        gasket_id: Foreign key to parent gasket
        generation: Recursion depth (0 for initial circles)

        # INTEGER columns (backward compatible, fast queries)
        curvature_num, curvature_denom: Curvature as num/denom pair
        center_x_num, center_x_denom: Center X as num/denom pair
        center_y_num, center_y_denom: Center Y as num/denom pair
        radius_num, radius_denom: Radius as num/denom pair

        # TEXT columns (exact storage, supports int/Fraction/SymPy)
        curvature_exact: Tagged string (e.g., "int:6", "frac:3/2", "sym:sqrt(2)")
        center_x_exact: Tagged string for X coordinate
        center_y_exact: Tagged string for Y coordinate
        radius_exact: Tagged string for radius

        parent_ids: JSON string of parent circle IDs (e.g., '[1, 2, 3]')
        tangent_ids: JSON string of tangent circle IDs (e.g., '[4, 5, 6]')
        created_at: Timestamp when circle was computed
        gasket: Relationship back to parent Gasket

    Hybrid Properties (Dual-Mode Access):
        # Legacy mode (Fraction only, from INTEGER columns)
        curvature: Returns Fraction from curvature_num/curvature_denom
        center_x: Returns Fraction from center_x_num/center_x_denom
        center_y: Returns Fraction from center_y_num/center_y_denom
        radius: Returns Fraction from radius_num/radius_denom

        # Exact mode (ExactNumber types, from TEXT columns - Phase 9)
        curvature_exact_value: Returns int, Fraction, or SymPy Expr
        center_x_exact_value: Returns int, Fraction, or SymPy Expr
        center_y_exact_value: Returns int, Fraction, or SymPy Expr
        radius_exact_value: Returns int, Fraction, or SymPy Expr

    Backward Compatibility:
        Old code using `circle.curvature` continues to work (returns Fraction).
        New code using `circle.curvature_exact_value` gets exact ExactNumber types.

    Example Usage:
        # Legacy access (always returns Fraction)
        >>> circle.curvature
        Fraction(3, 2)

        # Exact access (returns int, Fraction, or SymPy)
        >>> circle.curvature_exact = "sym:sqrt(2)"
        >>> circle.curvature_exact_value
        sqrt(2)  # SymPy expression

        # Fallback behavior (no exact value stored)
        >>> circle.curvature_exact = None
        >>> circle.curvature_exact_value
        Fraction(3, 2)  # Falls back to INTEGER columns

    Reference:
        .DESIGN_SPEC.md section 4.2 - Circles table schema
        .DESIGN_SPEC.md section 8.4 - Hybrid exact arithmetic system
        Phase 3: Database migration (TEXT columns)
        Phase 9: Circle model update (hybrid properties)
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

    # Exact storage (TEXT columns for ExactNumber types - Phase 3)
    # Tagged format: "int:6", "frac:3/2", "sym:sqrt(2)"
    curvature_exact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    center_x_exact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    center_y_exact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    radius_exact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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

    @staticmethod
    def parse_exact(exact_str: str) -> ExactNumber:
        """
        Parse tagged exact string to ExactNumber (int, Fraction, or SymPy Expr).

        Parses the tagged string format used in TEXT exact columns:
        - "int:6" → int(6)
        - "frac:3/2" → Fraction(3, 2)
        - "sym:sqrt(2)" → sp.sympify("sqrt(2)")

        Args:
            exact_str: Tagged string in format "type:value"

        Returns:
            ExactNumber (int, Fraction, or SymPy Expr)

        Raises:
            ValueError: If string format is unknown or invalid

        Example:
            >>> Circle.parse_exact("int:6")
            6
            >>> Circle.parse_exact("frac:3/2")
            Fraction(3, 2)
            >>> Circle.parse_exact("sym:sqrt(2)")
            sqrt(2)

        Reference:
            .DESIGN_SPEC.md section 8.4 - Hybrid exact arithmetic system
        """
        if not exact_str:
            raise ValueError("Cannot parse empty exact string")

        if exact_str.startswith("int:"):
            return int(exact_str[4:])
        elif exact_str.startswith("frac:"):
            parts = exact_str[5:].split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid fraction format: {exact_str}")
            return Fraction(int(parts[0]), int(parts[1]))
        elif exact_str.startswith("sym:"):
            return sp.sympify(exact_str[4:])
        else:
            raise ValueError(f"Unknown exact format: {exact_str}")

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

    # Exact value hybrid properties (Phase 9)
    # These provide access to ExactNumber types (int/Fraction/SymPy) from TEXT columns

    @hybrid_property
    def curvature_exact_value(self) -> ExactNumber:
        """
        Get curvature as ExactNumber (int, Fraction, or SymPy Expr).

        Returns exact value from TEXT exact column if available,
        otherwise falls back to INTEGER columns as Fraction.

        Returns:
            ExactNumber - int, Fraction, or SymPy Expr

        Example:
            >>> circle.curvature_exact = "sym:sqrt(2)"
            >>> circle.curvature_exact_value
            sqrt(2)  # SymPy expression
            >>> circle.curvature_exact = "int:6"
            >>> circle.curvature_exact_value
            6  # Python int

        Reference:
            .DESIGN_SPEC.md section 8.4 - Hybrid exact arithmetic
        """
        if self.curvature_exact:
            return self.parse_exact(self.curvature_exact)
        # Fallback to INTEGER columns
        return Fraction(self.curvature_num, self.curvature_denom)

    @hybrid_property
    def center_x_exact_value(self) -> ExactNumber:
        """
        Get center X coordinate as ExactNumber (int, Fraction, or SymPy Expr).

        Returns:
            ExactNumber from TEXT exact column, or Fraction from INTEGER columns

        Example:
            >>> circle.center_x_exact = "frac:7/6"
            >>> circle.center_x_exact_value
            Fraction(7, 6)
        """
        if self.center_x_exact:
            return self.parse_exact(self.center_x_exact)
        return Fraction(self.center_x_num, self.center_x_denom)

    @hybrid_property
    def center_y_exact_value(self) -> ExactNumber:
        """
        Get center Y coordinate as ExactNumber (int, Fraction, or SymPy Expr).

        Returns:
            ExactNumber from TEXT exact column, or Fraction from INTEGER columns

        Example:
            >>> circle.center_y_exact = "sym:2*sqrt(2)/3"
            >>> circle.center_y_exact_value
            2*sqrt(2)/3  # SymPy expression
        """
        if self.center_y_exact:
            return self.parse_exact(self.center_y_exact)
        return Fraction(self.center_y_num, self.center_y_denom)

    @hybrid_property
    def radius_exact_value(self) -> ExactNumber:
        """
        Get radius as ExactNumber (int, Fraction, or SymPy Expr).

        Returns:
            ExactNumber from TEXT exact column, or Fraction from INTEGER columns

        Example:
            >>> circle.radius_exact = "int:1"
            >>> circle.radius_exact_value
            1
        """
        if self.radius_exact:
            return self.parse_exact(self.radius_exact)
        return Fraction(self.radius_num, self.radius_denom)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Circle(id={self.id}, gasket_id={self.gasket_id}, "
            f"k={self.curvature}, gen={self.generation})>"
        )


# Import Gasket to avoid circular import issues
from db.models.gasket import Gasket  # noqa: E402, F811
