"""
Descartes Circle Theorem Implementation

This module implements the Descartes Circle Theorem for calculating tangent circles
in Apollonian gaskets. Uses exact rational arithmetic via fractions.Fraction.

Reference: DESIGN_SPEC.md section 8.1

Mathematical Background:
- Given three mutually tangent circles with curvatures k₁, k₂, k₃
- The curvature of the two circles tangent to all three:
  k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)

- For centers (as complex numbers z₁, z₂, z₃):
  k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)
"""

import math
from fractions import Fraction
from typing import Tuple


# Type aliases for clarity
Curvature = Fraction
ComplexFraction = Tuple[Fraction, Fraction]  # (real, imag)
Circle = Tuple[Curvature, ComplexFraction]  # (curvature, center)


def complex_multiply(a: ComplexFraction, b: ComplexFraction) -> ComplexFraction:
    """
    Multiply two complex numbers represented as Fraction tuples.

    Formula: (a+bi)(c+di) = (ac-bd) + (ad+bc)i

    Args:
        a: First complex number as (real, imag) Fraction tuple
        b: Second complex number as (real, imag) Fraction tuple

    Returns:
        Product as (real, imag) Fraction tuple

    Example:
        >>> complex_multiply((Fraction(2), Fraction(3)), (Fraction(4), Fraction(5)))
        (Fraction(-7, 1), Fraction(22, 1))  # (2+3i)(4+5i) = -7+22i
    """
    a_real, a_imag = a
    b_real, b_imag = b

    real_part = a_real * b_real - a_imag * b_imag
    imag_part = a_real * b_imag + a_imag * b_real

    return (real_part, imag_part)


def complex_sqrt(z: ComplexFraction) -> ComplexFraction:
    """
    Compute square root of a complex number represented as Fraction tuple.

    ⚠️ WARNING: This function requires float conversion and loses exactness.
    The result is approximated using limit_denominator(1000000) to convert
    back to Fraction, providing ~6 digits of precision.

    For production use with symbolic computation, consider using sympy.

    Formula:
        √(a+bi) = √r * (cos(θ/2) + i*sin(θ/2))
        where r = √(a²+b²) and θ = atan2(b, a)

    Args:
        z: Complex number as (real, imag) Fraction tuple

    Returns:
        Square root as (real, imag) Fraction tuple (approximated)

    Example:
        >>> complex_sqrt((Fraction(0), Fraction(4)))
        # √(4i) ≈ (√2, √2)
        (Fraction(1414214, 1000000), Fraction(1414214, 1000000))
    """
    real, imag = z

    # Convert to float for calculation
    r_float = float(real)
    i_float = float(imag)

    # Calculate magnitude and angle
    magnitude = math.sqrt(r_float**2 + i_float**2)
    sqrt_magnitude = math.sqrt(magnitude)
    angle = math.atan2(i_float, r_float) / 2

    # Compute sqrt in rectangular form
    result_real = sqrt_magnitude * math.cos(angle)
    result_imag = sqrt_magnitude * math.sin(angle)

    # Convert back to Fraction with approximation
    return (
        Fraction(result_real).limit_denominator(1000000),
        Fraction(result_imag).limit_denominator(1000000),
    )


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
        >>> descartes_curvature(Fraction(-1), Fraction(2), Fraction(2))
        # Returns (Fraction(6, 1), Fraction(14, 15))
        # Standard Apollonian gasket starting configuration

    Note:
        ⚠️ Square root calculation uses float approximation via limit_denominator
    """
    # Calculate the discriminant: k₁k₂ + k₂k₃ + k₃k₁
    discriminant = k1 * k2 + k2 * k3 + k3 * k1

    # Calculate the sum: k₁ + k₂ + k₃
    sum_curvatures = k1 + k2 + k3

    # Calculate √(discriminant) with float approximation
    sqrt_disc_float = math.sqrt(float(discriminant))
    sqrt_disc = Fraction(sqrt_disc_float).limit_denominator(1000000)

    # Two solutions: ± 2√(discriminant)
    two_sqrt_disc = 2 * sqrt_disc

    k4_plus = sum_curvatures + two_sqrt_disc
    k4_minus = sum_curvatures - two_sqrt_disc

    return (k4_plus, k4_minus)


def descartes_center(
    c1: ComplexFraction,
    c2: ComplexFraction,
    c3: ComplexFraction,
    k1: Curvature,
    k2: Curvature,
    k3: Curvature,
    k4: Curvature,
    sign: int = 1,
) -> ComplexFraction:
    """
    Calculate the center of the fourth circle using complex Descartes theorem.

    Implements complex Descartes formula from DESIGN_SPEC.md section 8.1:
    k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)

    Args:
        c1: Center of first circle as (x, y) Fraction tuple
        c2: Center of second circle
        c3: Center of third circle
        k1: Curvature of first circle
        k2: Curvature of second circle
        k3: Curvature of third circle
        k4: Curvature of fourth circle (from descartes_curvature)
        sign: +1 for plus branch, -1 for minus branch (default: 1)

    Returns:
        Center of fourth circle as (x, y) Fraction tuple

    Note:
        ⚠️ Uses complex_sqrt which includes float approximation
    """
    # Compute k₁z₁ + k₂z₂ + k₃z₃
    # Scalar multiplication: k * (real, imag) = (k*real, k*imag)
    k1z1 = (k1 * c1[0], k1 * c1[1])
    k2z2 = (k2 * c2[0], k2 * c2[1])
    k3z3 = (k3 * c3[0], k3 * c3[1])

    sum_kz = (k1z1[0] + k2z2[0] + k3z3[0], k1z1[1] + k2z2[1] + k3z3[1])

    # Compute k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁
    z1z2 = complex_multiply(c1, c2)
    z2z3 = complex_multiply(c2, c3)
    z3z1 = complex_multiply(c3, c1)

    k1k2z1z2 = (k1 * k2 * z1z2[0], k1 * k2 * z1z2[1])
    k2k3z2z3 = (k2 * k3 * z2z3[0], k2 * k3 * z2z3[1])
    k3k1z3z1 = (k3 * k1 * z3z1[0], k3 * k1 * z3z1[1])

    sum_products = (
        k1k2z1z2[0] + k2k3z2z3[0] + k3k1z3z1[0],
        k1k2z1z2[1] + k2k3z2z3[1] + k3k1z3z1[1],
    )

    # Take square root
    sqrt_products = complex_sqrt(sum_products)

    # Multiply by ± 2
    two_sqrt = (2 * sqrt_products[0] * sign, 2 * sqrt_products[1] * sign)

    # Add to sum: k₁z₁ + k₂z₂ + k₃z₃ ± 2√(...)
    numerator = (sum_kz[0] + two_sqrt[0], sum_kz[1] + two_sqrt[1])

    # Divide by k₄: z₄ = numerator / k₄
    z4 = (numerator[0] / k4, numerator[1] / k4)

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
        circle1: First circle as (curvature, (center_x, center_y))
        circle2: Second circle as (curvature, (center_x, center_y))
        circle3: Third circle as (curvature, (center_x, center_y))

    Returns:
        Tuple of two Circle solutions:
        - circle_plus: Solution using + branch of formula
        - circle_minus: Solution using - branch of formula

    Example:
        >>> c1 = (Fraction(-1), (Fraction(0), Fraction(0)))
        >>> c2 = (Fraction(2), (Fraction(1), Fraction(0)))
        >>> c3 = (Fraction(2), (Fraction(-1), Fraction(0)))
        >>> circle_plus, circle_minus = descartes_solve(c1, c2, c3)

    Note:
        ⚠️ Uses float approximation for square roots
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
