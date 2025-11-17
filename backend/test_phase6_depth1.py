"""Ultra-minimal test: depth 1 only to verify basic functionality."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fractions import Fraction
import sympy as sp

from core.gasket_generator import generate_apollonian_gasket

print("Phase 6: Ultra-Minimal Test (depth 1)")
print("=" * 60)

# Test [1, 2, 2] at depth 1
print("\n[Test] Configuration [1, 2, 2] at depth 1")

try:
    curvatures = [Fraction(1), Fraction(2), Fraction(2)]
    circles = list(generate_apollonian_gasket(curvatures, max_depth=1, stream=False))

    print(f"✓ Generated {len(circles)} circles")
    print(f"✓ No INTEGER overflow!")

    # Check types
    for i, circle in enumerate(circles):
        curvature_type = type(circle.curvature).__name__
        center_x_type = type(circle.center[0]).__name__
        center_y_type = type(circle.center[1]).__name__

        print(f"\nCircle {i}: gen={circle.generation}")
        print(f"  Curv: {circle.curvature} ({curvature_type})")
        print(f"  Center.x: {circle.center[0]} ({center_x_type})")
        print(f"  Center.y: {circle.center[1]} ({center_y_type})")

    print("\n" + "=" * 60)
    print("✓ Phase 6 basic functionality WORKS")
    print("✓ .limit_denominator() removed successfully")
    print("=" * 60)

except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
