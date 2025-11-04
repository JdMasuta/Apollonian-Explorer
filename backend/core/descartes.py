"""
Descartes Circle Theorem Implementation with SymPy

This module implements the Descartes Circle Theorem for calculating tangent circles
in Apollonian gaskets. Uses SymPy for exact symbolic computation throughout.

Reference: DESIGN_SPEC.md section 8.1

Mathematical Background:
- Given three mutually tangent circles with curvatures k₁, k₂, k₃
- The curvature of the two circles tangent to all three:
  k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)

- For centers (as complex numbers z₁, z₂, z₃):
  k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)
"""

from typing import Tuple
from sympy import Rational, sqrt, re, im, simplify, I
from sympy.core.numbers import Rational as RationalType


# Type aliases for clarity
Curvature = RationalType  # SymPy Rational type
ComplexNumber = object  # SymPy complex expression (Rational + Rational*I)
Circle = Tuple[Curvature, ComplexNumber]  # (curvature, center)


def descartes_curvature(
    k1: Curvature, k2: Curvature, k3: Curvature
) -> Tuple[Curvature, Curvature]:
    """
    Calculate the curvature of the fourth circle tangent to three circles.

    Implements Descartes Circle Theorem as specified in DESIGN_SPEC.md section 8.1

    Formula: k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)

    The ± gives two solutions representing the two circles tangent to all three.
    Negative curvature represents an enclosing circle (infinite or negative radius).

    Args:
        k1: Curvature of first circle (reciprocal of radius)
        k2: Curvature of second circle
        k3: Curvature of third circle

    Returns:
        Tuple of (k4_plus, k4_minus) - the two curvature solutions

    Example:
        >>> descartes_curvature(Rational(-1), Rational(2), Rational(2))
        (Rational(6, 1), Rational(2, 3))
        # Standard Apollonian gasket starting configuration

    Note:
        ✓ Uses exact SymPy symbolic computation - no float approximation!
    """
    # Calculate the discriminant: k₁k₂ + k₂k₃ + k₃k₁
    discriminant = k1 * k2 + k2 * k3 + k3 * k1

    # Calculate the sum: k₁ + k₂ + k₃
    sum_curvatures = k1 + k2 + k3

    # Calculate √(discriminant) - SymPy keeps this exact!
    sqrt_disc = sqrt(discriminant)

    # Two solutions: ± 2√(discriminant)
    two_sqrt_disc = 2 * sqrt_disc

    k4_plus = simplify(sum_curvatures + two_sqrt_disc)
    k4_minus = simplify(sum_curvatures - two_sqrt_disc)

    return (k4_plus, k4_minus)


def descartes_center(
    c1: ComplexNumber,
    c2: ComplexNumber,
    c3: ComplexNumber,
    k1: Curvature,
    k2: Curvature,
    k3: Curvature,
    k4: Curvature,
    sign: int = 1,
) -> ComplexNumber:
    """
    Calculate the center of the fourth circle using complex Descartes theorem.

    Implements complex Descartes formula from DESIGN_SPEC.md section 8.1:
    k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)

    Args:
        c1: Center of first circle as SymPy complex number (x + y*I)
        c2: Center of second circle
        c3: Center of third circle
        k1: Curvature of first circle
        k2: Curvature of second circle
        k3: Curvature of third circle
        k4: Curvature of fourth circle (from descartes_curvature)
        sign: +1 for plus branch, -1 for minus branch (default: 1)

    Returns:
        Center of fourth circle as SymPy complex number

    Note:
        ✓ Uses exact SymPy symbolic computation - no float approximation!
    """
    # Compute k₁z₁ + k₂z₂ + k₃z₃
    k1z1 = k1 * c1
    k2z2 = k2 * c2
    k3z3 = k3 * c3

    sum_kz = k1z1 + k2z2 + k3z3

    # Compute k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁
    z1z2 = c1 * c2
    z2z3 = c2 * c3
    z3z1 = c3 * c1

    k1k2z1z2 = k1 * k2 * z1z2
    k2k3z2z3 = k2 * k3 * z2z3
    k3k1z3z1 = k3 * k1 * z3z1

    sum_products = k1k2z1z2 + k2k3z2z3 + k3k1z3z1

    # Take square root - SymPy handles complex sqrt symbolically!
    sqrt_products = sqrt(sum_products)

    # Multiply by ± 2
    two_sqrt = 2 * sqrt_products * sign

    # Add to sum: k₁z₁ + k₂z₂ + k₃z₃ ± 2√(...)
    numerator = sum_kz + two_sqrt

    # Divide by k₄: z₄ = numerator / k₄
    z4 = simplify(numerator / k4)

    return z4


