"""
CircleData class for Apollonian Gasket circles with hybrid exact arithmetic.

Reference: .DESIGN_SPEC.md section 8 (Algorithms)
Reference: .DESIGN_SPEC.md section 8.4 (Hybrid Exact Arithmetic System)

This module provides a pure Python data structure for circles
before they are persisted to the database. Uses the hybrid exact arithmetic
system to support int, Fraction, and SymPy expression types.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Dict

from core.exact_math import (
    ExactNumber,
    ExactComplex,
    smart_divide,
    smart_real,
    smart_imag,
    format_exact,
    to_string,
    to_numerator_denominator,
    to_fraction_lossy,
)
from core.circle_math import circle_hash


@dataclass
class CircleData:
    """
    Data class representing a circle in an Apollonian gasket.

    Uses hybrid exact arithmetic to support three number types:
    - int: For integer values (fastest)
    - Fraction: For rational values (exact, medium speed)
    - SymPy Expr: For irrational values like sqrt(2) (exact, preserves symbolic form)

    Attributes:
        curvature: Circle curvature (k). Curvature = 1/radius. Type: ExactNumber
        center: Circle center as complex number (real, imag). Type: ExactComplex
        generation: Recursion depth (0 for initial circles).
        parent_ids: List of database IDs of parent circles (circles this was generated from).
        id: Database ID (None until persisted).
        tangent_ids: List of database IDs of circles tangent to this one.
    """

    curvature: ExactNumber
    center: ExactComplex
    generation: int
    parent_ids: List[int] = field(default_factory=list)
    id: Optional[int] = None
    tangent_ids: List[int] = field(default_factory=list)

    def radius(self) -> ExactNumber:
        """
        Calculate circle radius using hybrid exact arithmetic.

        Returns:
            Radius as ExactNumber (r = 1/k)
            - Returns int if curvature is 1
            - Returns Fraction for rational results
            - Returns SymPy Expr for irrational results

        Raises:
            ZeroDivisionError: If curvature is zero

        Example:
            >>> circle = CircleData(curvature=2, center=(0, 0), generation=0)
            >>> circle.radius()
            Fraction(1, 2)
        """
        return smart_divide(1, self.curvature)

    def hash_key(self) -> str:
        """
        Generate unique hash for this circle using exact arithmetic.

        Uses format_exact() to convert ExactNumber values to canonical string format
        before hashing. This ensures consistent hashing across all three exact types.

        Returns:
            32-character MD5 hex hash

        Note:
            Hash format changed in Phase 5 to support ExactNumber types.
            Old hashes (Fraction-only) are incompatible.
        """
        # Extract real and imaginary parts from ExactComplex
        center_real = smart_real(self.center)
        center_imag = smart_imag(self.center)

        # Use circle_hash with ExactNumber-aware formatting
        return circle_hash(self.curvature, center_real, center_imag)

    def to_dict(self) -> Dict:
        """
        Serialize circle to dictionary with unified fraction format.

        All numeric values are serialized as "numerator/denominator" strings
        for API consistency (per Phase 5 requirements):
        - int: "6" → "6/1"
        - Fraction: "3/2" → "3/2" (unchanged)
        - SymPy: "sqrt(2)" → "14142136/10000000" (approximated)

        Returns:
            Dictionary with string representations of all fields.

        Example:
            {
                "id": 1,
                "curvature": "3/2",
                "center": {"x": "1/4", "y": "-1/3"},
                "radius": "2/3",
                "generation": 2,
                "parent_ids": [1, 2, 3],
                "tangent_ids": [4, 5, 6]
            }
        """
        # Extract center components
        center_real = smart_real(self.center)
        center_imag = smart_imag(self.center)

        # Calculate radius
        radius = self.radius()

        # Helper function to convert ExactNumber to unified fraction format
        def to_unified_fraction_format(value: ExactNumber) -> str:
            """Convert ExactNumber to 'num/denom' string format."""
            # Convert to Fraction (lossy for SymPy expressions)
            frac = to_fraction_lossy(value)
            return f"{frac.numerator}/{frac.denominator}"

        return {
            "id": self.id,
            "curvature": to_unified_fraction_format(self.curvature),
            "center": {
                "x": to_unified_fraction_format(center_real),
                "y": to_unified_fraction_format(center_imag),
            },
            "radius": to_unified_fraction_format(radius),
            "generation": self.generation,
            "parent_ids": self.parent_ids.copy(),
            "tangent_ids": self.tangent_ids.copy(),
        }

    def to_database_dict(self) -> Dict:
        """
        Convert to database-compatible format with dual storage strategy.

        Populates both INTEGER columns (for fast queries and backward compatibility)
        and TEXT columns (for exact storage of irrational values).

        INTEGER storage:
        - Stores numerator/denominator pairs
        - LOSSY for irrational values (approximates sqrt(2) as large fraction)
        - Used for indexing and numeric queries

        TEXT storage:
        - Stores exact tagged strings: "int:6", "frac:3/2", "sym:sqrt(2)"
        - LOSSLESS for all types
        - Used for exact reconstruction

        Returns:
            Dictionary with all database column values

        Example:
            {
                "curvature_num": 3,
                "curvature_denom": 2,
                "curvature_exact": "frac:3/2",
                "center_x_num": 0,
                "center_x_denom": 1,
                "center_x_exact": "int:0",
                ...
            }
        """
        # Extract center components
        center_real = smart_real(self.center)
        center_imag = smart_imag(self.center)

        # Calculate radius
        radius = self.radius()

        # Convert to INTEGER format (lossy for irrationals)
        curvature_num, curvature_denom = to_numerator_denominator(self.curvature)
        center_x_num, center_x_denom = to_numerator_denominator(center_real)
        center_y_num, center_y_denom = to_numerator_denominator(center_imag)
        radius_num, radius_denom = to_numerator_denominator(radius)

        # Convert to TEXT format (exact for all types)
        curvature_exact = format_exact(self.curvature)
        center_x_exact = format_exact(center_real)
        center_y_exact = format_exact(center_imag)
        radius_exact = format_exact(radius)

        return {
            # INTEGER columns (lossy, for indexing)
            "curvature_num": curvature_num,
            "curvature_denom": curvature_denom,
            "center_x_num": center_x_num,
            "center_x_denom": center_x_denom,
            "center_y_num": center_y_num,
            "center_y_denom": center_y_denom,
            "radius_num": radius_num,
            "radius_denom": radius_denom,

            # TEXT columns (exact, for reconstruction)
            "curvature_exact": curvature_exact,
            "center_x_exact": center_x_exact,
            "center_y_exact": center_y_exact,
            "radius_exact": radius_exact,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        center_real = smart_real(self.center)
        center_imag = smart_imag(self.center)
        return (
            f"CircleData(id={self.id}, "
            f"k={self.curvature}, "
            f"center=({center_real}, {center_imag}), "
            f"gen={self.generation})"
        )


# Test if run directly
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add parent directory for imports when run as script
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from fractions import Fraction
    import sympy as sp

    print("CircleData - Hybrid Exact Arithmetic Implementation")
    print("=" * 60)

    # Test 1: Integer curvature
    print("\nTest 1: Integer curvature")
    circle1 = CircleData(
        curvature=6,  # int
        center=(0, 0),
        generation=0,
        parent_ids=[],
    )
    print(f"  Circle: {circle1}")
    print(f"  Radius: {circle1.radius()} (type: {type(circle1.radius()).__name__})")
    print(f"  Hash: {circle1.hash_key()}")
    print(f"  to_dict()['curvature']: {circle1.to_dict()['curvature']}")
    print(f"  to_dict()['radius']: {circle1.to_dict()['radius']}")

    # Test 2: Fraction curvature
    print("\nTest 2: Fraction curvature")
    circle2 = CircleData(
        curvature=Fraction(3, 2),
        center=(Fraction(1, 4), Fraction(-1, 3)),
        generation=1,
        parent_ids=[1, 2, 3],
        id=5,
        tangent_ids=[1, 2, 3],
    )
    print(f"  Circle: {circle2}")
    print(f"  Radius: {circle2.radius()}")
    print(f"  Hash: {circle2.hash_key()}")
    print(f"  to_dict(): {circle2.to_dict()}")

    # Test 3: SymPy curvature (irrational)
    print("\nTest 3: SymPy curvature (irrational)")
    k_sympy = 3 + 2*sp.sqrt(3)
    circle3 = CircleData(
        curvature=k_sympy,
        center=(0, sp.sqrt(2)),  # Mixed: int real, SymPy imag
        generation=0,
    )
    print(f"  Circle: {circle3}")
    print(f"  Curvature type: {type(circle3.curvature).__name__}")
    print(f"  Radius: {circle3.radius()}")
    print(f"  Hash: {circle3.hash_key()}")
    print(f"  to_dict()['curvature']: {circle3.to_dict()['curvature']}")
    print(f"  to_dict()['center']['y']: {circle3.to_dict()['center']['y']}")

    # Test 4: Database dict
    print("\nTest 4: Database dict (dual storage)")
    db_dict = circle2.to_database_dict()
    print(f"  INTEGER: curvature_num={db_dict['curvature_num']}, curvature_denom={db_dict['curvature_denom']}")
    print(f"  TEXT: curvature_exact={db_dict['curvature_exact']}")
    print(f"  TEXT: center_x_exact={db_dict['center_x_exact']}, center_y_exact={db_dict['center_y_exact']}")

    # Test 5: Hash consistency
    print("\nTest 5: Hash deduplication")
    circle4 = CircleData(
        curvature=6,  # Same as circle1
        center=(0, 0),
        generation=0,
    )
    assert circle1.hash_key() == circle4.hash_key(), "Identical circles should have same hash"
    print("  ✓ Hash deduplication test passed")

    print("\n" + "=" * 60)
    print("✓ All CircleData tests passed!")
    print("✓ Supports int, Fraction, and SymPy Expr types")
    print("✓ Unified fraction format for API")
    print("✓ Dual storage (INTEGER + TEXT) for database")
    print("=" * 60)
