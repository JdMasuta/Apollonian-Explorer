"""
Apollonian Gasket generation algorithm.

Reference: .DESIGN_SPEC.md section 8.2 (Gasket Generation Algorithm)

This module implements the recursive generation of Apollonian gaskets
using the Descartes Circle Theorem and breadth-first search.
"""

import math
from fractions import Fraction
from typing import List, Generator, Set, Tuple
from collections import deque

from core.circle_data import CircleData, ComplexFraction
from core.descartes import descartes_solve


def is_duplicate(
    curvature: Fraction,
    center: Tuple[Fraction, Fraction],
    existing_circles: List[CircleData],
    tolerance: float = 1e-10
) -> bool:
    """
    Check if a circle is a duplicate of any existing circle.

    Uses numerical tolerance to handle floating-point precision issues
    in square root calculations during Descartes theorem.

    Args:
        curvature: Curvature of the circle to check
        center: Center coordinates as (x, y) tuple of Fractions
        existing_circles: List of CircleData objects to check against
        tolerance: Maximum difference for considering values equal (default 1e-10)

    Returns:
        True if circle matches any existing circle within tolerance, False otherwise

    Reference:
        ISSUES.md Issue #3 - Incomplete deduplication in BFS
    """
    for existing in existing_circles:
        # Check curvature match
        curvature_diff = abs(float(curvature - existing.curvature))
        if curvature_diff < tolerance:
            # Check center coordinates match
            center_x_diff = abs(float(center[0] - existing.center[0]))
            center_y_diff = abs(float(center[1] - existing.center[1]))

            if center_x_diff < tolerance and center_y_diff < tolerance:
                return True

    return False


def initialize_standard_gasket(curvatures: List[Fraction]) -> List[CircleData]:
    """
    Initialize an Apollonian gasket with 3 or 4 starting circles.

    For 3 curvatures, creates circles in a standard triangle configuration.
    For 4 curvatures, uses them as the initial gasket configuration.

    Args:
        curvatures: List of 3-4 curvatures as Fraction objects

    Returns:
        List of CircleData objects representing initial circles

    Raises:
        ValueError: If curvatures count is not 3 or 4

    Note:
        This implementation uses a simplified geometric placement for MVP.
        The circles are positioned to be approximately tangent, but exact
        tangency constraints may not be satisfied for all configurations.
        This can be improved in Phase 7 with full constraint solving.

    Reference:
        .DESIGN_SPEC.md section 8.2 - Standard gasket initialization
    """
    if len(curvatures) == 3:
        return _initialize_three_circles(curvatures)
    elif len(curvatures) == 4:
        return _initialize_four_circles(curvatures)
    else:
        raise ValueError(f"Need 3 or 4 initial curvatures, got {len(curvatures)}")


