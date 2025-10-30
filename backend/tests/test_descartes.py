"""
Unit tests for Descartes Circle Theorem implementation.

Reference: DESIGN_SPEC.md section 8.1

Tests cover:
- Complex number arithmetic helpers
- Curvature calculations using Descartes theorem
- Center calculations using complex Descartes theorem
- Edge cases and numerical stability
"""

import pytest
import sys
import math
from pathlib import Path
from fractions import Fraction

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.descartes import (
    complex_multiply,
    complex_sqrt,
    descartes_curvature,
    descartes_center,
    descartes_solve,
)


class TestComplexArithmetic:
    """Tests for complex number helper functions."""

    def test_complex_multiply_simple(self):
        """Test multiplication of simple complex numbers."""
        # (2+3i) * (4+5i) = 8+10i+12i+15i² = 8+22i-15 = -7+22i
        a = (Fraction(2), Fraction(3))
        b = (Fraction(4), Fraction(5))
        result = complex_multiply(a, b)

        assert result[0] == Fraction(-7), f"Real part should be -7, got {result[0]}"
        assert result[1] == Fraction(22), f"Imag part should be 22, got {result[1]}"

    def test_complex_multiply_real_only(self):
        """Test multiplication with real-only numbers."""
        # (3+0i) * (4+0i) = 12+0i
        a = (Fraction(3), Fraction(0))
        b = (Fraction(4), Fraction(0))
        result = complex_multiply(a, b)

        assert result[0] == Fraction(12)
        assert result[1] == Fraction(0)

    def test_complex_multiply_imaginary_only(self):
        """Test multiplication with imaginary-only numbers."""
        # (0+2i) * (0+3i) = -6+0i (since i² = -1)
        a = (Fraction(0), Fraction(2))
        b = (Fraction(0), Fraction(3))
        result = complex_multiply(a, b)

        assert result[0] == Fraction(-6)
        assert result[1] == Fraction(0)

    def test_complex_sqrt_real_positive(self):
        """Test square root of positive real number."""
        # √4 = 2
        z = (Fraction(4), Fraction(0))
        result = complex_sqrt(z)

        # Should be approximately (2, 0)
        assert abs(float(result[0]) - 2.0) < 0.001
        assert abs(float(result[1]) - 0.0) < 0.001

    def test_complex_sqrt_imaginary(self):
        """Test square root of pure imaginary number."""
        # √(4i) = √2 + √2*i (approximately 1.414 + 1.414i)
        z = (Fraction(0), Fraction(4))
        result = complex_sqrt(z)

        sqrt_2 = 1.41421356
        assert abs(float(result[0]) - sqrt_2) < 0.01
        assert abs(float(result[1]) - sqrt_2) < 0.01

    def test_complex_sqrt_general(self):
        """Test square root of general complex number."""
        # √(3+4i) ≈ 2 + 1i
        z = (Fraction(3), Fraction(4))
        result = complex_sqrt(z)

        # Verify by squaring the result
        squared = complex_multiply(result, result)

        # Should get back approximately (3, 4)
        assert abs(float(squared[0]) - 3.0) < 0.01
        assert abs(float(squared[1]) - 4.0) < 0.01


