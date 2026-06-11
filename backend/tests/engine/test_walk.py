"""
Tests for the duplicate-free packing walk.

Reference: REVAMP_BLUEPRINT.md Phase 3.3 — regression tests pin verified
integer bend sequences for classic packings; structural tests verify the
4·3^(g-1) circles-per-generation law and duplicate-freedom by construction.
"""

import time
from collections import Counter
from fractions import Fraction

from core.engine.seeds import seed_from_preset, seed_strip
from core.engine.walk import GeneratedCircle, WalkBudget, walk


def classic_walk(depth):
    return list(walk(seed_from_preset("classic"), WalkBudget(max_depth=depth)))


class TestStructure:
    def test_generation_counts(self):
        """Bounded packings emit exactly 4·3^(g-1) circles at generation g."""
        circles = classic_walk(4)
        counts = Counter(c.generation for c in circles)
        assert counts == {0: 4, 1: 4, 2: 12, 3: 36, 4: 108}

    def test_no_duplicates(self):
        """Reduced-word enumeration emits every circle exactly once."""
        circles = classic_walk(5)
        keys = {
            (c.circle.cocurvature, c.circle.curvature, c.circle.kx, c.circle.ky)
            for c in circles
        }
        assert len(keys) == len(circles)

    def test_all_valid_and_words_reduced(self):
        circles = classic_walk(4)
        for c in circles:
            assert c.circle.q_form() == -1
            for a, b in zip(c.word, c.word[1:]):
                assert a != b, f"non-reduced word {c.word}"

    def test_words_unique(self):
        circles = classic_walk(4)
        words = [c.word for c in circles if c.generation > 0]
        assert len(words) == len(set(words))


class TestKnownBends:
    def test_generation_one_bends(self):
        circles = classic_walk(1)
        bends = sorted(c.circle.curvature for c in circles if c.generation == 1)
        assert bends == [3, 6, 6, 15]

    def test_generation_two_bends(self):
        """Pinned, hand-verified gen-2 bend multiset of the (-1,2,2,3) gasket."""
        circles = classic_walk(2)
        bends = sorted(c.circle.curvature for c in circles if c.generation == 2)
        assert bends == [6, 6, 11, 11, 14, 14, 15, 23, 23, 35, 38, 38]

    def test_integral_packing_all_integer_bends(self):
        """Every bend of an integral packing is an integer (in fact, every
        inversive coordinate is)."""
        circles = classic_walk(5)
        for c in circles:
            assert isinstance(c.circle.curvature, int)

    def test_minus11_21_24_28_gen1(self):
        """Root quadruple (-11, 21, 24, 28): reflections give
        2·(sum of other three) − k."""
        circles = list(walk(seed_from_preset("minus11-21-24-28"), WalkBudget(max_depth=1)))
        bends = sorted(c.circle.curvature for c in circles if c.generation == 1)
        # 2(21+24+28)+11 = 157, 2(-11+24+28)-21 = 61, 2(-11+21+28)-24 = 52,
        # 2(-11+21+24)-28 = 40
        assert bends == [40, 52, 61, 157]


class TestStripWalk:
    def test_strip_first_generation(self):
        circles = list(walk(seed_strip(), WalkBudget(max_depth=1)))
        gen1 = [c.circle for c in circles if c.generation == 1]
        described = sorted(
            (v.curvature, v.center() if not v.is_line else None) for v in gen1
        )
        assert described == [
            (1, (-2, 1)),
            (1, (4, 1)),
            (4, (1, Fraction(1, 4))),
            (4, (1, Fraction(7, 4))),
        ]

    def test_strip_invariants_deep(self):
        circles = list(walk(seed_strip(), WalkBudget(max_depth=4)))
        for c in circles:
            assert c.circle.q_form() == -1


class TestBudgets:
    def test_max_circles(self):
        circles = list(walk(seed_from_preset("classic"), WalkBudget(max_depth=5, max_circles=10)))
        assert len(circles) == 10

    def test_max_curvature_prunes(self):
        full = classic_walk(3)
        pruned = list(
            walk(seed_from_preset("classic"), WalkBudget(max_depth=3, max_curvature=100.0))
        )
        full_keys = {
            (c.circle.cocurvature, c.circle.curvature, c.circle.kx, c.circle.ky) for c in full
        }
        for c in pruned:
            key = (c.circle.cocurvature, c.circle.curvature, c.circle.kx, c.circle.ky)
            assert key in full_keys
            assert c.generation == 0 or float(c.circle.curvature) <= 100.0
        assert len(pruned) < len(full)

    def test_depth_zero(self):
        circles = list(walk(seed_from_preset("classic"), WalkBudget(max_depth=0)))
        assert len(circles) == 4
        assert all(c.generation == 0 for c in circles)

    def test_seed_records(self):
        circles = list(walk(seed_from_preset("classic"), WalkBudget(max_depth=0)))
        assert [c.seed_index for c in circles] == [0, 1, 2, 3]
        assert all(isinstance(c, GeneratedCircle) for c in circles)


class TestPerformance:
    def test_depth_ten_under_budget(self):
        """Milestone 1 acceptance: depth-10 classic gasket in < 5s in CI
        (typically ~0.5s); 118,100 circles."""
        start = time.time()
        count = sum(1 for _ in walk(seed_from_preset("classic"), WalkBudget(max_depth=10)))
        elapsed = time.time() - start
        assert count == 4 + 2 * (3**10 - 1)  # 4 + Σ 4·3^(g-1) = 118,100
        assert elapsed < 5.0, f"depth-10 walk took {elapsed:.2f}s"
