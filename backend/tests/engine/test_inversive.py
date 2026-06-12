"""
Exact-equality tests for inversive (augmented curvature-center) coordinates.

Reference: REVAMP_BLUEPRINT.md Phase 3.3 — all invariants are exact algebraic
identities; no floating-point tolerances appear anywhere in this suite.
"""

from fractions import Fraction

import pytest
import sympy as sp

from core.engine.inversive import InversiveCircle


class TestConstruction:
    def test_unit_circle_at_origin(self):
        """Unit circle: b = 1, center (0,0), cocurvature -1."""
        v = InversiveCircle.from_curvature_center(1, 0, 0)
        assert v == InversiveCircle(-1, 1, 0, 0)

    def test_bounding_circle(self):
        """Enclosing unit circle: b = -1, cocurvature +1."""
        v = InversiveCircle.from_curvature_center(-1, 0, 0)
        assert v == InversiveCircle(1, -1, 0, 0)

    def test_rational_circle(self):
        """b = 3 at (0, 2/3): v = (1, 3, 0, 2) — all integers."""
        v = InversiveCircle.from_curvature_center(3, 0, Fraction(2, 3))
        assert v == InversiveCircle(1, 3, 0, 2)

    def test_zero_curvature_rejected(self):
        with pytest.raises(ValueError, match="line"):
            InversiveCircle.from_curvature_center(0, 1, 1)

    def test_line_construction(self):
        """Line y = 0 with downward normal: v = (0, 0, 0, -1)."""
        v = InversiveCircle.line(0, -1, 0)
        assert v == InversiveCircle(0, 0, 0, -1)
        assert v.is_line

    def test_line_requires_unit_normal(self):
        with pytest.raises(ValueError, match="unit vector"):
            InversiveCircle.line(1, 1, 0)

    def test_irrational_center(self):
        """Centers in Q(√3) stay exact through construction."""
        v = InversiveCircle.from_curvature_center(1, 1, sp.sqrt(3))
        assert v.is_valid()
        x, y = v.center()
        assert x == 1
        assert sp.simplify(y - sp.sqrt(3)) == 0


class TestInvariants:
    def test_q_form_is_minus_one(self):
        """Q(v) = -1 exactly for circles and lines."""
        examples = [
            InversiveCircle.from_curvature_center(-1, 0, 0),
            InversiveCircle.from_curvature_center(2, Fraction(1, 2), 0),
            InversiveCircle.from_curvature_center(Fraction(3, 7), 5, Fraction(-2, 11)),
            InversiveCircle.line(0, 1, 2),
        ]
        for v in examples:
            assert v.q_form() == -1
            assert v.is_valid()

    def test_tangency_inner_product(self):
        """B(v, w) = 1 exactly for tangent pairs of the classic gasket."""
        v_out = InversiveCircle.from_curvature_center(-1, 0, 0)
        v_l = InversiveCircle.from_curvature_center(2, Fraction(-1, 2), 0)
        v_r = InversiveCircle.from_curvature_center(2, Fraction(1, 2), 0)
        v_top = InversiveCircle.from_curvature_center(3, 0, Fraction(2, 3))

        quartet = [v_out, v_l, v_r, v_top]
        for i in range(4):
            for j in range(i + 1, 4):
                assert quartet[i].inner(quartet[j]) == 1
                assert quartet[i].is_tangent_to(quartet[j])

    def test_non_tangent_pair(self):
        """Disjoint circles give B != 1."""
        a = InversiveCircle.from_curvature_center(1, 0, 0)
        b = InversiveCircle.from_curvature_center(1, 10, 0)
        assert a.inner(b) != 1
        assert not a.is_tangent_to(b)


class TestAccessors:
    def test_center_radius_roundtrip(self):
        v = InversiveCircle.from_curvature_center(Fraction(5, 3), Fraction(7, 2), -4)
        x, y = v.center()
        assert x == Fraction(7, 2)
        assert y == -4
        assert v.radius() == Fraction(3, 5)

    def test_negative_curvature_radius(self):
        v = InversiveCircle.from_curvature_center(-2, 0, 0)
        assert v.radius() == Fraction(1, 2)

    def test_line_has_no_center_or_radius(self):
        v = InversiveCircle.line(0, 1, 0)
        with pytest.raises(ValueError):
            v.center()
        with pytest.raises(ValueError):
            v.radius()

    def test_approx(self):
        v = InversiveCircle.from_curvature_center(2, Fraction(1, 2), 0)
        x, y, r = v.approx()
        assert (x, y, r) == (0.5, 0.0, 0.5)

    def test_as_dict_circle(self):
        v = InversiveCircle.from_curvature_center(3, 0, Fraction(2, 3))
        d = v.as_dict()
        assert d["kind"] == "circle"
        assert d["curvature"] == "3"
        assert d["center"] == {"x": "0", "y": "2/3"}
        assert d["radius"] == "1/3"

    def test_as_dict_line(self):
        v = InversiveCircle.line(0, 1, 2)
        d = v.as_dict()
        assert d["kind"] == "line"
        assert d["curvature"] == "0"
        assert d["offset"] == "2"
