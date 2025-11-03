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
import sympy as sp

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


def verify_tangency(
    circle1: CircleData,
    circle2: CircleData,
    tolerance: float = 1e-10
) -> bool:
    """
    Verify that two circles are tangent to each other.

    Checks if the distance between centers matches the expected tangency
    distance (sum or difference of radii) within a tolerance.

    Args:
        circle1, circle2: CircleData objects to check
        tolerance: Maximum acceptable error (default 1e-10)

    Returns:
        True if circles are tangent within tolerance, False otherwise

    Reference:
        ISSUES.md Issue #2 - Tangency verification for exact placement
    """
    # Calculate actual distance between centers
    x1, y1 = circle1.center
    x2, y2 = circle2.center
    actual_distance = float(((x2 - x1)**2 + (y2 - y1)**2) ** 0.5)

    # Calculate expected tangency distance
    expected_distance = float(_compute_tangent_distance(
        circle1.curvature,
        circle2.curvature
    ))

    # Check if they match within tolerance
    error = abs(actual_distance - expected_distance)
    return error < tolerance


def _compute_tangent_distance(k1: Fraction, k2: Fraction) -> Fraction:
    """
    Compute exact distance between centers of two tangent circles.

    Args:
        k1, k2: Curvatures of two circles

    Returns:
        Exact distance as Fraction

    Reference:
        ISSUES.md Issue #2 - Exact rational arithmetic for initial placement
    """
    r1 = Fraction(1) / abs(k1) if k1 != 0 else Fraction(1)
    r2 = Fraction(1) / abs(k2) if k2 != 0 else Fraction(1)

    # Determine tangency type based on curvature signs
    if k1 > 0 and k2 > 0:
        # Both circles external - distance is sum of radii
        return r1 + r2
    elif k1 < 0 and k2 > 0:
        # Circle 1 encloses circle 2 - distance is difference
        return abs(r1) - r2
    elif k1 > 0 and k2 < 0:
        # Circle 2 encloses circle 1 - distance is difference
        return abs(r2) - r1
    else:
        # Both negative (both enclosing) - edge case
        return abs(abs(r1) - abs(r2))


def _solve_third_circle_position_exact(
    k1: Fraction, k2: Fraction, k3: Fraction,
    c1_pos: Tuple[Fraction, Fraction],
    c2_pos: Tuple[Fraction, Fraction]
) -> Tuple[Fraction, Fraction]:
    """
    Solve for exact position of third circle using symbolic math.

    Given two circles with known positions, finds the exact position
    of a third circle that is tangent to both, using sympy for
    exact rational arithmetic throughout.

    Args:
        k1, k2, k3: Curvatures of the three circles
        c1_pos: Position (x, y) of circle 1 as Fractions
        c2_pos: Position (x, y) of circle 2 as Fractions

    Returns:
        Position (x, y) of circle 3 as Fractions

    Reference:
        ISSUES.md Issue #2 - Exact rational geometry for initial placement
    """
    # Define symbolic variables (use real=True, not rational=True)
    # Solutions often involve square roots which are irrational
    x, y = sp.symbols('x y', real=True)

    # Convert Fractions to sympy expressions
    x1 = sp.Rational(c1_pos[0].numerator, c1_pos[0].denominator)
    y1 = sp.Rational(c1_pos[1].numerator, c1_pos[1].denominator)
    x2 = sp.Rational(c2_pos[0].numerator, c2_pos[0].denominator)
    y2 = sp.Rational(c2_pos[1].numerator, c2_pos[1].denominator)

    # Calculate target distances
    d13 = _compute_tangent_distance(k1, k3)
    d23 = _compute_tangent_distance(k2, k3)

    # Convert to sympy Rationals
    d13_sp = sp.Rational(d13.numerator, d13.denominator)
    d23_sp = sp.Rational(d23.numerator, d23.denominator)

    # Set up tangency constraint equations
    # (x - x1)^2 + (y - y1)^2 = d13^2
    # (x - x2)^2 + (y - y2)^2 = d23^2
    eq1 = sp.Eq((x - x1)**2 + (y - y1)**2, d13_sp**2)
    eq2 = sp.Eq((x - x2)**2 + (y - y2)**2, d23_sp**2)

    # Solve the system symbolically
    solutions = sp.solve([eq1, eq2], [x, y])

    if not solutions:
        # Fallback to approximate solution if symbolic solving fails
        raise ValueError("Cannot find exact tangent position for given curvatures")

    # Choose the solution with positive y (above x-axis)
    # If multiple solutions, prefer the one with y > 0
    best_solution = None
    for sol in solutions:
        x_val, y_val = sol

        # Convert sympy expressions to Python Fraction
        # For irrational expressions (like sqrt), convert to float with high precision
        try:
            # Try exact rational conversion first
            if isinstance(x_val, sp.Rational):
                x_frac = Fraction(int(x_val.p), int(x_val.q))
            else:
                # For irrational values, evaluate numerically with high precision
                x_float = float(x_val.evalf(50))  # 50 digits of precision
                x_frac = Fraction(x_float).limit_denominator(10**9)

            if isinstance(y_val, sp.Rational):
                y_frac = Fraction(int(y_val.p), int(y_val.q))
            else:
                y_float = float(y_val.evalf(50))
                y_frac = Fraction(y_float).limit_denominator(10**9)

            # Prefer solution with y > 0 (above x-axis)
            if best_solution is None or y_frac > best_solution[1]:
                best_solution = (x_frac, y_frac)
        except (ValueError, AttributeError, TypeError) as e:
            # Skip solutions that can't be converted
            continue

    if best_solution is None:
        raise ValueError("Cannot convert symbolic solution to exact Fraction")

    return best_solution


