"""Tests for inversions, dual circles, and parabolic cusp chains (M5)."""

import time

import pytest

from core.engine.cusp import cusp_chain
from core.engine.group import dual_circle, invert, reflect
from core.engine.seeds import seed_from_preset
from core.engine.walk import WalkBudget, walk


class TestInversion:
    def test_involution_and_invariants(self):
        q = seed_from_preset("classic")
        mirror = q[3]  # bend-3 circle
        for target in q:
            image = invert(mirror, target)
            assert image.q_form() == -1
            assert invert(mirror, image) == target  # involution

    def test_preserves_inner_products(self):
        """Lorentz reflection: all pairwise B values preserved exactly."""
        q = seed_from_preset("classic")
        mirror = q[3]
        images = [invert(mirror, v) for v in q]
        for i in range(4):
            for j in range(4):
                assert images[i].inner(images[j]) == q[i].inner(q[j])

    def test_unit_circle_inversion_swaps_cocurvature(self):
        q = seed_from_preset("classic")  # q[0] is the unit bounding circle
        image = invert(q[0], q[1])
        assert image.cocurvature == q[1].curvature
        assert image.curvature == q[1].cocurvature

    def test_member_through_center_maps_to_line(self):
        """The bend-2 circles pass through the origin: images are lines."""
        q = seed_from_preset("classic")
        assert invert(q[0], q[1]).is_line
        assert invert(q[0], q[2]).is_line


class TestDualCircles:
    def test_dual_properties(self):
        q = seed_from_preset("classic")
        for j in range(4):
            d = dual_circle(q, j)
            assert d.q_form() == -1
            for m in range(4):
                if m != j:
                    assert d.inner(q[m]) == 0  # orthogonal to the fixed three

    def test_dual_inversion_realizes_swap(self):
        """invert(D_j, v_j) == reflect(quartet, j): the dual Apollonian group
        realizes the swaps as Möbius actions."""
        q = seed_from_preset("classic")
        for j in range(4):
            assert invert(dual_circle(q, j), q[j]) == reflect(q, j)


class TestCuspChain:
    def test_origin_cusp_bends(self):
        """Chain at the tangency of the two bend-2 circles: bends 4n²-1."""
        seed = seed_from_preset("classic")
        result = cusp_chain(seed, "S1", "S2", min_radius=1e-3)
        assert result.verified_words
        bends = sorted(set(r.circle.curvature for r in result.records))
        assert bends[:5] == [3, 15, 35, 63, 99]

    def test_words_match_tree_walk(self):
        """Chain words are sound tree addresses (dedupe-safe)."""
        seed = seed_from_preset("classic")
        result = cusp_chain(seed, "S1", "S2", min_radius=1e-3)
        tree = {c.word: c.circle for c in walk(seed, WalkBudget(max_depth=8))}
        overlapping = [r for r in result.records if r.word in tree]
        assert overlapping, "expected word overlap with the tree walk"
        for r in overlapping:
            assert tree[r.word] == r.circle

    def test_exact_invariants(self):
        seed = seed_from_preset("classic")
        result = cusp_chain(seed, "S1", "S2", min_radius=1e-4)
        for r in result.records:
            assert r.circle.q_form() == -1
            assert r.circle.inner(seed[1]) == 1
            assert r.circle.inner(seed[2]) == 1

    def test_deep_word_anchors(self):
        """Cusp between a deep circle and one of its parents."""
        seed = seed_from_preset("classic")
        result = cusp_chain(seed, "0", "S1", min_radius=1e-3)
        assert result.records
        target_a = reflect(seed, 0)
        for r in result.records:
            assert r.circle.inner(target_a) == 1
            assert r.circle.inner(seed[1]) == 1

    def test_o1_per_element(self):
        """Parabolic acceleration: bend ~1e6 chains in milliseconds
        (the tree walk would need word length ~ sqrt(bend) ≈ 500+)."""
        seed = seed_from_preset("classic")
        start = time.time()
        result = cusp_chain(seed, "S1", "S2", min_radius=1e-10)
        assert time.time() - start < 1.0
        assert max(r.circle.curvature for r in result.records) > 1e5

    def test_non_tangent_rejected(self):
        # The two bend-3 circles (top/bottom) are disjoint: B = 7.
        seed = seed_from_preset("classic")
        with pytest.raises(ValueError, match="not tangent"):
            cusp_chain(seed, "S3", "3", min_radius=1e-3)

    def test_invalid_word_rejected(self):
        seed = seed_from_preset("classic")
        with pytest.raises(ValueError):
            cusp_chain(seed, "00", "S1", min_radius=1e-3)
