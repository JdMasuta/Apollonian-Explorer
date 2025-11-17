"""Debug tangency verification issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fractions import Fraction
import sympy as sp

from core.gasket_generator import _initialize_three_circles, _compute_tangent_distance, verify_tangency
from core.circle_data import CircleData

print("=" * 70)
print("Debug Tangency Verification")
print("=" * 70)

# Test [1, 2, 2] configuration
print("\n[Test] Initializing three circles with curvatures [1, 2, 2]")

curvatures = [Fraction(1), Fraction(2), Fraction(2)]

try:
    circles = _initialize_three_circles(curvatures)
    print(f"✓ Successfully initialized {len(circles)} circles")

    for i, circle in enumerate(circles):
        print(f"\nCircle {i+1}:")
        print(f"  Curvature: {circle.curvature} (type: {type(circle.curvature).__name__})")
        print(f"  Center: {circle.center}")
        if isinstance(circle.center, tuple):
            print(f"    x: {circle.center[0]} (type: {type(circle.center[0]).__name__})")
            print(f"    y: {circle.center[1]} (type: {type(circle.center[1]).__name__})")

except Exception as e:
    print(f"\n✗ Initialization failed: {e}")

    # Manual initialization to see where it fails
    print("\n--- Manual Step-by-Step Initialization ---")

    k1, k2, k3 = curvatures

    # Circle 1: at origin (but moved to (1, 0) as per the code)
    c1_pos = (Fraction(1), Fraction(0))
    c1 = CircleData(curvature=k1, center=c1_pos, generation=0, parent_ids=[])
    print(f"\nCircle 1: k={c1.curvature}, center={c1.center}")

    # Circle 2: on x-axis, tangent to circle 1
    d12 = _compute_tangent_distance(k1, k2)
    print(f"Distance between circles 1 and 2: {d12} (type: {type(d12).__name__})")

    c2_pos = (d12, Fraction(0))
    c2 = CircleData(curvature=k2, center=c2_pos, generation=0, parent_ids=[])
    print(f"Circle 2: k={c2.curvature}, center={c2.center}")

    # Verify tangency between c1 and c2
    print(f"\nVerifying tangency between circles 1 and 2...")
    is_tangent = verify_tangency(c1, c2)
    print(f"  Tangent: {is_tangent}")

    if not is_tangent:
        # Debug the verification
        print("\n  --- Tangency Debug ---")
        x1, y1 = c1.center
        x2, y2 = c2.center

        dx = x2 - x1
        dy = y2 - y1
        distance_squared = dx**2 + dy**2

        print(f"  dx = {dx}")
        print(f"  dy = {dy}")
        print(f"  distance_squared = {distance_squared}")

        if isinstance(distance_squared, sp.Expr):
            actual_distance = float(sp.sqrt(distance_squared))
        else:
            actual_distance = float(distance_squared ** 0.5)

        print(f"  actual_distance = {actual_distance}")

        expected_dist = _compute_tangent_distance(c1.curvature, c2.curvature)
        print(f"  expected_dist = {expected_dist} (type: {type(expected_dist).__name__})")

        if isinstance(expected_dist, sp.Expr):
            expected_distance = float(expected_dist)
        else:
            expected_distance = float(expected_dist)

        print(f"  expected_distance = {expected_distance}")

        error = abs(actual_distance - expected_distance)
        print(f"  error = {error}")
        print(f"  tolerance = 1e-10")
        print(f"  error < tolerance: {error < 1e-10}")

print("\n" + "=" * 70)
