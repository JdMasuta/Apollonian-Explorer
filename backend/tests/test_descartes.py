"""
Unit tests for Descartes Circle Theorem implementation (hybrid exact arithmetic).

Reference: .DESIGN_SPEC.md section 8.1 (Descartes Circle Theorem)
Reference: .DESIGN_SPEC.md section 8.4 (Hybrid Exact Arithmetic System)

Tests cover:
- Complex number arithmetic helpers (core.exact_math smart_complex_*)
- Curvature calculations using Descartes theorem
- Center calculations using complex Descartes theorem
- Edge cases and numerical stability

Note: the hybrid arithmetic system returns int for integer results, Fraction
for rational results, and SymPy Expr for irrational results. Tests therefore
assert exact *values* (int == Fraction comparisons are valid in Python) and
use is_exact() for type checks instead of pinning a single numeric type.
"""

import math
from fractions import Fraction

import sympy as sp

from core.descartes import (
    descartes_curvature,
    descartes_center,
    descartes_solve,
)
from core.exact_math import smart_complex_multiply, smart_complex_sqrt


def is_exact(value) -> bool:
    """True if value is one of the hybrid exact number types."""
    return isinstance(value, (int, Fraction, sp.Expr))


class TestComplexArithmetic:
    """Tests for hybrid complex number helpers in core.exact_math."""

    def test_complex_multiply_simple(self):
        """(2+3i) * (4+5i) = -7+22i."""
        result = smart_complex_multiply((2, 3), (4, 5))

        assert result[0] == -7, f"Real part should be -7, got {result[0]}"
        assert result[1] == 22, f"Imag part should be 22, got {result[1]}"

    def test_complex_multiply_real_only(self):
        """(3+0i) * (4+0i) = 12+0i."""
        result = smart_complex_multiply((3, 0), (4, 0))

        assert result[0] == 12
        assert result[1] == 0

    def test_complex_multiply_imaginary_only(self):
        """(0+2i) * (0+3i) = -6+0i (since i² = -1)."""
        result = smart_complex_multiply((0, 2), (0, 3))

        assert result[0] == -6
        assert result[1] == 0

    def test_complex_multiply_rational(self):
        """(1/2 + 1/3 i) * (1/4 + 1/5 i) = (1/8 - 1/15) + (1/10 + 1/12)i."""
        result = smart_complex_multiply(
            (Fraction(1, 2), Fraction(1, 3)), (Fraction(1, 4), Fraction(1, 5))
        )

        assert result[0] == Fraction(1, 8) - Fraction(1, 15)
        assert result[1] == Fraction(1, 10) + Fraction(1, 12)

    def test_complex_sqrt_real_positive(self):
        """√(4+0i) = 2 exactly."""
        result = smart_complex_sqrt((4, 0))

        assert result[0] == 2
        assert result[1] == 0

    def test_complex_sqrt_imaginary(self):
        """√(4i) = √2 + √2·i (verified numerically)."""
        result = smart_complex_sqrt((0, 4))

        sqrt_2 = math.sqrt(2)
        assert abs(float(result[0]) - sqrt_2) < 1e-9
        assert abs(float(result[1]) - sqrt_2) < 1e-9

    def test_complex_sqrt_general(self):
        """√(3+4i) = 2+i exactly: verify by squaring."""
        result = smart_complex_sqrt((3, 4))
        squared = smart_complex_multiply(result, result)

        assert abs(float(squared[0]) - 3.0) < 1e-9
        assert abs(float(squared[1]) - 4.0) < 1e-9


