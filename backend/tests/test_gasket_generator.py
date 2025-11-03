"""
Unit tests for gasket generation algorithms.

Reference: backend/core/gasket_generator.py
"""

import pytest
from fractions import Fraction
from core.gasket_generator import (
    initialize_standard_gasket,
    generate_apollonian_gasket,
    is_duplicate
)
from core.circle_data import CircleData


class TestInitializeStandardGasket:
    """Tests for standard gasket initialization."""

    def test_three_unit_curvatures(self):
        """Test initialization with three unit curvatures (1, 1, 1)."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = initialize_standard_gasket(curvatures)

        assert len(circles) == 3
        assert all(c.generation == 0 for c in circles)
        assert all(c.parent_ids == [] for c in circles)
        assert all(c.id is None for c in circles)

        # Check curvatures are correct
        assert circles[0].curvature == Fraction(1)
        assert circles[1].curvature == Fraction(1)
        assert circles[2].curvature == Fraction(1)

    def test_three_different_curvatures(self):
        """Test initialization with different curvatures."""
        curvatures = [Fraction(-1), Fraction(2), Fraction(2)]
        circles = initialize_standard_gasket(curvatures)

        assert len(circles) == 3
        assert circles[0].curvature == Fraction(-1)
        assert circles[1].curvature == Fraction(2)
        assert circles[2].curvature == Fraction(2)

    def test_circle_positions_are_set(self):
        """Test that circles have non-None center positions."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = initialize_standard_gasket(curvatures)

        for circle in circles:
            assert circle.center is not None
            assert len(circle.center) == 2
            real, imag = circle.center
            assert isinstance(real, Fraction)
            assert isinstance(imag, Fraction)

    def test_first_circle_at_origin(self):
        """Test that first circle is positioned at origin."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = initialize_standard_gasket(curvatures)

        # First circle should be at origin
        assert circles[0].center == (Fraction(0), Fraction(0))

    def test_circles_have_unique_hashes(self):
        """Test that initialized circles have different hashes."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = initialize_standard_gasket(curvatures)

        hashes = [c.hash_key() for c in circles]

        # All three circles should have unique positions and thus unique hashes
        assert len(set(hashes)) == 3, "All circles should have unique hashes"

    def test_fractional_curvatures(self):
        """Test initialization with fractional curvatures."""
        curvatures = [Fraction(3, 2), Fraction(5, 3), Fraction(7, 4)]
        circles = initialize_standard_gasket(curvatures)

        assert len(circles) == 3
        assert circles[0].curvature == Fraction(3, 2)
        assert circles[1].curvature == Fraction(5, 3)
        assert circles[2].curvature == Fraction(7, 4)

    def test_negative_curvature_enclosing_circle(self):
        """Test with negative curvature (enclosing circle)."""
        curvatures = [Fraction(-1), Fraction(1), Fraction(1)]
        circles = initialize_standard_gasket(curvatures)

        assert len(circles) == 3
        assert circles[0].curvature == Fraction(-1)
        # Enclosing circle should have negative curvature
        assert circles[0].radius() == Fraction(-1)

    def test_two_curvatures_raises_error(self):
        """Test that 2 curvatures raises ValueError."""
        curvatures = [Fraction(1), Fraction(2)]

        with pytest.raises(ValueError, match="Need 3 or 4"):
            initialize_standard_gasket(curvatures)

    def test_five_curvatures_raises_error(self):
        """Test that 5 curvatures raises ValueError."""
        curvatures = [Fraction(1), Fraction(2), Fraction(3), Fraction(4), Fraction(5)]

        with pytest.raises(ValueError, match="Need 3 or 4"):
            initialize_standard_gasket(curvatures)

    def test_zero_curvatures_raises_error(self):
        """Test that 0 curvatures raises ValueError."""
        curvatures = []

        with pytest.raises(ValueError, match="Need 3 or 4"):
            initialize_standard_gasket(curvatures)

    def test_four_curvatures_not_implemented(self):
        """Test that 4 curvatures raises NotImplementedError."""
        curvatures = [Fraction(1), Fraction(2), Fraction(3), Fraction(4)]

        with pytest.raises(NotImplementedError, match="Four-circle initialization"):
            initialize_standard_gasket(curvatures)

    def test_all_circles_have_radii(self):
        """Test that all circles can compute their radii."""
        curvatures = [Fraction(1), Fraction(2), Fraction(3)]
        circles = initialize_standard_gasket(curvatures)

        for circle in circles:
            radius = circle.radius()
            assert isinstance(radius, Fraction)
            # Radius should be non-zero
            assert radius != 0

    def test_radii_match_curvatures(self):
        """Test that radius = 1/curvature for each circle."""
        curvatures = [Fraction(1), Fraction(2), Fraction(3)]
        circles = initialize_standard_gasket(curvatures)

        for circle in circles:
            expected_radius = Fraction(1) / abs(circle.curvature)
            assert circle.radius() == expected_radius or circle.radius() == -expected_radius


