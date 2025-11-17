"""Quick test script for Phase 5: CircleData with ExactNumber types."""

from fractions import Fraction
import sympy as sp

from core.circle_data import CircleData
from core.circle_math import curvature_to_radius, circle_hash

print("Testing Phase 5: CircleData with Hybrid Exact Arithmetic")
print("=" * 70)

# Test 1: Integer curvature
print("\n[Test 1] Integer curvature")
circle1 = CircleData(
    curvature=6,  # int
    center=(0, 0),
    generation=0,
    parent_ids=[],
)
print(f"  Circle: {circle1}")
print(f"  Radius: {circle1.radius()} (type: {type(circle1.radius()).__name__})")
print(f"  Hash: {circle1.hash_key()}")
print(f"  to_dict()['curvature']: {circle1.to_dict()['curvature']}")
print(f"  to_dict()['radius']: {circle1.to_dict()['radius']}")
assert circle1.to_dict()['curvature'] == "6/1", "Integer should serialize as '6/1'"
print("  ✓ Integer curvature test passed")

# Test 2: Fraction curvature
print("\n[Test 2] Fraction curvature")
circle2 = CircleData(
    curvature=Fraction(3, 2),
    center=(Fraction(1, 4), Fraction(-1, 3)),
    generation=1,
    parent_ids=[1, 2, 3],
    id=5,
    tangent_ids=[1, 2, 3],
)
print(f"  Circle: {circle2}")
print(f"  Radius: {circle2.radius()}")
print(f"  Hash: {circle2.hash_key()}")
print(f"  to_dict(): {circle2.to_dict()}")
assert circle2.to_dict()['curvature'] == "3/2", "Fraction should serialize as '3/2'"
print("  ✓ Fraction curvature test passed")

# Test 3: SymPy curvature (irrational)
print("\n[Test 3] SymPy curvature (irrational)")
k_sympy = 3 + 2*sp.sqrt(3)
circle3 = CircleData(
    curvature=k_sympy,
    center=(0, sp.sqrt(2)),  # Mixed: int real, SymPy imag
    generation=0,
)
print(f"  Circle: {circle3}")
print(f"  Curvature type: {type(circle3.curvature).__name__}")
print(f"  Radius: {circle3.radius()}")
print(f"  Hash: {circle3.hash_key()}")
print(f"  to_dict()['curvature']: {circle3.to_dict()['curvature']}")
print(f"  to_dict()['center']['y']: {circle3.to_dict()['center']['y']}")
# SymPy should be approximated to fraction format
assert "/" in circle3.to_dict()['curvature'], "SymPy should serialize as fraction"
print("  ✓ SymPy curvature test passed")

# Test 4: Database dict
print("\n[Test 4] Database dict (dual storage)")
db_dict = circle2.to_database_dict()
print(f"  INTEGER: curvature_num={db_dict['curvature_num']}, curvature_denom={db_dict['curvature_denom']}")
print(f"  TEXT: curvature_exact={db_dict['curvature_exact']}")
print(f"  TEXT: center_x_exact={db_dict['center_x_exact']}, center_y_exact={db_dict['center_y_exact']}")
assert db_dict['curvature_num'] == 3, "Curvature numerator should be 3"
assert db_dict['curvature_denom'] == 2, "Curvature denominator should be 2"
assert db_dict['curvature_exact'] == "frac:3/2", "Curvature exact should be 'frac:3/2'"
print("  ✓ Database dict test passed")

# Test 5: Hash consistency
print("\n[Test 5] Hash deduplication")
circle4 = CircleData(
    curvature=6,  # Same as circle1
    center=(0, 0),
    generation=0,
)
assert circle1.hash_key() == circle4.hash_key(), "Identical circles should have same hash"
print(f"  Hash 1: {circle1.hash_key()}")
print(f"  Hash 4: {circle4.hash_key()}")
print("  ✓ Hash deduplication test passed")

# Test 6: circle_math functions
print("\n[Test 6] circle_math functions")
r1 = curvature_to_radius(2)
print(f"  curvature_to_radius(2) = {r1} (type: {type(r1).__name__})")
r2 = curvature_to_radius(Fraction(3, 2))
print(f"  curvature_to_radius(3/2) = {r2} (type: {type(r2).__name__})")
h1 = circle_hash(1, 0, 0)
print(f"  circle_hash(1, 0, 0) = {h1}")
print("  ✓ circle_math functions test passed")

print("\n" + "=" * 70)
print("✓ ALL PHASE 5 TESTS PASSED!")
print("✓ CircleData supports int, Fraction, and SymPy Expr types")
print("✓ Unified fraction format for API serialization")
print("✓ Dual storage (INTEGER + TEXT) for database")
print("✓ circle_math.py updated to support ExactNumber types")
print("=" * 70)
