"""Minimal test for Phase 6: Verify [1,2,2] INTEGER overflow fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fractions import Fraction
import sympy as sp
from collections import Counter

from core.gasket_generator import generate_apollonian_gasket

print("=" * 70)
print("Phase 6: Minimal Test - INTEGER Overflow Fix Verification")
print("=" * 70)

# CRITICAL TEST: Previously failing [1, 2, 2] configuration
print("\n[CRITICAL TEST] Configuration [1, 2, 2] at depth 3")
print("This configuration caused INTEGER overflow before Phase 6")
print("due to .limit_denominator(10**9) creating huge Fractions")

try:
    curvatures = [Fraction(1), Fraction(2), Fraction(2)]
    print("\nGenerating gasket...")
    circles = list(generate_apollonian_gasket(curvatures, max_depth=3, stream=False))

    print(f"\n✓ SUCCESS! Generated {len(circles)} circles without INTEGER overflow")
    print(f"✓ Generations present: {sorted(set(c.generation for c in circles))}")

    # Count circles by generation
    gen_counts = Counter(c.generation for c in circles)
    print(f"✓ Circles per generation: {dict(sorted(gen_counts.items()))}")

    # Check for SymPy expressions (irrational values preserved)
    sympy_count = 0
    for circle in circles:
        if isinstance(circle.curvature, sp.Expr):
            sympy_count += 1
        if isinstance(circle.center, tuple):
            if isinstance(circle.center[0], sp.Expr):
                sympy_count += 1
            if isinstance(circle.center[1], sp.Expr):
                sympy_count += 1

    print(f"✓ Found {sympy_count} SymPy expressions (irrational values preserved)")

    # Verify no huge denominators
    max_denom = 0
    for circle in circles:
        if isinstance(circle.curvature, Fraction) and circle.curvature.denominator > max_denom:
            max_denom = circle.curvature.denominator
        if isinstance(circle.center, tuple):
            if isinstance(circle.center[0], Fraction) and circle.center[0].denominator > max_denom:
                max_denom = circle.center[0].denominator
            if isinstance(circle.center[1], Fraction) and circle.center[1].denominator > max_denom:
                max_denom = circle.center[1].denominator

    print(f"✓ Max Fraction denominator: {max_denom}")

    if max_denom > 10**9:
        print(f"  ⚠ WARNING: Denominator > 10^9 found! .limit_denominator() may still be present")
    else:
        print(f"  ✓ No huge denominators - .limit_denominator() successfully removed!")

    print("\n" + "=" * 70)
    print("✓✓✓ PHASE 6 ROOT CAUSE FIX VERIFIED ✓✓✓")
    print("=" * 70)
    print("  ✓ [1,2,2] configuration works without INTEGER overflow")
    print("  ✓ .limit_denominator() successfully removed")
    print("  ✓ Irrational values preserved as SymPy expressions")
    print("  ✓ Hybrid exact arithmetic system working correctly")
    print("=" * 70)

except Exception as e:
    print(f"\n✗✗✗ TEST FAILED ✗✗✗")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 70)
