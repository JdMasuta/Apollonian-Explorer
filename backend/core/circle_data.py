"""
CircleData class for Apollonian Gasket circles.

Reference: .DESIGN_SPEC.md section 8 (Algorithms)

This module provides a pure Python data structure for circles
before they are persisted to the database. It includes methods
for serialization and hashing for deduplication.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple, Dict

from core.circle_math import circle_hash, curvature_to_radius, fraction_to_tuple

# Type alias for complex numbers represented as Fraction tuples
ComplexFraction = Tuple[Fraction, Fraction]  # (real, imag)


@dataclass
class CircleData:
    """
    Data class representing a circle in an Apollonian gasket.

    Attributes:
        curvature: Circle curvature (k). Curvature = 1/radius.
        center: Circle center as complex number (real, imag) in Fractions.
        generation: Recursion depth (0 for initial circles).
        parent_ids: List of database IDs of parent circles (circles this was generated from).
        id: Database ID (None until persisted).
        tangent_ids: List of database IDs of circles tangent to this one.
    """

    curvature: Fraction
    center: ComplexFraction
    generation: int
    parent_ids: List[int] = field(default_factory=list)
    id: Optional[int] = None
    tangent_ids: List[int] = field(default_factory=list)

    def radius(self) -> Fraction:
        """
        Calculate circle radius.

        Returns:
            Radius as Fraction (r = 1/k)

        Raises:
            ZeroDivisionError: If curvature is zero
        """
        return curvature_to_radius(self.curvature)

    def hash_key(self) -> str:
        """
        Generate unique hash for this circle.

        Used for deduplication during gasket generation.
        Two circles with the same curvature and center will have
        the same hash.

        Returns:
            32-character MD5 hex hash
        """
        center_real, center_imag = self.center
        return circle_hash(self.curvature, center_real, center_imag)

    def to_dict(self) -> Dict:
        """
        Serialize circle to dictionary.

        Returns:
            Dictionary with string representations of all fields.
            Fractions are serialized as "numerator/denominator".

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
        center_real, center_imag = self.center
        radius = self.radius()

        return {
            "id": self.id,
            "curvature": f"{self.curvature.numerator}/{self.curvature.denominator}",
            "center": {
                "x": f"{center_real.numerator}/{center_real.denominator}",
                "y": f"{center_imag.numerator}/{center_imag.denominator}",
            },
            "radius": f"{radius.numerator}/{radius.denominator}",
            "generation": self.generation,
            "parent_ids": self.parent_ids.copy(),
            "tangent_ids": self.tangent_ids.copy(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        center_real, center_imag = self.center
        return (
            f"CircleData(id={self.id}, "
            f"k={self.curvature}, "
            f"center=({center_real}, {center_imag}), "
            f"gen={self.generation})"
        )


# Test if run directly
if __name__ == "__main__":
    # Create a circle at origin with curvature 1
    circle1 = CircleData(
        curvature=Fraction(1),
        center=(Fraction(0), Fraction(0)),
        generation=0,
        parent_ids=[],
    )

    print(f"Circle 1: {circle1}")
    print(f"  Radius: {circle1.radius()}")
    print(f"  Hash: {circle1.hash_key()}")
    print(f"  Dict: {circle1.to_dict()}")

    # Create another circle
    circle2 = CircleData(
        curvature=Fraction(3, 2),
        center=(Fraction(1, 4), Fraction(-1, 3)),
        generation=1,
        parent_ids=[1, 2, 3],
        id=5,
        tangent_ids=[1, 2, 3],
    )

    print(f"\nCircle 2: {circle2}")
    print(f"  Radius: {circle2.radius()}")
    print(f"  Hash: {circle2.hash_key()}")
    print(f"  Dict: {circle2.to_dict()}")

    # Test that identical circles have same hash
    circle3 = CircleData(
        curvature=Fraction(1),
        center=(Fraction(0), Fraction(0)),
        generation=0,
    )
    assert circle1.hash_key() == circle3.hash_key(), "Identical circles should have same hash"
    print("\n✓ Hash deduplication test passed")
