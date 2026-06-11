"""
Exact tests for the Apollonian group action (swap reflections).

Reference: REVAMP_BLUEPRINT.md Phase 3.3 — reflection involution, invariant
preservation, and known bend values are checked with exact equality.
"""

import random
from fractions import Fraction

from core.engine.group import apply_reflection, reflect, reflection_coefficients
from core.engine.inversive import InversiveCircle
from core.engine.seeds import seed_from_preset, seed_strip


def classic_quartet():
    return seed_from_preset("classic")


class TestReflection:
    def test_known_bends(self):
        """Reflections of (-1, 2, 2, 3) give bends 15, 6, 6, 3."""
        q = classic_quartet()
        assert [reflect(q, j).curvature for j in range(4)] == [15, 6, 6, 3]

    def test_reflected_circle_exact_coordinates(self):
        """Reflecting the bounding circle gives the bend-15 circle exactly."""
        q = classic_quartet()
        v = reflect(q, 0)
        assert v == InversiveCircle(1, 15, 0, 4)
        assert v.center() == (0, Fraction(4, 15))

    def test_preserves_q_form(self):
        """Q(Sⱼ v) = -1 exactly for every reflection."""
        q = classic_quartet()
        for j in range(4):
            assert reflect(q, j).q_form() == -1

    def test_preserves_tangency(self):
        """The reflected circle is tangent to the three fixed circles."""
        q = classic_quartet()
        for j in range(4):
            new = reflect(q, j)
            for m in range(4):
                if m != j:
                    assert new.inner(q[m]) == 1

    def test_involution(self):
        """Sⱼ(Sⱼ(quartet)) = quartet exactly."""
        q = classic_quartet()
        for j in range(4):
            assert apply_reflection(apply_reflection(q, j), j) == q

    def test_involution_on_strip(self):
        """Involution also holds with lines in the quartet."""
        q = seed_strip()
        for j in range(4):
            assert apply_reflection(apply_reflection(q, j), j) == q

    def test_invalid_index(self):
        q = classic_quartet()
        for j in (-1, 4):
            try:
                reflect(q, j)
                assert False, "expected ValueError"
            except ValueError:
                pass


class TestReflectionMatrix:
    def test_matrix_is_involution_over_z(self):
        """The 4×4 coefficient matrix of Sⱼ squares to the identity over ℤ."""
        identity = [[1 if i == m else 0 for m in range(4)] for i in range(4)]
        for j in range(4):
            mat = reflection_coefficients(j)
            square = [
                [sum(mat[i][k] * mat[k][m] for k in range(4)) for m in range(4)]
                for i in range(4)
            ]
            assert square == identity

    def test_matrix_matches_reflect(self):
        """Applying the coefficient matrix reproduces reflect()."""
        q = classic_quartet()
        for j in range(4):
            mat = reflection_coefficients(j)
            expected = reflect(q, j)
            row = mat[j]
            combined = InversiveCircle(
                sum(row[m] * q[m].cocurvature for m in range(4)),
                sum(row[m] * q[m].curvature for m in range(4)),
                sum(row[m] * q[m].kx for m in range(4)),
                sum(row[m] * q[m].ky for m in range(4)),
            )
            assert combined == expected


class TestRandomWords:
    def test_invariants_along_random_reduced_words(self):
        """Q = -1 and pairwise B = 1 hold exactly along random reduced words.

        Deterministic randomized property test (seeded) over words of length
        up to 12 in the Apollonian group.
        """
        rng = random.Random(0)
        for _ in range(25):
            quartet = classic_quartet()
            last = -1
            for _ in range(rng.randint(1, 12)):
                j = rng.choice([m for m in range(4) if m != last])
                quartet = apply_reflection(quartet, j)
                last = j
            for i in range(4):
                assert quartet[i].q_form() == -1
                for m in range(i + 1, 4):
                    assert quartet[i].inner(quartet[m]) == 1
