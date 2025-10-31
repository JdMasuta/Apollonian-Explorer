"""
Unit tests for circle mathematics utilities.

Reference: backend/core/circle_math.py
"""

import pytest
from fractions import Fraction
from core.circle_math import (
    curvature_to_radius,
    circle_hash,
    fraction_to_tuple,
    tuple_to_fraction,
)


class TestCurvatureToRadius:
    """Tests for curvature to radius conversion."""

    def test_simple_curvature(self):
        """Test with simple integer curvature."""
        k = Fraction(2)
        r = curvature_to_radius(k)
        assert r == Fraction(1, 2)

    def test_unit_curvature(self):
        """Test with curvature = 1."""
        k = Fraction(1)
        r = curvature_to_radius(k)
        assert r == Fraction(1, 1)

    def test_fractional_curvature(self):
        """Test with fractional curvature."""
        k = Fraction(3, 2)
        r = curvature_to_radius(k)
        assert r == Fraction(2, 3)

    def test_negative_curvature(self):
        """Test with negative curvature (enclosing circle)."""
        k = Fraction(-1)
        r = curvature_to_radius(k)
        assert r == Fraction(-1, 1)

    def test_zero_curvature_raises_error(self):
        """Test that zero curvature raises ZeroDivisionError."""
        k = Fraction(0)
        with pytest.raises(ZeroDivisionError, match="infinite radius"):
            curvature_to_radius(k)


class TestCircleHash:
    """Tests for circle hash generation."""

    def test_origin_circle(self):
        """Test hash for circle at origin."""
        hash_val = circle_hash(Fraction(1), Fraction(0), Fraction(0))
        assert isinstance(hash_val, str)
        assert len(hash_val) == 32  # MD5 hex length

    def test_same_circle_same_hash(self):
        """Test that identical circles produce identical hashes."""
        hash1 = circle_hash(Fraction(1), Fraction(0), Fraction(0))
        hash2 = circle_hash(Fraction(1), Fraction(0), Fraction(0))
        assert hash1 == hash2

    def test_different_circles_different_hash(self):
        """Test that different circles produce different hashes."""
        hash1 = circle_hash(Fraction(1), Fraction(0), Fraction(0))
        hash2 = circle_hash(Fraction(2), Fraction(0), Fraction(0))
        hash3 = circle_hash(Fraction(1), Fraction(1), Fraction(0))
        hash4 = circle_hash(Fraction(1), Fraction(0), Fraction(1))

        # All should be different
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash1 != hash4
        assert hash2 != hash3

    def test_fractional_values(self):
        """Test hash with fractional curvature and center."""
        hash_val = circle_hash(Fraction(3, 2), Fraction(1, 4), Fraction(-1, 3))
        assert isinstance(hash_val, str)
        assert len(hash_val) == 32

    def test_equivalent_fractions_same_hash(self):
        """Test that equivalent fractions produce same hash."""
        # Fraction automatically reduces, so 2/4 becomes 1/2
        hash1 = circle_hash(Fraction(1, 2), Fraction(1, 2), Fraction(0))
        hash2 = circle_hash(Fraction(2, 4), Fraction(2, 4), Fraction(0))
        assert hash1 == hash2  # Fractions are automatically reduced


class TestFractionConversion:
    """Tests for fraction tuple conversion."""

    def test_fraction_to_tuple_simple(self):
        """Test simple fraction to tuple."""
        f = Fraction(3, 4)
        num, denom = fraction_to_tuple(f)
        assert num == 3
        assert denom == 4

    def test_fraction_to_tuple_negative(self):
        """Test negative fraction to tuple."""
        f = Fraction(-5, 7)
        num, denom = fraction_to_tuple(f)
        assert num == -5
        assert denom == 7

    def test_fraction_to_tuple_whole_number(self):
        """Test whole number fraction to tuple."""
        f = Fraction(5)
        num, denom = fraction_to_tuple(f)
        assert num == 5
        assert denom == 1

    def test_tuple_to_fraction_simple(self):
        """Test simple tuple to fraction."""
        f = tuple_to_fraction(3, 4)
        assert f == Fraction(3, 4)

    def test_tuple_to_fraction_negative(self):
        """Test negative tuple to fraction."""
        f = tuple_to_fraction(-5, 7)
        assert f == Fraction(-5, 7)

    def test_tuple_to_fraction_whole_number(self):
        """Test whole number tuple to fraction."""
        f = tuple_to_fraction(5, 1)
        assert f == Fraction(5, 1)

    def test_tuple_to_fraction_zero_denominator(self):
        """Test that zero denominator raises error."""
        with pytest.raises(ZeroDivisionError):
            tuple_to_fraction(5, 0)

    def test_round_trip_conversion(self):
        """Test round-trip conversion preserves value."""
        original = Fraction(22, 7)
        num, denom = fraction_to_tuple(original)
        reconstructed = tuple_to_fraction(num, denom)
        assert original == reconstructed

    def test_round_trip_negative(self):
        """Test round-trip with negative fraction."""
        original = Fraction(-22, 7)
        num, denom = fraction_to_tuple(original)
        reconstructed = tuple_to_fraction(num, denom)
        assert original == reconstructed

    def test_round_trip_reduces_fraction(self):
        """Test that Fraction automatically reduces."""
        num, denom = 6, 8  # Should reduce to 3/4
        f = tuple_to_fraction(num, denom)
        assert f == Fraction(3, 4)
        # When we extract again, we get the reduced form
        new_num, new_denom = fraction_to_tuple(f)
        assert new_num == 3
        assert new_denom == 4
