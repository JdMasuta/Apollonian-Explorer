"""
Exact tests for seed (root quartet) construction.

Reference: REVAMP_BLUEPRINT.md Phase 3.3. Placement results are pinned as
exact rational values; tangency is verified through the inversive inner
product, never by float distance.
"""

from fractions import Fraction

import pytest
import sympy as sp

from core.engine.inversive import InversiveCircle
from core.engine.seeds import (
    PRESETS,
    complete_triple,
    is_descartes_quadruple,
    seed_from_preset,
    seed_from_quadruple,
    seed_from_triple,
    seed_strip,
)


class TestQuadrupleValidation:
    def test_valid_integral_quadruples(self):
        for quad in [(-1, 2, 2, 3), (-2, 3, 6, 7), (-3, 4, 12, 13), (-11, 21, 24, 28),
                     (2, 2, 3, 15), (0, 0, 1, 1)]:
            assert is_descartes_quadruple(*quad), quad

    def test_invalid_quadruples(self):
        for quad in [(-1, 2, 2, 4), (1, 2, 3, 4), (-1, 1, 1, 1)]:
            assert not is_descartes_quadruple(*quad), quad

    def test_rational_quadruple(self):
        # Scaling a valid quadruple by a rational preserves the relation.
        scaled = tuple(Fraction(k, 5) for k in (-1, 2, 2, 3))
        assert is_descartes_quadruple(*scaled)


class TestCompleteTriple:
    def test_classic_degenerate(self):
        """(-1, 2, 2): discriminant 0, double root 3."""
        assert complete_triple(-1, 2, 2) == (3, 3)

    def test_classic_inner_pair(self):
        """(-1, 2, 3): completions 6 and 2."""
        assert complete_triple(-1, 2, 3) == (6, 2)

    def test_irrational_completion(self):
        """(1, 1, 1): 3 ± 2√3 exactly."""
        plus, minus = complete_triple(1, 1, 1)
        assert sp.simplify(plus - (3 + 2 * sp.sqrt(3))) == 0
        assert sp.simplify(minus - (3 - 2 * sp.sqrt(3))) == 0

    def test_completions_satisfy_descartes(self):
        for triple in [(-1, 2, 3), (2, 3, 6), (5, 8, 8)]:
            for k4 in complete_triple(*triple):
                assert is_descartes_quadruple(*triple, k4)

    def test_negative_discriminant_rejected(self):
        with pytest.raises(ValueError, match="discriminant"):
            complete_triple(-1, 1, Fraction(1, 10))


class TestQuadruplePlacement:
    def test_classic_exact_positions(self):
        """(-1, 2, 2, 3) places at known exact rational coordinates."""
        q = seed_from_quadruple(-1, 2, 2, 3)
        assert [v.curvature for v in q] == [-1, 2, 2, 3]
        assert q[0].center() == (0, 0)
        assert q[1].center() == (Fraction(1, 2), 0)
        assert q[2].center() == (Fraction(-1, 2), 0)
        assert q[3].center() == (0, Fraction(2, 3))

    def test_classic_integer_coordinates(self):
        """Integral packings have all-integer inversive coordinates."""
        q = seed_from_quadruple(-1, 2, 2, 3)
        for v in q:
            for value in (v.cocurvature, v.curvature, v.kx, v.ky):
                assert isinstance(value, int), v

    def test_all_presets_construct_and_verify(self):
        for name in PRESETS:
            q = seed_from_preset(name)
            for i in range(4):
                assert q[i].q_form() == -1
                for j in range(i + 1, 4):
                    assert q[i].inner(q[j]) == 1

    def test_all_positive_quadruple(self):
        """Interior quartets (no enclosing circle) place correctly."""
        q = seed_from_quadruple(2, 2, 3, 15)
        for i in range(4):
            for j in range(i + 1, 4):
                assert q[i].inner(q[j]) == 1

    def test_big_integral_quadruple(self):
        q = seed_from_quadruple(-11, 21, 24, 28)
        for i in range(4):
            assert q[i].q_form() == -1
            for j in range(i + 1, 4):
                assert q[i].inner(q[j]) == 1

    def test_invalid_quadruple_rejected(self):
        with pytest.raises(ValueError, match="Descartes"):
            seed_from_quadruple(-1, 2, 2, 4)

    def test_zero_curvature_rejected(self):
        with pytest.raises(ValueError, match="strip"):
            seed_from_quadruple(0, 0, 1, 1)

    def test_two_negative_rejected(self):
        # Satisfies no valid geometry; the curvature sign check fires first
        # for quadruples passing the algebraic relation is impossible, so use
        # a synthetic case that passes neither.
        with pytest.raises(ValueError):
            seed_from_quadruple(-1, -1, 2, 2)


class TestTriplePlacement:
    def test_classic_triple(self):
        """(-1, 2, 2) completes to the standard gasket quartet."""
        q = seed_from_triple(-1, 2, 2)
        assert [v.curvature for v in q] == [-1, 2, 2, 3]

    def test_irrational_triple(self):
        """(1, 1, 1) completes to enclosing circle 3 - 2√3 and verifies."""
        q = seed_from_triple(1, 1, 1)
        assert sp.simplify(sp.sympify(q[3].curvature) - (3 - 2 * sp.sqrt(3))) == 0
        for i in range(4):
            assert q[i].is_valid()
            for j in range(i + 1, 4):
                assert q[i].is_tangent_to(q[j])


class TestStrip:
    def test_strip_structure(self):
        q = seed_strip()
        assert q[0].is_line and q[1].is_line
        assert q[2].curvature == 1 and q[3].curvature == 1
        assert q[0] == InversiveCircle(0, 0, 0, -1)
        assert q[1] == InversiveCircle(4, 0, 0, 1)

    def test_strip_tangencies(self):
        q = seed_strip()
        for i in range(4):
            assert q[i].q_form() == -1
            for j in range(i + 1, 4):
                assert q[i].inner(q[j]) == 1