class TestDescartesCircleTheorem:
    """Tests for Descartes Circle Theorem implementation.

    Reference: .DESIGN_SPEC.md section 8.1
    """

    def test_degenerate_discriminant(self):
        """
        Test (-1, 2, 2): discriminant k₁k₂ + k₂k₃ + k₃k₁ = -2 + 4 - 2 = 0,
        so both curvature solutions coincide at k₄ = 3. (The two bend-3
        circles of the standard gasket come from the two *center* branches.)
        """
        k4_plus, k4_minus = descartes_curvature(-1, 2, 2)

        assert k4_plus == 3, f"k4_plus should be 3, got {k4_plus}"
        assert k4_minus == 3, f"k4_minus should be 3, got {k4_minus}"

    def test_known_configuration(self):
        """
        Test (-1, 2, 3) from the standard (-1, 2, 2, 3) gasket.

        discriminant = (-1)(2) + (2)(3) + (3)(-1) = 1, sum = 4
        k₄ = 4 ± 2√1 = {6, 2}
        """
        k4_plus, k4_minus = descartes_curvature(-1, 2, 3)

        assert k4_plus == 6, f"k4_plus should be 6, got {k4_plus}"
        assert k4_minus == 2, f"k4_minus should be 2, got {k4_minus}"

    def test_identical_curvatures(self):
        """
        Test (1, 1, 1): k₄ = 3 ± 2√3, an exact irrational (SymPy) result.
        """
        k4_plus, k4_minus = descartes_curvature(1, 1, 1)

        # Exact symbolic comparison
        assert sp.simplify(sp.sympify(k4_plus) - (3 + 2 * sp.sqrt(3))) == 0
        assert sp.simplify(sp.sympify(k4_minus) - (3 - 2 * sp.sqrt(3))) == 0

    def test_descartes_quadratic_identity(self):
        """
        Every solution must satisfy the Descartes quadratic form:
        2(k₁² + k₂² + k₃² + k₄²) = (k₁ + k₂ + k₃ + k₄)²
        """
        for k1, k2, k3 in [(-1, 2, 3), (-1, 2, 2), (2, 3, 6), (-11, 21, 24)]:
            for k4 in descartes_curvature(k1, k2, k3):
                lhs = 2 * (k1**2 + k2**2 + k3**2 + k4**2)
                rhs = (k1 + k2 + k3 + k4) ** 2
                assert sp.simplify(sp.sympify(lhs) - sp.sympify(rhs)) == 0, (
                    f"Quadratic identity failed for ({k1},{k2},{k3}) -> {k4}"
                )

    def test_center_calculation_standard_gasket(self):
        """
        Standard gasket placement: bounding circle b=-1 at origin, two b=2
        circles at (±1/2, 0). The bend-3 circles sit at (0, ±2/3).
        """
        k1, k2, k3 = -1, 2, 2
        c1 = (0, 0)
        c2 = (Fraction(1, 2), 0)
        c3 = (Fraction(-1, 2), 0)

        k4_plus, _ = descartes_curvature(k1, k2, k3)
        assert k4_plus == 3

        center_plus = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=1)
        center_minus = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=-1)

        ys = sorted(float(c[1]) for c in (center_plus, center_minus))
        for c in (center_plus, center_minus):
            assert float(c[0]) == 0.0
        assert abs(ys[0] + 2 / 3) < 1e-12
        assert abs(ys[1] - 2 / 3) < 1e-12

    def test_center_with_negative_curvature(self):
        """
        Center calculation with an enclosing circle (negative curvature)
        returns exact, finite coordinates.
        """
        c1, k1 = (0, 0), Fraction(-1, 2)
        c2, k2 = (-1, 0), 1
        c3, k3 = (1, 0), 1

        k4_plus, _ = descartes_curvature(k1, k2, k3)
        center = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=1)

        assert is_exact(center[0]) and is_exact(center[1])
        assert not math.isnan(float(center[0]))
        assert not math.isnan(float(center[1]))
        assert abs(float(center[0])) < 100
        assert abs(float(center[1])) < 100

    def test_negative_curvature_enclosing(self):
        """Both solutions for (-1, 2, 3) are positive (internal circles)."""
        k4_plus, k4_minus = descartes_curvature(-1, 2, 3)

        assert k4_plus > 0
        assert k4_minus > 0

    def test_large_curvatures_stability(self):
        """Large curvatures produce exact results without overflow."""
        k4_plus, k4_minus = descartes_curvature(1000, 1001, 1002)

        assert is_exact(k4_plus)
        assert is_exact(k4_minus)
        # k₄ = 3003 ± 2√3006002; both finite
        assert abs(float(k4_plus)) < 10**7
        assert abs(float(k4_minus)) < 10**7

    def test_descartes_solve_integration(self):
        """descartes_solve combines curvature and center calculations."""
        circle1 = (-1, (0, 0))  # Enclosing
        circle2 = (2, (Fraction(1, 2), 0))
        circle3 = (2, (Fraction(-1, 2), 0))

        circle_plus, circle_minus = descartes_solve(circle1, circle2, circle3)

        k4_plus, center_plus = circle_plus
        k4_minus, center_minus = circle_minus

        assert k4_plus == 3
        assert k4_minus == 3
        for center in (center_plus, center_minus):
            assert isinstance(center, tuple) and len(center) == 2
            assert is_exact(center[0]) and is_exact(center[1])