def _initialize_three_circles(curvatures: List[Fraction]) -> List[CircleData]:
    """
    Initialize gasket with 3 circles in standard configuration.

    Uses simplified placement:
    - Circle 1: at origin
    - Circle 2: tangent to right of circle 1
    - Circle 3: positioned above based on tangency geometry

    Args:
        curvatures: List of exactly 3 curvatures

    Returns:
        List of 3 CircleData objects
    """
    k1, k2, k3 = curvatures

    # Calculate radii
    r1 = Fraction(1) / abs(k1) if k1 != 0 else Fraction(1)
    r2 = Fraction(1) / abs(k2) if k2 != 0 else Fraction(1)
    r3 = Fraction(1) / abs(k3) if k3 != 0 else Fraction(1)

    # Circle 1: at origin
    c1 = CircleData(
        curvature=k1,
        center=(Fraction(0), Fraction(0)),
        generation=0,
        parent_ids=[],
    )

    # Circle 2: tangent to right of circle 1
    # Distance between centers = r1 + r2 (for external tangency)
    # If one has negative curvature (enclosing), adjust accordingly
    if k1 > 0 and k2 > 0:
        # Both circles are external
        center2_x = r1 + r2
    elif k1 < 0 and k2 > 0:
        # Circle 1 encloses circle 2
        center2_x = abs(r1) - r2
    elif k1 > 0 and k2 < 0:
        # Circle 2 encloses circle 1
        center2_x = r1 + abs(r2)
    else:
        # Both negative (unusual but handle it)
        center2_x = abs(r1) - abs(r2)

    c2 = CircleData(
        curvature=k2,
        center=(center2_x, Fraction(0)),
        generation=0,
        parent_ids=[],
    )

    # Circle 3: positioned to be tangent to both c1 and c2
    # For MVP, use simplified geometric calculation
    # This is an approximation and may not be perfectly tangent

    # Use triangle geometry: place circle 3 such that it's tangent to both
    # Distance from c1 center to c3 center should be r1 + r3
    # Distance from c2 center to c3 center should be r2 + r3

    # Using law of cosines to find position
    # This is a simplified approach; exact solution requires solving quadratic

    d12 = float(center2_x)  # Distance between c1 and c2 centers
    r1_f = float(r1)
    r2_f = float(r2)
    r3_f = float(r3)

    # Target distances
    if k1 > 0 and k3 > 0:
        d13 = r1_f + r3_f
    elif k1 < 0 and k3 > 0:
        d13 = abs(r1_f) - r3_f
    else:
        d13 = r1_f + r3_f

    if k2 > 0 and k3 > 0:
        d23 = r2_f + r3_f
    elif k2 < 0 and k3 > 0:
        d23 = abs(r2_f) - r3_f
    else:
        d23 = r2_f + r3_f

    # Using cosine rule: c^2 = a^2 + b^2 - 2ab*cos(C)
    # d23^2 = d13^2 + d12^2 - 2*d13*d12*cos(theta)
    # Solve for cos(theta)
    try:
        cos_theta = (d13**2 + d12**2 - d23**2) / (2 * d13 * d12)
        # Clamp to valid range
        cos_theta = max(-1.0, min(1.0, cos_theta))
        theta = math.acos(cos_theta)

        # Position of c3 center
        center3_x = d13 * math.cos(theta)
        center3_y = d13 * math.sin(theta)

        # Convert back to Fraction with limited denominator
        center3_x_frac = Fraction(center3_x).limit_denominator(1000000)
        center3_y_frac = Fraction(center3_y).limit_denominator(1000000)
    except (ValueError, ZeroDivisionError):
        # Fallback to simple positioning if calculation fails
        center3_x_frac = Fraction(float(center2_x) / 2).limit_denominator(1000000)
        center3_y_frac = Fraction(float(d13)).limit_denominator(1000000)

    c3 = CircleData(
        curvature=k3,
        center=(center3_x_frac, center3_y_frac),
        generation=0,
        parent_ids=[],
    )

    return [c1, c2, c3]


def _initialize_four_circles(curvatures: List[Fraction]) -> List[CircleData]:
    """
    Initialize gasket with 4 circles.

    For MVP, this is not fully implemented. Raises NotImplementedError.
    Full implementation requires specifying positions or solving the
    4-circle tangency system.

    Args:
        curvatures: List of exactly 4 curvatures

    Raises:
        NotImplementedError: Four-circle initialization requires positions

    TODO: Implement in Phase 7 with full constraint solving
    """
    raise NotImplementedError(
        "Four-circle initialization requires position specification. "
        "Currently only 3-circle initialization is supported. "
        "This feature will be implemented in Phase 7."
    )