class TestGenerateApollonianGasket:
    """Tests for full gasket generation."""

    def test_generates_initial_circles(self):
        """Test that generator includes initial circles."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=0, stream=False))

        # At depth 0, should only have the 3 initial circles
        assert len(circles) == 3
        assert all(c.generation == 0 for c in circles)

    def test_depth_1_generates_new_circles(self):
        """Test that depth 1 generates additional circles."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=1, stream=False))

        # Should have initial 3 + some from depth 1
        assert len(circles) > 3

        # Should have circles at generation 0 and 1
        generations = {c.generation for c in circles}
        assert 0 in generations
        assert 1 in generations

    def test_depth_limiting(self):
        """Test that max_depth limits generation."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]

        circles_d2 = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))
        circles_d3 = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

        # Depth 3 should have more circles than depth 2
        assert len(circles_d3) > len(circles_d2)

        # No circles should exceed max_depth generation
        assert all(c.generation <= 2 for c in circles_d2)
        assert all(c.generation <= 3 for c in circles_d3)

    def test_deduplication_works(self):
        """Test that duplicate circles are not generated."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

        # Check all hashes are unique
        hashes = [c.hash_key() for c in circles]
        assert len(hashes) == len(set(hashes)), "All circles should have unique hashes"

    def test_streaming_mode(self):
        """Test that streaming mode yields circles incrementally."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]

        # Collect streamed circles
        streamed_circles = []
        for circle in generate_apollonian_gasket(curvatures, max_depth=2, stream=True):
            streamed_circles.append(circle)

        # Should have generated circles
        assert len(streamed_circles) > 0

        # Should match batch mode count
        batch_circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))
        assert len(streamed_circles) == len(batch_circles)

    def test_batch_mode(self):
        """Test that batch mode returns all circles at once."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # Should have generated circles
        assert len(circles) > 0

    def test_negative_curvature_configuration(self):
        """Test with negative curvature (enclosing circle)."""
        curvatures = [Fraction(-1), Fraction(2), Fraction(2)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # Should generate circles
        assert len(circles) > 3

        # First circle should have negative curvature
        initial_circles = [c for c in circles if c.generation == 0]
        assert any(c.curvature < 0 for c in initial_circles)

    def test_different_curvatures(self):
        """Test with non-uniform curvatures."""
        curvatures = [Fraction(1), Fraction(2), Fraction(3)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # Should generate circles
        assert len(circles) > 3

        # Initial circles should have specified curvatures
        initial_circles = [c for c in circles if c.generation == 0]
        initial_curvatures = {c.curvature for c in initial_circles}
        assert Fraction(1) in initial_curvatures
        assert Fraction(2) in initial_curvatures
        assert Fraction(3) in initial_curvatures

    def test_fractional_curvatures(self):
        """Test with fractional curvatures."""
        curvatures = [Fraction(3, 2), Fraction(5, 3), Fraction(7, 4)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=1, stream=False))

        # Should generate circles
        assert len(circles) > 3

    def test_all_circles_have_valid_data(self):
        """Test that all generated circles have valid data."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        for circle in circles:
            # Check curvature is a Fraction
            assert isinstance(circle.curvature, Fraction)

            # Check center is a tuple of Fractions
            assert len(circle.center) == 2
            assert isinstance(circle.center[0], Fraction)
            assert isinstance(circle.center[1], Fraction)

            # Check generation is non-negative
            assert circle.generation >= 0

            # Check parent_ids is a list
            assert isinstance(circle.parent_ids, list)

    def test_generation_increments_correctly(self):
        """Test that generation numbers increment correctly."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

        # Group by generation
        from collections import defaultdict
        by_gen = defaultdict(list)
        for circle in circles:
            by_gen[circle.generation].append(circle)

        # Check that we have circles at each generation 0 through 3
        assert 0 in by_gen
        assert 1 in by_gen
        assert 2 in by_gen
        assert 3 in by_gen

        # Generation 0 should have exactly 3 circles (initial)
        assert len(by_gen[0]) == 3

    def test_known_configuration_depth_2(self):
        """Test known configuration produces expected circle count."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # This is a known configuration; verify reasonable count
        # Exact count may vary based on deduplication and geometry
        assert len(circles) >= 10  # Should have at least 10 circles at depth 2
        assert len(circles) <= 20  # Should not have more than 20


class TestIsDuplicate:
    """
    Tests for is_duplicate() helper function.

    Reference: ISSUES.md Issue #3 - Incomplete deduplication
    """

    def test_identical_circle_is_duplicate(self):
        """Test that identical circles are detected as duplicates."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )
        circle2 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )

        assert is_duplicate(
            circle2.curvature,
            circle2.center,
            [circle1]
        )

    def test_different_curvature_not_duplicate(self):
        """Test that circles with different curvatures are not duplicates."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )

        assert not is_duplicate(
            Fraction(2),  # Different curvature
            (Fraction(0), Fraction(0)),
            [circle1]
        )

    def test_different_position_not_duplicate(self):
        """Test that circles with different positions are not duplicates."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )

        assert not is_duplicate(
            Fraction(1),
            (Fraction(1), Fraction(0)),  # Different position
            [circle1]
        )

    def test_near_duplicate_within_tolerance(self):
        """Test that near-duplicates within tolerance are detected."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )

        # Very slightly different due to floating-point approximation
        # Difference: 1e-12, which is less than default tolerance (1e-10)
        near_curvature = Fraction(1000000000000, 1000000000001)

        assert is_duplicate(
            near_curvature,
            (Fraction(0), Fraction(0)),
            [circle1],
            tolerance=1e-10
        )

    def test_near_duplicate_outside_tolerance(self):
        """Test that near-duplicates outside tolerance are not detected."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[]
        )

        # Difference: 0.01, which is greater than tolerance (1e-10)
        different_curvature = Fraction(101, 100)

        assert not is_duplicate(
            different_curvature,
            (Fraction(0), Fraction(0)),
            [circle1],
            tolerance=1e-10
        )

    def test_duplicate_in_list_of_many(self):
        """Test finding duplicate in a list of multiple circles."""
        circles = [
            CircleData(Fraction(1), (Fraction(0), Fraction(0)), 0, []),
            CircleData(Fraction(2), (Fraction(1), Fraction(0)), 0, []),
            CircleData(Fraction(3), (Fraction(2), Fraction(0)), 0, []),
        ]

        # Should match the second circle
        assert is_duplicate(
            Fraction(2),
            (Fraction(1), Fraction(0)),
            circles
        )

    def test_no_duplicate_in_empty_list(self):
        """Test that no duplicate is found in empty list."""
        assert not is_duplicate(
            Fraction(1),
            (Fraction(0), Fraction(0)),
            []
        )