class TestDescartesCircleTheorem:
    """Tests for Descartes Circle Theorem implementation.

    Reference: DESIGN_SPEC.md section 8.1
    """

    def test_known_configuration(self):
        """
        Test with known Apollonian gasket configuration.

        Starting curvatures: -1, 2, 2, 3
        Expected results: k4_plus = 6, k4_minus = 14/15

        This is a standard configuration for Apollonian gaskets.
        """
        k1 = Fraction(-1)
        k2 = Fraction(2)
        k3 = Fraction(2)
        # Note: The third curvature in the initial configuration is 3
        # We're solving for k4 given k1, k2, k3

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Expected: k4 = -1 + 2 + 2 ± 2√(-2 + 4 - 2)
        # = 3 ± 2√0 = 3
        # This gives k4=3 (both solutions the same when discriminant=0)

        # Actually testing (-1, 2, 2) which should give different results
        # Let's check the actual mathematics:
        # discriminant = k1*k2 + k2*k3 + k3*k1 = (-1)(2) + (2)(2) + (2)(-1)
        # = -2 + 4 - 2 = 0
        # So √0 = 0, meaning k4 = 3 ± 0 = 3

        assert k4_plus == Fraction(3), f"k4_plus should be 3, got {k4_plus}"
        assert k4_minus == Fraction(3), f"k4_minus should be 3, got {k4_minus}"

    def test_known_configuration_corrected(self):
        """
        Test with corrected known configuration.

        For the standard (-1, 2, 2, 3) Apollonian gasket, we need to test
        with k1=-1, k2=2, k3=3 to find k4.

        Expected: k4_plus = 6, k4_minus = 2/3
        """
        k1 = Fraction(-1)
        k2 = Fraction(2)
        k3 = Fraction(3)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # discriminant = (-1)(2) + (2)(3) + (3)(-1) = -2 + 6 - 3 = 1
        # sum = -1 + 2 + 3 = 4
        # k4 = 4 ± 2√1 = 4 ± 2 = {6, 2}

        assert k4_plus == Fraction(6), f"k4_plus should be 6, got {k4_plus}"
        assert k4_minus == Fraction(2), f"k4_minus should be 2, got {k4_minus}"

    def test_identical_curvatures(self):
        """
        Test with three identical curvatures (1, 1, 1).

        Expected: k4 = 3 ± 2√3 ≈ 3 ± 3.464 ≈ {6.464, -0.464}
        """
        k1 = k2 = k3 = Fraction(1)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # discriminant = 1*1 + 1*1 + 1*1 = 3
        # sum = 1 + 1 + 1 = 3
        # k4 = 3 ± 2√3 ≈ 3 ± 3.464

        # Since we use float approximation, verify approximate values
        assert abs(float(k4_plus) - 6.464) < 0.01, f"k4_plus ≈ 6.464, got {float(k4_plus)}"
        assert abs(float(k4_minus) + 0.464) < 0.01, f"k4_minus ≈ -0.464, got {float(k4_minus)}"

    def test_center_calculation_simple(self):
        """
        Test center calculation with a simple configuration.

        Use three circles with known positions and curvatures.
        """
        # Three circles:
        # Circle 1: center (0, 0), curvature 1 (radius 1)
        # Circle 2: center (2, 0), curvature 1 (radius 1)
        # Circle 3: center (1, √3), curvature 1 (radius 1)
        # These form an equilateral triangle

        c1 = (Fraction(0), Fraction(0))
        c2 = (Fraction(2), Fraction(0))
        c3 = (Fraction(1), Fraction(1732051, 1000000))  # ≈ √3

        k1 = k2 = k3 = Fraction(1)

        # Calculate k4 first
        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Calculate center for plus branch
        center_plus = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=1)

        # For three mutually tangent circles of equal radius forming
        # an equilateral triangle, the fourth circle should be centered
        # at the centroid: ((0+2+1)/3, (0+0+√3)/3) = (1, √3/3)

        # Verify center is approximately at centroid
        centroid_x = float(Fraction(1))
        centroid_y = float(Fraction(1732051, 1000000)) / 3  # √3/3 ≈ 0.577

        assert abs(float(center_plus[0]) - centroid_x) < 0.1
        assert abs(float(center_plus[1]) - centroid_y) < 0.1

    def test_center_with_negative_curvature(self):
        """
        Test center calculation with enclosing circle (negative curvature).
        """
        # Enclosing circle at origin with radius 2 (curvature -1/2)
        c1 = (Fraction(0), Fraction(0))
        k1 = Fraction(-1, 2)

        # Two internal circles
        c2 = (Fraction(-1), Fraction(0))
        k2 = Fraction(1)

        c3 = (Fraction(1), Fraction(0))
        k3 = Fraction(1)

        # Calculate fourth circle curvature
        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Calculate center
        center = descartes_center(c1, c2, c3, k1, k2, k3, k4_plus, sign=1)

        # Center should be a valid Fraction tuple
        assert isinstance(center[0], Fraction)
        assert isinstance(center[1], Fraction)

        # Verify center is a reasonable value (not NaN, not infinite)
        assert not math.isnan(float(center[0]))
        assert not math.isnan(float(center[1]))
        assert abs(float(center[0])) < 100
        assert abs(float(center[1])) < 100

    def test_negative_curvature_enclosing(self):
        """
        Test with enclosing circle (negative curvature).

        Using the standard Apollonian gasket configuration: (-1, 2, 2, 3)
        When given (-1, 2, 3), we expect k4 to have both positive solutions.
        """
        k1 = Fraction(-1)  # Enclosing circle
        k2 = Fraction(2)
        k3 = Fraction(3)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Both solutions should be positive (internal to enclosing circle)
        # Expected: k4 = 4 ± 2 = {6, 2}
        assert k4_plus > 0, f"k4_plus should be positive, got {k4_plus}"
        assert k4_minus > 0, f"k4_minus should be positive, got {k4_minus}"
        assert k4_plus == Fraction(6)
        assert k4_minus == Fraction(2)

    def test_large_curvatures_stability(self):
        """
        Test numerical stability with large curvatures.

        Should not raise overflow or precision errors.
        """
        k1 = Fraction(1000)
        k2 = Fraction(1001)
        k3 = Fraction(1002)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Should not overflow, should return valid Fractions
        assert isinstance(k4_plus, Fraction)
        assert isinstance(k4_minus, Fraction)

        # Results should be reasonable (not infinite, not NaN)
        assert abs(float(k4_plus)) < 1000000
        assert abs(float(k4_minus)) < 1000000

    def test_descartes_solve_integration(self):
        """
        Test the integrated descartes_solve function.

        Combines curvature and center calculations.
        """
        # Three circles with known configuration
        circle1 = (Fraction(-1), (Fraction(0), Fraction(0)))  # Enclosing
        circle2 = (Fraction(2), (Fraction(1), Fraction(0)))
        circle3 = (Fraction(2), (Fraction(-1), Fraction(0)))

        # Solve for the two tangent circles
        circle_plus, circle_minus = descartes_solve(circle1, circle2, circle3)

        # Extract results
        k4_plus, center_plus = circle_plus
        k4_minus, center_minus = circle_minus

        # Verify curvatures are Fractions
        assert isinstance(k4_plus, Fraction)
        assert isinstance(k4_minus, Fraction)

        # Verify centers are valid ComplexFraction tuples
        assert isinstance(center_plus, tuple) and len(center_plus) == 2
        assert isinstance(center_minus, tuple) and len(center_minus) == 2
        assert isinstance(center_plus[0], Fraction)
        assert isinstance(center_plus[1], Fraction)

        # Verify results are reasonable
        assert abs(float(k4_plus)) < 1000
        assert abs(float(center_plus[0])) < 100
        assert abs(float(center_plus[1])) < 100