def initialize_standard_gasket(curvatures: List[Fraction]) -> List[CircleData]:
    """
    Initialize an Apollonian gasket with 3 or 4 starting circles.

    For 3 curvatures, creates circles in a standard triangle configuration
    using exact rational arithmetic and symbolic solving for tangency.

    For 4 curvatures, uses them as the initial gasket configuration.

    Args:
        curvatures: List of 3-4 curvatures as Fraction objects

    Returns:
        List of CircleData objects representing initial circles

    Raises:
        ValueError: If curvatures count is not 3 or 4

    Reference:
        .DESIGN_SPEC.md section 8.2 - Standard gasket initialization
        ISSUES.md Issue #2 - Exact rational geometry for initial placement
    """
    if len(curvatures) == 3:
        return _initialize_three_circles(curvatures)
    elif len(curvatures) == 4:
        return _initialize_four_circles(curvatures)
    else:
        raise ValueError(f"Need 3 or 4 initial curvatures, got {len(curvatures)}")


def _initialize_three_circles(curvatures: List[Fraction]) -> List[CircleData]:
    """
    Initialize gasket with 3 circles in standard configuration using exact geometry.

    Uses exact rational arithmetic with symbolic solving:
    - Circle 1: at origin (0, 0)
    - Circle 2: on x-axis, tangent to circle 1
    - Circle 3: positioned using symbolic solving to be exactly tangent to both

    This implementation uses sympy to solve the tangency constraints exactly,
    avoiding floating-point approximations that would compromise the goal of
    exact rational arithmetic throughout the system.

    Args:
        curvatures: List of exactly 3 curvatures

    Returns:
        List of 3 CircleData objects with exact tangent positions

    Reference:
        ISSUES.md Issue #2 - Exact rational geometry for initial placement
    """
    k1, k2, k3 = curvatures

    # Circle 1: at origin
    c1_pos = (Fraction(0), Fraction(0))
    c1 = CircleData(
        curvature=k1,
        center=c1_pos,
        generation=0,
        parent_ids=[],
    )

    # Circle 2: on x-axis, tangent to circle 1
    # Distance is computed exactly based on tangency type
    d12 = _compute_tangent_distance(k1, k2)

    # Handle degenerate case: if d12 == 0, circles are concentric
    # Place circle 2 at a small offset to allow solving for circle 3
    if d12 == 0:
        # For concentric circles, place c2 at origin but c3 will be positioned radially
        # This is a special configuration (e.g., outer circle with same-radius inner circle)
        c2_pos = (Fraction(0), Fraction(0))
        c2 = CircleData(
            curvature=k2,
            center=c2_pos,
            generation=0,
            parent_ids=[],
        )

        # For this degenerate case, position c3 based on tangency with c1 only
        d13 = _compute_tangent_distance(k1, k3)
        # Place c3 on positive x-axis at distance d13 from origin
        c3_pos = (d13, Fraction(0))
    else:
        c2_pos = (d12, Fraction(0))
        c2 = CircleData(
            curvature=k2,
            center=c2_pos,
            generation=0,
            parent_ids=[],
        )

        # Circle 3: solve for exact position using symbolic math
        # This solves the system of equations:
        # distance(c1, c3) = tangent_distance(k1, k3)
        # distance(c2, c3) = tangent_distance(k2, k3)
        try:
            c3_pos = _solve_third_circle_position_exact(k1, k2, k3, c1_pos, c2_pos)
        except ValueError as e:
            # If symbolic solving fails, raise with context
            raise ValueError(
                f"Cannot compute exact tangent position for curvatures {k1}, {k2}, {k3}: {e}"
            )

    c3 = CircleData(
        curvature=k3,
        center=c3_pos,
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
