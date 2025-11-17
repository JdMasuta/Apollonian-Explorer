"""Test suite for Phase 9: Circle Model with Hybrid Properties for ExactNumber.

This test verifies:
1. parse_exact() method correctly parses int, Fraction, and SymPy types
2. Hybrid properties return correct ExactNumber types from TEXT columns
3. Fallback to INTEGER columns when TEXT columns are NULL
4. Backward compatibility with existing Fraction-based properties
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fractions import Fraction
import sympy as sp

from db.models.circle import Circle

print("=" * 70)
print("Phase 9: Circle Model Hybrid Properties Test Suite")
print("=" * 70)

# Test 1: parse_exact() Method - Integer Type
print("\n[Test 1] parse_exact() with integer type")
result = Circle.parse_exact("int:6")
print(f"  Input: 'int:6'")
print(f"  Output: {result} (type: {type(result).__name__})")
assert result == 6, f"Expected 6, got {result}"
assert isinstance(result, int), f"Expected int type, got {type(result).__name__}"
print("  ✓ Integer parsing test passed")

# Test 2: parse_exact() Method - Fraction Type
print("\n[Test 2] parse_exact() with Fraction type")
result = Circle.parse_exact("frac:3/2")
print(f"  Input: 'frac:3/2'")
print(f"  Output: {result} (type: {type(result).__name__})")
assert result == Fraction(3, 2), f"Expected Fraction(3, 2), got {result}"
assert isinstance(result, Fraction), f"Expected Fraction type, got {type(result).__name__}"
print("  ✓ Fraction parsing test passed")

# Test 3: parse_exact() Method - SymPy Type
print("\n[Test 3] parse_exact() with SymPy type")
result = Circle.parse_exact("sym:sqrt(2)")
print(f"  Input: 'sym:sqrt(2)'")
print(f"  Output: {result} (type: {type(result).__name__})")
expected = sp.sqrt(2)
assert result == expected, f"Expected sqrt(2), got {result}"
assert isinstance(result, sp.Expr), f"Expected SymPy Expr type, got {type(result).__name__}"
print("  ✓ SymPy parsing test passed")

# Test 4: parse_exact() Method - Complex SymPy Expression
print("\n[Test 4] parse_exact() with complex SymPy expression")
result = Circle.parse_exact("sym:5 + 4*sqrt(2)")
print(f"  Input: 'sym:5 + 4*sqrt(2)'")
print(f"  Output: {result} (type: {type(result).__name__})")
expected = 5 + 4*sp.sqrt(2)
assert result == expected, f"Expected 5 + 4*sqrt(2), got {result}"
assert isinstance(result, sp.Expr), f"Expected SymPy Expr type, got {type(result).__name__}"
print("  ✓ Complex SymPy expression parsing test passed")

# Test 5: parse_exact() Method - Error Handling
print("\n[Test 5] parse_exact() error handling")
test_cases = [
    ("", "empty string"),
    ("invalid:6", "unknown format"),
    ("frac:invalid", "invalid fraction"),
    ("frac:3", "missing denominator"),
]

for test_input, description in test_cases:
    try:
        Circle.parse_exact(test_input)
        print(f"  ✗ FAILED: {description} - should have raised ValueError")
        assert False, f"parse_exact('{test_input}') should raise ValueError"
    except ValueError as e:
        print(f"  ✓ {description}: correctly raised ValueError")

print("  ✓ Error handling test passed")

# Test 6: Hybrid Property - curvature_exact_value with Integer
print("\n[Test 6] curvature_exact_value with integer")
circle = Circle()
circle.curvature_num = 6
circle.curvature_denom = 1
circle.curvature_exact = "int:6"

result = circle.curvature_exact_value
print(f"  curvature_exact: '{circle.curvature_exact}'")
print(f"  curvature_exact_value: {result} (type: {type(result).__name__})")
assert result == 6, f"Expected 6, got {result}"
assert isinstance(result, int), f"Expected int, got {type(result).__name__}"
print("  ✓ Integer curvature_exact_value test passed")

# Test 7: Hybrid Property - curvature_exact_value with Fraction
print("\n[Test 7] curvature_exact_value with Fraction")
circle = Circle()
circle.curvature_num = 3
circle.curvature_denom = 2
circle.curvature_exact = "frac:3/2"

result = circle.curvature_exact_value
print(f"  curvature_exact: '{circle.curvature_exact}'")
print(f"  curvature_exact_value: {result} (type: {type(result).__name__})")
assert result == Fraction(3, 2), f"Expected Fraction(3, 2), got {result}"
assert isinstance(result, Fraction), f"Expected Fraction, got {type(result).__name__}"
print("  ✓ Fraction curvature_exact_value test passed")

# Test 8: Hybrid Property - curvature_exact_value with SymPy
print("\n[Test 8] curvature_exact_value with SymPy")
circle = Circle()
circle.curvature_num = 14142136  # Approximation
circle.curvature_denom = 10000000
circle.curvature_exact = "sym:sqrt(2)"

result = circle.curvature_exact_value
print(f"  curvature_exact: '{circle.curvature_exact}'")
print(f"  curvature_exact_value: {result} (type: {type(result).__name__})")
assert result == sp.sqrt(2), f"Expected sqrt(2), got {result}"
assert isinstance(result, sp.Expr), f"Expected SymPy Expr, got {type(result).__name__}"
print("  ✓ SymPy curvature_exact_value test passed")

# Test 9: Fallback Behavior - NULL TEXT Column
print("\n[Test 9] Fallback to INTEGER columns when TEXT is NULL")
circle = Circle()
circle.curvature_num = 7
circle.curvature_denom = 3
circle.curvature_exact = None  # No exact value

result = circle.curvature_exact_value
print(f"  curvature_exact: {circle.curvature_exact}")
print(f"  curvature_exact_value: {result} (type: {type(result).__name__})")
assert result == Fraction(7, 3), f"Expected Fraction(7, 3), got {result}"
assert isinstance(result, Fraction), f"Expected Fraction, got {type(result).__name__}"
print("  ✓ Fallback behavior test passed")

# Test 10: Backward Compatibility - Legacy curvature Property
print("\n[Test 10] Backward compatibility with legacy curvature property")
circle = Circle()
circle.curvature_num = 5
circle.curvature_denom = 2
circle.curvature_exact = "sym:sqrt(3)"  # Has SymPy in exact column

# Legacy property should always return Fraction from INTEGER columns
legacy_result = circle.curvature
print(f"  Legacy curvature: {legacy_result} (type: {type(legacy_result).__name__})")
assert legacy_result == Fraction(5, 2), f"Expected Fraction(5, 2), got {legacy_result}"
assert isinstance(legacy_result, Fraction), f"Expected Fraction, got {type(legacy_result).__name__}"

# Exact property should return SymPy from TEXT column
exact_result = circle.curvature_exact_value
print(f"  Exact curvature_exact_value: {exact_result} (type: {type(exact_result).__name__})")
assert exact_result == sp.sqrt(3), f"Expected sqrt(3), got {exact_result}"
assert isinstance(exact_result, sp.Expr), f"Expected SymPy Expr, got {type(exact_result).__name__}"

print("  ✓ Backward compatibility test passed")

# Test 11: All Coordinates - center_x_exact_value
print("\n[Test 11] center_x_exact_value property")
circle = Circle()
circle.center_x_num = 7
circle.center_x_denom = 6
circle.center_x_exact = "frac:7/6"

result = circle.center_x_exact_value
print(f"  center_x_exact_value: {result} (type: {type(result).__name__})")
assert result == Fraction(7, 6), f"Expected Fraction(7, 6), got {result}"
print("  ✓ center_x_exact_value test passed")

# Test 12: All Coordinates - center_y_exact_value with SymPy
print("\n[Test 12] center_y_exact_value with SymPy expression")
circle = Circle()
circle.center_y_num = 9428090  # Approximation
circle.center_y_denom = 10000000
circle.center_y_exact = "sym:2*sqrt(2)/3"

result = circle.center_y_exact_value
print(f"  center_y_exact_value: {result} (type: {type(result).__name__})")
expected = 2*sp.sqrt(2)/3
assert result == expected, f"Expected 2*sqrt(2)/3, got {result}"
print("  ✓ center_y_exact_value with SymPy test passed")

# Test 13: All Coordinates - radius_exact_value
print("\n[Test 13] radius_exact_value property")
circle = Circle()
circle.radius_num = 1
circle.radius_denom = 1
circle.radius_exact = "int:1"

result = circle.radius_exact_value
print(f"  radius_exact_value: {result} (type: {type(result).__name__})")
assert result == 1, f"Expected 1, got {result}"
assert isinstance(result, int), f"Expected int, got {type(result).__name__}"
print("  ✓ radius_exact_value test passed")

# Test 14: Mixed Types in Single Circle
print("\n[Test 14] Circle with mixed ExactNumber types")
circle = Circle()

# Curvature: int
circle.curvature_num = 5
circle.curvature_denom = 1
circle.curvature_exact = "int:5"

# Center X: Fraction
circle.center_x_num = 3
circle.center_x_denom = 2
circle.center_x_exact = "frac:3/2"

# Center Y: SymPy
circle.center_y_num = 14142136
circle.center_y_denom = 10000000
circle.center_y_exact = "sym:sqrt(2)"

# Radius: Fraction
circle.radius_num = 1
circle.radius_denom = 5
circle.radius_exact = "frac:1/5"

print(f"  curvature: {circle.curvature_exact_value} ({type(circle.curvature_exact_value).__name__})")
print(f"  center_x: {circle.center_x_exact_value} ({type(circle.center_x_exact_value).__name__})")
print(f"  center_y: {circle.center_y_exact_value} ({type(circle.center_y_exact_value).__name__})")
print(f"  radius: {circle.radius_exact_value} ({type(circle.radius_exact_value).__name__})")

assert isinstance(circle.curvature_exact_value, int)
assert isinstance(circle.center_x_exact_value, Fraction)
assert isinstance(circle.center_y_exact_value, sp.Expr)
assert isinstance(circle.radius_exact_value, Fraction)

print("  ✓ Mixed types test passed")

# Summary
print("\n" + "=" * 70)
print("✓ ALL PHASE 9 TESTS PASSED!")
print("=" * 70)
print("Summary:")
print("  ✓ parse_exact() correctly parses int, Fraction, and SymPy types")
print("  ✓ Hybrid properties return correct ExactNumber types")
print("  ✓ Fallback to INTEGER columns when TEXT is NULL")
print("  ✓ Backward compatibility maintained (legacy properties work)")
print("  ✓ All coordinate properties (curvature, center_x, center_y, radius)")
print("  ✓ Mixed ExactNumber types in single Circle")
print("  ✓ Error handling for invalid input")
print("=" * 70)
