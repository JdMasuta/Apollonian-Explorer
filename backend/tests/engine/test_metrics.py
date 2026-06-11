"""Tests for research metrics over generated circles."""

from fractions import Fraction

import pytest

from core.engine.inversive import InversiveCircle
from core.engine.metrics import bend_residue, integer_bend, is_prime_bend
from core.engine.seeds import seed_from_preset
from core.engine.walk import WalkBudget, walk


def circle_with_bend(b):
    return InversiveCircle.from_curvature_center(b, 0, 0)


class TestIntegerBend:
    def test_int(self):
        assert integer_bend(circle_with_bend(6)) == 6

    def test_integral_fraction(self):
        assert integer_bend(circle_with_bend(Fraction(6, 1))) == 6

    def test_non_integral(self):
        assert integer_bend(circle_with_bend(Fraction(3, 2))) is None


class TestResidues:
    def test_residues_mod_24_classic(self):
        """Admissible residues mod 24 of the (-1,2,2,3) packing are the
        known eight classes {2, 3, 6, 11, 14, 15, 18, 23} (with -1 ≡ 23)."""
        circles = list(walk(seed_from_preset("classic"), WalkBudget(max_depth=6)))
        residues = {bend_residue(c.circle, 24) for c in circles}
        assert residues == {2, 3, 6, 11, 14, 15, 18, 23}

    def test_invalid_modulus(self):
        with pytest.raises(ValueError):
            bend_residue(circle_with_bend(6), 0)


class TestPrimeBends:
    def test_prime(self):
        assert is_prime_bend(circle_with_bend(11)) is True

    def test_composite(self):
        assert is_prime_bend(circle_with_bend(6)) is False

    def test_negative_uses_absolute_value(self):
        assert is_prime_bend(circle_with_bend(-11)) is True

    def test_non_integral(self):
        assert is_prime_bend(circle_with_bend(Fraction(3, 2))) is None