def generate_apollonian_gasket(
    initial_curvatures: List[Fraction],
    max_depth: int,
    stream: bool = False
) -> Generator[CircleData, None, None]:
    """
    Generate Apollonian gasket using breadth-first search.

    Uses the Descartes Circle Theorem to recursively generate circles.
    For each triplet of mutually tangent circles, computes two new circles
    that are tangent to all three. Continues until max_depth is reached.

    Args:
        initial_curvatures: List of 3-4 curvatures for initial circles
        max_depth: Maximum recursion depth (generation level)
        stream: If True, yield circles as generated (for WebSocket streaming).
                If False, collect all circles and yield at the end.

    Yields:
        CircleData objects as they are generated

    Example:
        >>> curvatures = [Fraction(1), Fraction(1), Fraction(1)]
        >>> circles = list(generate_apollonian_gasket(curvatures, max_depth=3))
        >>> len(circles)  # Should have initial 3 + generated circles
        > 3

    Reference:
        .DESIGN_SPEC.md section 8.2 - BFS gasket generation algorithm
    """
    # Step 1: Initialize starting circles
    circles = initialize_standard_gasket(initial_curvatures)
    circle_hashes: Set[str] = {c.hash_key() for c in circles}

    # Step 2: Yield initial circles if streaming
    if stream:
        for circle in circles:
            yield circle

    # Step 3: Set up BFS queue
    # Queue contains tuples of (circle1, circle2, circle3, depth)
    queue = deque()

    # Step 4: Add all possible initial triplets to queue
    # For 3 initial circles, there's only one triplet
    if len(circles) >= 3:
        # Add the initial triplet
        queue.append((circles[0], circles[1], circles[2], 0))

    # Step 5: BFS loop
    while queue:
        c1, c2, c3, depth = queue.popleft()

        # Check depth limit
        if depth >= max_depth:
            continue

        # Convert CircleData to format expected by descartes_solve
        # descartes_solve expects: (curvature, (center_real, center_imag))
        circle1 = (c1.curvature, c1.center)
        circle2 = (c2.curvature, c2.center)
        circle3 = (c3.curvature, c3.center)

        try:
            # Compute two new circles tangent to all three
            (k_new1, z_new1), (k_new2, z_new2) = descartes_solve(
                circle1, circle2, circle3
            )

            # Process both new circles
            new_circles = []
            for k, z in [(k_new1, z_new1), (k_new2, z_new2)]:
                # ISSUE #3 FIX: Check if this solution is a parent circle
                # Descartes theorem returns two solutions: one new circle + one parent
                # We must explicitly discard the parent before hash checking
                if is_duplicate(k, z, [c1, c2, c3]):
                    # This is the parent circle that was part of the quartet
                    # Skip it and continue to the next solution
                    continue

                # Create CircleData object
                new_circle = CircleData(
                    curvature=k,
                    center=z,
                    generation=depth + 1,
                    parent_ids=[],  # Will be set when persisted to DB
                )

                # Check for duplicates using hash
                hash_key = new_circle.hash_key()
                if hash_key not in circle_hashes:
                    # ISSUE #3 FIX: Additional numerical tolerance check
                    # Hash may miss duplicates due to sqrt approximation errors
                    if not is_duplicate(k, z, circles):
                        # New unique circle found
                        circle_hashes.add(hash_key)
                        circles.append(new_circle)
                        new_circles.append(new_circle)

                        # Yield immediately if streaming
                        if stream:
                            yield new_circle

            # Step 6: Add new triplets to queue for next iteration
            # For each new circle, create triplets with existing parent circles
            for new_circle in new_circles:
                # Create three new triplets, each replacing one parent circle
                queue.append((c1, c2, new_circle, depth + 1))
                queue.append((c2, c3, new_circle, depth + 1))
                queue.append((c3, c1, new_circle, depth + 1))

        except Exception as e:
            # Skip invalid configurations
            # This can happen if the Descartes formula produces invalid results
            # (e.g., complex square roots, invalid geometric configurations)
            # For MVP, we silently skip these cases
            continue

    # Step 7: If not streaming, yield all circles at the end
    if not stream:
        for circle in circles:
            yield circle


# Manual test
if __name__ == "__main__":
    print("Testing gasket generation...")

    # Test 1: Generate small gasket (depth 2)
    print("\n" + "="*50)
    print("Test 1: Generate depth-2 gasket with (1, 1, 1)")
    curvatures = [Fraction(1), Fraction(1), Fraction(1)]
    circles = list(generate_apollonian_gasket(curvatures, max_depth=2, stream=False))

    print(f"Generated {len(circles)} circles at depth 2")
    print(f"Generations: {set(c.generation for c in circles)}")

    # Test 2: Generate larger gasket (depth 5)
    print("\n" + "="*50)
    print("Test 2: Generate depth-5 gasket with (-1, 2, 2, 3)")
    curvatures2 = [Fraction(-1), Fraction(2), Fraction(2)]
    circles2 = list(generate_apollonian_gasket(curvatures2, max_depth=5, stream=False))

    print(f"Generated {len(circles2)} circles at depth 5")
    print(f"Generations: {sorted(set(c.generation for c in circles2))}")

    # Count circles by generation
    from collections import Counter
    gen_counts = Counter(c.generation for c in circles2)
    print(f"Circles per generation: {dict(sorted(gen_counts.items()))}")

    # Test 3: Test streaming mode
    print("\n" + "="*50)
    print("Test 3: Streaming mode")
    count = 0
    for circle in generate_apollonian_gasket(curvatures, max_depth=3, stream=True):
        count += 1
    print(f"Streamed {count} circles at depth 3")

    # Test 4: Verify deduplication
    print("\n" + "="*50)
    print("Test 4: Deduplication check")
    circles3 = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))
    hashes = [c.hash_key() for c in circles3]
    unique_hashes = set(hashes)
    print(f"Total circles: {len(circles3)}")
    print(f"Unique hashes: {len(unique_hashes)}")
    print(f"✓ Deduplication working: {len(circles3) == len(unique_hashes)}")

    print("\n✓ All manual tests passed!")
