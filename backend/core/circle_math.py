"""
Circle mathematics utilities for Apollonian Gasket.

Reference: .DESIGN_SPEC.md section 8 (Algorithms)

This module provides helper functions for:
- Curvature-radius conversion
- Hash generation for circle deduplication
- Fraction serialization/deserialization
"""

import hashlib
from fractions import Fraction
from typing import Tuple


def curvature_to_radius(curvature: Fraction) -> Fraction:
    """
    Convert curvature to radius.

    For a circle, radius r = 1 / curvature k.

    Args:
        curvature: Circle curvature (k)

    Returns:
        Circle radius (r = 1/k)

    Raises:
        ZeroDivisionError: If curvature is zero (infinite radius)

    Example:
        >>> curvature_to_radius(Fraction(2))
        Fraction(1, 2)
    """
    if curvature == 0:
        raise ZeroDivisionError("Cannot compute radius for zero curvature (infinite radius)")

    return Fraction(1, 1) / curvature


def circle_hash(curvature: Fraction, center_real: Fraction, center_imag: Fraction) -> str:
    """
    Generate unique hash for a circle for deduplication.

    Uses MD5 hash of canonical string representation:
    "curvature_num/curvature_denom_real_num/real_denom_imag_num/imag_denom"

    Args:
        curvature: Circle curvature
        center_real: Real part of center (as Fraction)
        center_imag: Imaginary part of center (as Fraction)

    Returns:
        32-character hex MD5 hash

    Example:
        >>> circle_hash(Fraction(1), Fraction(0), Fraction(0))
        'd751713988987e9331980363e24189ce'
    """
    # Create canonical string representation
    key = f"{curvature.numerator}/{curvature.denominator}_{center_real.numerator}/{center_real.denominator}_{center_imag.numerator}/{center_imag.denominator}"

    # Generate MD5 hash
    return hashlib.md5(key.encode()).hexdigest()


def fraction_to_tuple(f: Fraction) -> Tuple[int, int]:
    """
    Extract numerator and denominator from Fraction.

    Args:
        f: Fraction to decompose

    Returns:
        Tuple of (numerator, denominator)

    Example:
        >>> fraction_to_tuple(Fraction(3, 4))
        (3, 4)
    """
    return (f.numerator, f.denominator)


def tuple_to_fraction(num: int, denom: int) -> Fraction:
    """
    Reconstruct Fraction from numerator and denominator.

    Args:
        num: Numerator
        denom: Denominator

    Returns:
        Fraction object

    Raises:
        ZeroDivisionError: If denominator is zero

    Example:
        >>> tuple_to_fraction(3, 4)
        Fraction(3, 4)
    """
    return Fraction(num, denom)


# Test the functions if run directly
if __name__ == "__main__":
    # Test curvature_to_radius
    k = Fraction(2)
    r = curvature_to_radius(k)
    print(f"Curvature {k} → Radius {r}")

    # Test circle_hash
    hash_val = circle_hash(Fraction(1), Fraction(0), Fraction(0))
    print(f"Hash for (1, 0, 0): {hash_val}")

    # Test fraction conversion
    f = Fraction(3, 4)
    num, denom = fraction_to_tuple(f)
    f_reconstructed = tuple_to_fraction(num, denom)
    print(f"Fraction {f} → ({num}, {denom}) → {f_reconstructed}")

    assert f == f_reconstructed, "Round-trip conversion failed"
    print("All manual tests passed!")