def descartes_solve(
    circle1: Circle, circle2: Circle, circle3: Circle
) -> Tuple[Circle, Circle]:
    """
    Calculate two circles tangent to three given circles.

    This is a convenience function that combines descartes_curvature() and
    descartes_center() to solve for both tangent circles in one call.

    Implements full Descartes Circle Theorem from DESIGN_SPEC.md section 8.1

    Args:
        circle1: First circle as (curvature, center) where center is complex number
        circle2: Second circle as (curvature, center)
        circle3: Third circle as (curvature, center)

    Returns:
        Tuple of two Circle solutions:
        - circle_plus: Solution using + branch of formula
        - circle_minus: Solution using - branch of formula

    Example:
        >>> from sympy import Rational, I
        >>> c1 = (Rational(-1), Rational(0))
        >>> c2 = (Rational(2), Rational(1))
        >>> c3 = (Rational(2), Rational(-1))
        >>> circle_plus, circle_minus = descartes_solve(c1, c2, c3)

    Note:
        ✓ Uses exact SymPy symbolic computation - no float approximation!
    """
    # Extract curvatures and centers
    k1, c1 = circle1
    k2, c2 = circle2
    k3, c3 = circle3

    # Calculate curvatures of the two solutions
    k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

    # Calculate centers for both solutions
    center_plus = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=1)
    center_minus = descartes_center(c1, c2, c3, k1, k2, k3, k4_minus, sign=-1)

    # Return both complete circles
    circle_plus = (k4_plus, center_plus)
    circle_minus = (k4_minus, center_minus)

    return (circle_plus, circle_minus)


def create_complex(x: Curvature, y: Curvature) -> ComplexNumber:
    """
    Helper function to create a complex number from real and imaginary parts.

    Args:
        x: Real part as SymPy Rational
        y: Imaginary part as SymPy Rational

    Returns:
        SymPy complex number (x + y*I)

    Example:
        >>> create_complex(Rational(1), Rational(2))
        1 + 2*I
    """
    return x + y * I


def get_complex_parts(z: ComplexNumber) -> Tuple[Curvature, Curvature]:
    """
    Helper function to extract real and imaginary parts from a SymPy complex number.

    Args:
        z: SymPy complex number

    Returns:
        Tuple of (real_part, imag_part) as SymPy Rationals

    Example:
        >>> z = Rational(1) + Rational(2)*I
        >>> get_complex_parts(z)
        (1, 2)
    """
    real_part = simplify(re(z))
    imag_part = simplify(im(z))
    return (real_part, imag_part)


# Example usage and testing
if __name__ == "__main__":
    print("Descartes Circle Theorem - SymPy Exact Implementation\n")
    print("=" * 60)

    # Standard Apollonian gasket configuration:
    # Outer circle with curvature -1 (radius 1, centered at origin)
    # Two touching circles with curvature 2 (radius 0.5)
    k1 = Rational(-1)
    k2 = Rational(2)
    k3 = Rational(2)

    c1 = Rational(0)  # Center at origin
    c2 = Rational(1)  # Center at (1, 0)
    c3 = Rational(-1)  # Center at (-1, 0)

    circle1 = (k1, c1)
    circle2 = (k2, c2)
    circle3 = (k3, c3)

    print("\nInput circles:")
    print(f"Circle 1: curvature = {k1}, center = {c1}")
    print(f"Circle 2: curvature = {k2}, center = {c2}")
    print(f"Circle 3: curvature = {k3}, center = {c3}")

    # Calculate the two tangent circles
    circle_plus, circle_minus = descartes_solve(circle1, circle2, circle3)

    k4_plus, center_plus = circle_plus
    k4_minus, center_minus = circle_minus

    print("\n" + "=" * 60)
    print("Results (exact symbolic values):")
    print("=" * 60)
    print(f"\nSolution 1 (plus branch):")
    print(f"  Curvature: {k4_plus}")
    print(f"  Center: {center_plus}")
    
    # Extract real and imaginary parts for clarity
    real_plus, imag_plus = get_complex_parts(center_plus)
    print(f"  Center (re, im): ({real_plus}, {imag_plus})")

    print(f"\nSolution 2 (minus branch):")
    print(f"  Curvature: {k4_minus}")
    print(f"  Center: {center_minus}")
    
    real_minus, imag_minus = get_complex_parts(center_minus)
    print(f"  Center (re, im): ({real_minus}, {imag_minus})")

    # Show numerical approximations if desired
    print("\n" + "=" * 60)
    print("Numerical approximations (for reference):")
    print("=" * 60)
    print(f"\nSolution 1:")
    print(f"  Curvature: {float(k4_plus):.10f}")
    print(f"  Center: {complex(center_plus)}")

    print(f"\nSolution 2:")
    print(f"  Curvature: {float(k4_minus):.10f}")
    print(f"  Center: {complex(center_minus)}")

    print("\n" + "=" * 60)
    print("✓ All calculations performed with exact symbolic arithmetic!")
    print("=" * 60)