class TestParentCircleDetection:
    """
    Tests for parent circle detection in gasket generation.

    Reference: ISSUES.md Issue #3 - Incomplete deduplication
    """

    def test_no_parent_circles_reappear_depth_1(self):
        """Test that parent circles are not added back at depth 1."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=1, stream=False))

        # Get initial circles (generation 0)
        initial_circles = [c for c in circles if c.generation == 0]
        assert len(initial_circles) == 3

        # Get new circles (generation 1)
        new_circles = [c for c in circles if c.generation == 1]

        # Check that no generation-1 circle matches any initial circle
        for new_circle in new_circles:
            for initial_circle in initial_circles:
                # They should not be duplicates
                assert not is_duplicate(
                    new_circle.curvature,
                    new_circle.center,
                    [initial_circle]
                ), f"Generation 1 circle should not match initial circle"

    def test_no_parent_circles_reappear_depth_2(self):
        """Test that parent circles are not added back at depth 2."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # Group by generation
        by_gen = {}
        for circle in circles:
            if circle.generation not in by_gen:
                by_gen[circle.generation] = []
            by_gen[circle.generation].append(circle)

        # For each generation, ensure no circle appears in earlier generations
        for gen in [1, 2]:
            if gen in by_gen and gen - 1 in by_gen:
                current_gen_circles = by_gen[gen]
                previous_gens_circles = []
                for prev_gen in range(gen):
                    if prev_gen in by_gen:
                        previous_gens_circles.extend(by_gen[prev_gen])

                # Check that no current-generation circle matches any previous circle
                for current_circle in current_gen_circles:
                    assert not is_duplicate(
                        current_circle.curvature,
                        current_circle.center,
                        previous_gens_circles
                    ), f"Gen {gen} circle should not match earlier generations"

    def test_all_circles_unique_across_generations(self):
        """Test that all circles are unique across all generations."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

        # Check every pair of circles
        for i, circle1 in enumerate(circles):
            for j, circle2 in enumerate(circles):
                if i != j:
                    # Two different circles should not be duplicates
                    assert not is_duplicate(
                        circle2.curvature,
                        circle2.center,
                        [circle1]
                    ), f"Circle {i} and circle {j} are duplicates"

    def test_hash_deduplication_still_works(self):
        """Test that hash-based deduplication still functions correctly."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

        # All hashes should still be unique
        hashes = [c.hash_key() for c in circles]
        unique_hashes = set(hashes)

        assert len(hashes) == len(unique_hashes), \
            "Hash deduplication should prevent duplicate hashes"

    def test_numerical_tolerance_catches_edge_cases(self):
        """Test that numerical tolerance catches near-duplicates missed by hashing."""
        curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

        # Manually check that no two circles are within tolerance
        tolerance = 1e-10
        for i, circle1 in enumerate(circles):
            for j, circle2 in enumerate(circles):
                if i != j:
                    curvature_diff = abs(float(circle1.curvature - circle2.curvature))
                    center_x_diff = abs(float(circle1.center[0] - circle2.center[0]))
                    center_y_diff = abs(float(circle1.center[1] - circle2.center[1]))

                    # If curvatures match within tolerance, centers should differ
                    if curvature_diff < tolerance:
                        assert (center_x_diff >= tolerance or center_y_diff >= tolerance), \
                            f"Circles {i} and {j} are too similar (within tolerance)"
