"""Tests for the engine -> CircleData bridge (core.engine_adapter)."""

from fractions import Fraction

import pytest

from core.circle_data import CircleData
from core.engine_adapter import generate_circles


class TestGenerateCircles:
    def test_classic_triple(self):
        """(-1, 2, 2) completes to the classic quartet and walks correctly."""
        circles = list(generate_circles([-1, 2, 2], max_depth=2))

        assert all(isinstance(c, CircleData) for c in circles)
        seed_bends = sorted(c.curvature for c in circles if c.generation == 0)
        assert seed_bends == [-1, 2, 2, 3]
        gen1 = sorted(c.curvature for c in circles if c.generation == 1)
        assert gen1 == [3, 6, 6, 15]
        # 4 seed + 4 + 12
        assert len(circles) == 20

    def test_quadruple_now_supported(self):
        """4 curvatures work (the legacy generator raised NotImplementedError)."""
        circles = list(generate_circles([-1, 2, 2, 3], max_depth=1))
        assert len(circles) == 8

    def test_fraction_curvatures(self):
        scaled = [Fraction(k, 5) for k in (-1, 2, 2)]
        circles = list(generate_circles(scaled, max_depth=1))
        assert sorted(c.curvature for c in circles if c.generation == 0) == sorted(
            scaled + [Fraction(3, 5)]
        )

    def test_exact_centers(self):
        circles = list(generate_circles([-1, 2, 2], max_depth=0))
        by_bend_y = sorted((c.curvature, c.center) for c in circles)
        assert by_bend_y[0] == (-1, (0, 0))
        assert (3, (0, Fraction(2, 3))) in by_bend_y

    def test_max_circles_cap(self):
        circles = list(generate_circles([-1, 2, 2], max_depth=5, max_circles=10))
        assert len(circles) == 10

    def test_invalid_count(self):
        with pytest.raises(ValueError, match="3 or 4"):
            list(generate_circles([1, 1], max_depth=1))

    def test_invalid_quadruple(self):
        with pytest.raises(ValueError, match="Descartes"):
            list(generate_circles([-1, 2, 2, 4], max_depth=1))

    def test_unrealizable_triple(self):
        with pytest.raises(ValueError, match="discriminant"):
            list(generate_circles([-1, 1, Fraction(1, 10)], max_depth=1))

    def test_database_dict_roundtrip(self):
        """Engine-produced CircleData serializes through the legacy DB path."""
        circles = list(generate_circles([-1, 2, 2], max_depth=1))
        for c in circles:
            d = c.to_database_dict()
            assert Fraction(d["curvature_num"], d["curvature_denom"]) == Fraction(c.curvature)
            assert d["curvature_exact"].startswith(("int:", "frac:"))
