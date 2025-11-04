"""
Unit tests for exact_math.py hybrid exact arithmetic system.

Reference: .DESIGN_SPEC.md Section 8.4
Target: 80+ tests with 100% coverage

Test Organization:
- TestTypeDetection: 20 tests for is_sympy_integer, is_sympy_rational, sympy_to_exact
- TestArithmeticOperations: 30 tests for smart_add, smart_multiply, smart_divide, smart_sqrt, smart_power, smart_abs
- TestConversionFunctions: 20 tests for to_sympy, to_string, format_exact, parse_exact, to_numerator_denominator, to_fraction_lossy
- TestComplexOperations: 15 tests for complex number operations
- TestEdgeCases: 15+ tests for edge cases and error handling
"""

import pytest
from fractions import Fraction
import sympy as sp
from sympy import sqrt, Rational, I, simplify

from core.exact_math import (
    # Type detection
    is_sympy_integer,
    is_sympy_rational,
    sympy_to_exact,
    # Arithmetic operations
    smart_add,
    smart_multiply,
    smart_divide,
    smart_sqrt,
    smart_power,
    smart_abs,
    # Complex operations
    smart_complex_multiply,
    smart_complex_divide,
    smart_complex_conjugate,
    smart_complex_sqrt,
    smart_real,
    smart_imag,
    smart_abs_squared,
    # Conversion functions
    to_sympy,
    to_string,
    format_exact,
    parse_exact,
    to_numerator_denominator,
    to_fraction_lossy,
)


class TestTypeDetection:
    """Tests for type detection functions (20 tests)."""

    # is_sympy_integer tests (7 tests)
    def test_is_sympy_integer_with_integer(self):
        """Test that sp.Integer(5) is detected as integer."""
        assert is_sympy_integer(sp.Integer(5)) is True

    def test_is_sympy_integer_with_rational_integer(self):
        """Test that sp.Rational(6, 1) is detected as integer."""
        assert is_sympy_integer(sp.Rational(6, 1)) is True

    def test_is_sympy_integer_with_fraction(self):
        """Test that sp.Rational(3, 2) is NOT detected as integer."""
        assert is_sympy_integer(sp.Rational(3, 2)) is False

    def test_is_sympy_integer_with_irrational(self):
        """Test that sqrt(2) is NOT detected as integer."""
        assert is_sympy_integer(sqrt(2)) is False

    def test_is_sympy_integer_with_simplified_integer(self):
        """Test that sqrt(4) simplifies to 2 and is detected as integer."""
        assert is_sympy_integer(sqrt(4)) is True

    def test_is_sympy_integer_with_zero(self):
        """Test that zero is detected as integer."""
        assert is_sympy_integer(sp.Integer(0)) is True

    def test_is_sympy_integer_with_negative(self):
        """Test that negative integers are detected."""
        assert is_sympy_integer(sp.Integer(-5)) is True

    # is_sympy_rational tests (7 tests)
    def test_is_sympy_rational_with_integer(self):
        """Test that sp.Integer(5) is rational."""
        assert is_sympy_rational(sp.Integer(5)) is True

    def test_is_sympy_rational_with_fraction(self):
        """Test that sp.Rational(3, 2) is rational."""
        assert is_sympy_rational(sp.Rational(3, 2)) is True

    def test_is_sympy_rational_with_irrational_sqrt(self):
        """Test that sqrt(2) is NOT rational."""
        assert is_sympy_rational(sqrt(2)) is False

    def test_is_sympy_rational_with_simplified_rational(self):
        """Test that sqrt(4) / 2 simplifies to 1 (rational)."""
        expr = sqrt(4) / sp.Integer(2)
        assert is_sympy_rational(expr) is True

    def test_is_sympy_rational_with_complex_irrational(self):
        """Test that sqrt(2) + sqrt(3) is NOT rational."""
        expr = sqrt(2) + sqrt(3)
        assert is_sympy_rational(expr) is False

    def test_is_sympy_rational_with_zero(self):
        """Test that zero is rational."""
        assert is_sympy_rational(sp.Integer(0)) is True

    def test_is_sympy_rational_with_negative_fraction(self):
        """Test that negative fractions are rational."""
        assert is_sympy_rational(sp.Rational(-3, 4)) is True

    # sympy_to_exact tests (6 tests)
    def test_sympy_to_exact_integer(self):
        """Test conversion of sp.Integer(5) to int."""
        result = sympy_to_exact(sp.Integer(5))
        assert result == 5
        assert isinstance(result, int)

    def test_sympy_to_exact_rational(self):
        """Test conversion of sp.Rational(3, 2) to Fraction."""
        result = sympy_to_exact(sp.Rational(3, 2))
        assert result == Fraction(3, 2)
        assert isinstance(result, Fraction)

    def test_sympy_to_exact_irrational(self):
        """Test that sqrt(2) remains as SymPy expression."""
        result = sympy_to_exact(sqrt(2))
        assert isinstance(result, sp.Expr)
        assert result == sqrt(2)

    def test_sympy_to_exact_simplified_integer(self):
        """Test that sqrt(4) converts to int 2."""
        result = sympy_to_exact(sqrt(4))
        assert result == 2
        assert isinstance(result, int)

    def test_sympy_to_exact_zero(self):
        """Test that zero converts to int."""
        result = sympy_to_exact(sp.Integer(0))
        assert result == 0
        assert isinstance(result, int)

    def test_sympy_to_exact_negative_rational(self):
        """Test conversion of negative fraction."""
        result = sympy_to_exact(sp.Rational(-5, 3))
        assert result == Fraction(-5, 3)
        assert isinstance(result, Fraction)


class TestArithmeticOperations:
    """Tests for arithmetic operation functions (30 tests)."""

    # smart_add tests (6 tests)
    def test_smart_add_two_ints(self):
        """Test adding two integers returns int."""
        result = smart_add(3, 5)
        assert result == 8
        assert isinstance(result, int)

    def test_smart_add_int_and_fraction(self):
        """Test adding int and Fraction."""
        result = smart_add(3, Fraction(1, 2))
        assert result == Fraction(7, 2)
        assert isinstance(result, Fraction)

    def test_smart_add_two_fractions_to_int(self):
        """Test adding two fractions that sum to integer."""
        result = smart_add(Fraction(3, 2), Fraction(1, 2))
        assert result == 2
        assert isinstance(result, int)

    def test_smart_add_int_and_irrational(self):
        """Test adding int and sqrt(2)."""
        result = smart_add(3, sqrt(2))
        assert isinstance(result, sp.Expr)
        assert simplify(result - (3 + sqrt(2))) == 0

    def test_smart_add_two_irrationals_to_rational(self):
        """Test adding sqrt(2) + (-sqrt(2)) = 0."""
        result = smart_add(sqrt(2), -sqrt(2))
        assert result == 0
        assert isinstance(result, int)

    def test_smart_add_negative_numbers(self):
        """Test adding negative numbers."""
        result = smart_add(-5, -3)
        assert result == -8
        assert isinstance(result, int)

    # smart_multiply tests (6 tests)
    def test_smart_multiply_two_ints(self):
        """Test multiplying two integers."""
        result = smart_multiply(3, 5)
        assert result == 15
        assert isinstance(result, int)

    def test_smart_multiply_int_and_fraction(self):
        """Test multiplying int and Fraction."""
        result = smart_multiply(4, Fraction(3, 2))
        assert result == 6
        assert isinstance(result, int)

    def test_smart_multiply_two_fractions(self):
        """Test multiplying two fractions."""
        result = smart_multiply(Fraction(2, 3), Fraction(3, 4))
        assert result == Fraction(1, 2)
        assert isinstance(result, Fraction)

    def test_smart_multiply_fraction_and_irrational(self):
        """Test multiplying Fraction and sqrt(2)."""
        result = smart_multiply(Fraction(3, 2), sqrt(2))
        assert isinstance(result, sp.Expr)
        assert simplify(result - (Rational(3, 2) * sqrt(2))) == 0

    def test_smart_multiply_two_irrationals_to_rational(self):
        """Test sqrt(2) * sqrt(2) = 2."""
        result = smart_multiply(sqrt(2), sqrt(2))
        assert result == 2
        assert isinstance(result, int)

    def test_smart_multiply_by_zero(self):
        """Test multiplication by zero."""
        result = smart_multiply(0, sqrt(2))
        assert result == 0
        assert isinstance(result, int)

    # smart_divide tests (6 tests)
    def test_smart_divide_exact_int_division(self):
        """Test exact integer division."""
        result = smart_divide(10, 2)
        assert result == 5
        assert isinstance(result, int)

    def test_smart_divide_int_to_fraction(self):
        """Test int division resulting in fraction."""
        result = smart_divide(3, 2)
        assert result == Fraction(3, 2)
        assert isinstance(result, Fraction)

    def test_smart_divide_fractions_to_int(self):
        """Test fraction division resulting in int."""
        result = smart_divide(Fraction(3, 2), Fraction(3, 4))
        assert result == 2
        assert isinstance(result, int)

    def test_smart_divide_fractions(self):
        """Test division of two fractions."""
        result = smart_divide(Fraction(2, 3), Fraction(4, 5))
        assert result == Fraction(5, 6)
        assert isinstance(result, Fraction)

    def test_smart_divide_int_by_irrational(self):
        """Test dividing int by sqrt(2)."""
        result = smart_divide(6, sqrt(2))
        assert isinstance(result, sp.Expr)
        # 6 / sqrt(2) = 6 * sqrt(2) / 2 = 3 * sqrt(2)
        expected = 3 * sqrt(2)
        assert simplify(result - expected) == 0

    def test_smart_divide_irrationals_to_rational(self):
        """Test sqrt(8) / sqrt(2) = 2."""
        result = smart_divide(sqrt(8), sqrt(2))
        assert result == 2
        assert isinstance(result, int)

    # smart_sqrt tests (6 tests)
    def test_smart_sqrt_perfect_square_int(self):
        """Test sqrt of perfect square returns int."""
        result = smart_sqrt(16)
        assert result == 4
        assert isinstance(result, int)

    def test_smart_sqrt_non_perfect_square_int(self):
        """Test sqrt of non-perfect square returns SymPy expression."""
        result = smart_sqrt(2)
        assert isinstance(result, sp.Expr)
        assert result == sqrt(2)

    def test_smart_sqrt_fraction_perfect_square(self):
        """Test sqrt(Fraction(9, 4)) = Fraction(3, 2)."""
        result = smart_sqrt(Fraction(9, 4))
        assert result == Fraction(3, 2)
        assert isinstance(result, Fraction)

    def test_smart_sqrt_fraction_non_perfect(self):
        """Test sqrt of non-perfect fraction."""
        result = smart_sqrt(Fraction(1, 2))
        assert isinstance(result, sp.Expr)
        assert simplify(result - sqrt(Rational(1, 2))) == 0

    def test_smart_sqrt_zero(self):
        """Test sqrt(0) = 0."""
        result = smart_sqrt(0)
        assert result == 0
        assert isinstance(result, int)

    def test_smart_sqrt_sympy_expr(self):
        """Test sqrt(sqrt(256)) = 4."""
        result = smart_sqrt(sqrt(256))
        assert result == 4
        assert isinstance(result, int)

    # smart_power tests (3 tests)
    def test_smart_power_int_base_int_exp(self):
        """Test 2^3 = 8."""
        result = smart_power(2, 3)
        assert result == 8
        assert isinstance(result, int)

    def test_smart_power_fraction_to_int(self):
        """Test (1/2)^2 = 1/4."""
        result = smart_power(Fraction(1, 2), 2)
        assert result == Fraction(1, 4)
        assert isinstance(result, Fraction)

    def test_smart_power_irrational_base(self):
        """Test (sqrt(2))^2 = 2."""
        result = smart_power(sqrt(2), 2)
        assert result == 2
        assert isinstance(result, int)

    # smart_abs tests (3 tests)
    def test_smart_abs_positive_int(self):
        """Test abs(5) = 5."""
        result = smart_abs(5)
        assert result == 5
        assert isinstance(result, int)

    def test_smart_abs_negative_int(self):
        """Test abs(-5) = 5."""
        result = smart_abs(-5)
        assert result == 5
        assert isinstance(result, int)

    def test_smart_abs_irrational(self):
        """Test abs(-sqrt(2)) = sqrt(2)."""
        result = smart_abs(-sqrt(2))
        assert isinstance(result, sp.Expr)
        assert result == sqrt(2)


class TestComplexOperations:
    """Tests for complex number operations (15 tests)."""

    # smart_complex_multiply tests (3 tests)
    def test_complex_multiply_two_tuples(self):
        """Test (3 + 2i) * (1 + 4i) = -5 + 14i."""
        result = smart_complex_multiply((3, 2), (1, 4))
        real, imag = result
        assert real == -5
        assert imag == 14

    def test_complex_multiply_with_zero_imaginary(self):
        """Test (5 + 0i) * (2 + 3i) = 10 + 15i."""
        result = smart_complex_multiply((5, 0), (2, 3))
        real, imag = result
        assert real == 10
        assert imag == 15

    def test_complex_multiply_with_fractions(self):
        """Test complex multiplication with fractions."""
        result = smart_complex_multiply(
            (Fraction(1, 2), Fraction(1, 3)),
            (Fraction(2, 1), Fraction(3, 1))
        )
        real, imag = result
        # (1/2 + 1/3*i) * (2 + 3*i) = (1/2*2 - 1/3*3) + (1/2*3 + 1/3*2)*i
        # = (1 - 1) + (3/2 + 2/3)*i = 0 + 13/6*i
        assert real == 0
        assert imag == Fraction(13, 6)

    # smart_complex_divide tests (2 tests)
    def test_complex_divide_integers(self):
        """Test (10 + 5i) / (2 + i) = 5."""
        result = smart_complex_divide((10, 5), (2, 1))
        real, imag = result
        # (10 + 5i) / (2 + i) = (10*2 + 5*1)/(2^2+1^2) + (5*2 - 10*1)/(2^2+1^2)*i
        # = 25/5 + 0/5*i = 5 + 0i
        assert real == 5
        assert imag == 0

    def test_complex_divide_to_fraction(self):
        """Test complex division resulting in fractions."""
        result = smart_complex_divide((1, 1), (2, 0))
        real, imag = result
        assert real == Fraction(1, 2)
        assert imag == Fraction(1, 2)

    # smart_complex_conjugate tests (2 tests)
    def test_complex_conjugate_tuple(self):
        """Test conjugate of (3 + 4i) = 3 - 4i."""
        result = smart_complex_conjugate((3, 4))
        real, imag = result
        assert real == 3
        assert imag == -4

    def test_complex_conjugate_with_fraction(self):
        """Test conjugate with fractions."""
        result = smart_complex_conjugate((Fraction(1, 2), Fraction(3, 4)))
        real, imag = result
        assert real == Fraction(1, 2)
        assert imag == Fraction(-3, 4)

    # smart_complex_sqrt tests (2 tests)
    def test_complex_sqrt_real_perfect_square(self):
        """Test sqrt of real perfect square (4 + 0i) = (2 + 0i)."""
        result = smart_complex_sqrt((4, 0))
        real, imag = result
        assert real == 2
        assert imag == 0

    def test_complex_sqrt_negative_real(self):
        """Test sqrt of negative real (-4 + 0i) = (0 + 2i)."""
        result = smart_complex_sqrt((-4, 0))
        real, imag = result
        # sqrt(-4) = 2i
        assert real == 0
        assert imag == 2

    # smart_real, smart_imag tests (4 tests)
    def test_smart_real_from_tuple(self):
        """Test extracting real part from tuple."""
        assert smart_real((3, 4)) == 3

    def test_smart_imag_from_tuple(self):
        """Test extracting imaginary part from tuple."""
        assert smart_imag((3, 4)) == 4

    def test_smart_real_from_sympy(self):
        """Test extracting real part from SymPy expression."""
        expr = sp.Integer(3) + sp.Integer(4) * I
        result = smart_real(expr)
        assert result == 3

    def test_smart_imag_from_sympy(self):
        """Test extracting imaginary part from SymPy expression."""
        expr = sp.Integer(3) + sp.Integer(4) * I
        result = smart_imag(expr)
        assert result == 4

    # smart_abs_squared tests (2 tests)
    def test_abs_squared_tuple(self):
        """Test |3 + 4i|^2 = 25."""
        result = smart_abs_squared((3, 4))
        assert result == 25
        assert isinstance(result, int)

    def test_abs_squared_with_fractions(self):
        """Test abs squared with fractions."""
        result = smart_abs_squared((Fraction(3, 2), Fraction(4, 3)))
        # (3/2)^2 + (4/3)^2 = 9/4 + 16/9 = (81 + 64) / 36 = 145/36
        assert result == Fraction(145, 36)


class TestConversionFunctions:
    """Tests for conversion functions (20 tests)."""

    # to_sympy tests (4 tests)
    def test_to_sympy_from_int(self):
        """Test converting int to SymPy."""
        result = to_sympy(5)
        assert result == sp.Integer(5)
        assert isinstance(result, sp.Integer)

    def test_to_sympy_from_fraction(self):
        """Test converting Fraction to SymPy."""
        result = to_sympy(Fraction(3, 2))
        assert result == sp.Rational(3, 2)
        assert isinstance(result, sp.Rational)

    def test_to_sympy_from_sympy(self):
        """Test converting SymPy expression (no-op)."""
        expr = sqrt(2)
        result = to_sympy(expr)
        assert result == expr

    def test_to_sympy_from_float(self):
        """Test converting float to SymPy."""
        result = to_sympy(3.14)
        assert isinstance(result, sp.Float)

    # to_string tests (4 tests)
    def test_to_string_from_int(self):
        """Test converting int to string."""
        assert to_string(5) == "5"

    def test_to_string_from_fraction(self):
        """Test converting Fraction to string."""
        assert to_string(Fraction(3, 2)) == "3/2"

    def test_to_string_from_sympy(self):
        """Test converting SymPy to string."""
        result = to_string(sqrt(2))
        assert "sqrt(2)" in result or "√2" in result or "2**(1/2)" in result

    def test_to_string_negative_fraction(self):
        """Test converting negative fraction to string."""
        assert to_string(Fraction(-3, 4)) == "-3/4"

    # format_exact tests (4 tests)
    def test_format_exact_int(self):
        """Test formatting int as tagged string."""
        assert format_exact(6) == "int:6"

    def test_format_exact_fraction(self):
        """Test formatting Fraction as tagged string."""
        assert format_exact(Fraction(3, 2)) == "frac:3/2"

    def test_format_exact_sympy(self):
        """Test formatting SymPy as tagged string."""
        result = format_exact(sqrt(2))
        assert result.startswith("sym:")
        assert "sqrt(2)" in result or "2**(1/2)" in result

    def test_format_exact_negative_int(self):
        """Test formatting negative int."""
        assert format_exact(-5) == "int:-5"

    # parse_exact tests (4 tests)
    def test_parse_exact_int(self):
        """Test parsing 'int:6' to int."""
        result = parse_exact("int:6")
        assert result == 6
        assert isinstance(result, int)

    def test_parse_exact_fraction(self):
        """Test parsing 'frac:3/2' to Fraction."""
        result = parse_exact("frac:3/2")
        assert result == Fraction(3, 2)
        assert isinstance(result, Fraction)

    def test_parse_exact_sympy(self):
        """Test parsing 'sym:sqrt(2)' to SymPy."""
        result = parse_exact("sym:sqrt(2)")
        assert isinstance(result, sp.Expr)
        assert simplify(result - sqrt(2)) == 0

    def test_parse_exact_negative_fraction(self):
        """Test parsing negative fraction."""
        result = parse_exact("frac:-3/4")
        assert result == Fraction(-3, 4)

    # to_numerator_denominator tests (2 tests)
    def test_to_numerator_denominator_int(self):
        """Test converting int to (num, denom)."""
        num, denom = to_numerator_denominator(5)
        assert num == 5
        assert denom == 1

    def test_to_numerator_denominator_fraction(self):
        """Test converting Fraction to (num, denom)."""
        num, denom = to_numerator_denominator(Fraction(3, 2))
        assert num == 3
        assert denom == 2

    # to_fraction_lossy tests (2 tests)
    def test_to_fraction_lossy_int(self):
        """Test converting int to Fraction."""
        result = to_fraction_lossy(5)
        assert result == Fraction(5, 1)

    def test_to_fraction_lossy_fraction(self):
        """Test converting Fraction (no-op)."""
        frac = Fraction(3, 2)
        result = to_fraction_lossy(frac)
        assert result == frac


class TestEdgeCases:
    """Tests for edge cases and error handling (15 tests)."""

    # Zero handling (3 tests)
    def test_add_zero_to_irrational(self):
        """Test 0 + sqrt(2) = sqrt(2)."""
        result = smart_add(0, sqrt(2))
        assert isinstance(result, sp.Expr)
        assert simplify(result - sqrt(2)) == 0

    def test_multiply_zero_by_irrational(self):
        """Test 0 * sqrt(2) = 0."""
        result = smart_multiply(0, sqrt(2))
        assert result == 0
        assert isinstance(result, int)

    def test_sqrt_of_zero(self):
        """Test sqrt(0) = 0."""
        result = smart_sqrt(0)
        assert result == 0
        assert isinstance(result, int)

    # Large numbers (3 tests)
    def test_large_int_arithmetic(self):
        """Test arithmetic with large integers."""
        large = 10**15
        result = smart_add(large, large)
        assert result == 2 * large
        assert isinstance(result, int)

    def test_large_fraction_multiplication(self):
        """Test multiplication with large fractions."""
        frac = Fraction(10**9, 10**9 + 1)
        result = smart_multiply(frac, frac)
        assert isinstance(result, Fraction)

    def test_large_power(self):
        """Test 2^10 = 1024."""
        result = smart_power(2, 10)
        assert result == 1024
        assert isinstance(result, int)

    # Negative numbers (3 tests)
    def test_negative_int_operations(self):
        """Test operations with negative integers."""
        result = smart_multiply(-3, -4)
        assert result == 12

    def test_negative_fraction_division(self):
        """Test division with negative fractions."""
        result = smart_divide(Fraction(-3, 2), Fraction(1, 2))
        assert result == -3
        assert isinstance(result, int)

    def test_sqrt_negative_returns_imaginary(self):
        """Test sqrt(-4) returns complex/imaginary result."""
        # Note: smart_sqrt works with real numbers only
        # For negative, it would create SymPy expression with I
        result = smart_sqrt(-4)
        assert isinstance(result, sp.Expr)

    # Nested operations (3 tests)
    def test_nested_sqrt(self):
        """Test sqrt(sqrt(256)) = 4."""
        inner = smart_sqrt(256)
        result = smart_sqrt(inner)
        assert result == 4
        assert isinstance(result, int)

    def test_nested_fraction_operations(self):
        """Test ((1/2) + (1/3)) * 6 = 5."""
        sum_result = smart_add(Fraction(1, 2), Fraction(1, 3))
        final = smart_multiply(sum_result, 6)
        assert final == 5
        assert isinstance(final, int)

    def test_complex_nested_expression(self):
        """Test (sqrt(2) * sqrt(2)) + 3 = 5."""
        mult = smart_multiply(sqrt(2), sqrt(2))
        result = smart_add(mult, 3)
        assert result == 5
        assert isinstance(result, int)

    # Error handling (3 tests)
    def test_parse_exact_invalid_tag(self):
        """Test parsing with invalid tag raises error."""
        with pytest.raises(ValueError, match="Unknown exact format"):
            parse_exact("invalid:123")

    def test_parse_exact_malformed_fraction(self):
        """Test parsing malformed fraction raises error."""
        with pytest.raises(ValueError, match="Invalid fraction format"):
            parse_exact("frac:3/2/1")

    def test_format_exact_unsupported_type(self):
        """Test formatting unsupported type raises error."""
        with pytest.raises(TypeError, match="Cannot format"):
            format_exact(3.14)  # float not supported


# Test that round-trip conversions work correctly
class TestRoundTripConversions:
    """Tests for round-trip conversions (5 tests)."""

    def test_roundtrip_int(self):
        """Test int -> format -> parse -> int."""
        original = 42
        formatted = format_exact(original)
        parsed = parse_exact(formatted)
        assert parsed == original
        assert isinstance(parsed, int)

    def test_roundtrip_fraction(self):
        """Test Fraction -> format -> parse -> Fraction."""
        original = Fraction(7, 13)
        formatted = format_exact(original)
        parsed = parse_exact(formatted)
        assert parsed == original
        assert isinstance(parsed, Fraction)

    def test_roundtrip_sympy(self):
        """Test SymPy -> format -> parse -> SymPy."""
        original = sqrt(2) + sqrt(3)
        formatted = format_exact(original)
        parsed = parse_exact(formatted)
        assert simplify(parsed - original) == 0

    def test_roundtrip_negative_int(self):
        """Test negative int round-trip."""
        original = -99
        formatted = format_exact(original)
        parsed = parse_exact(formatted)
        assert parsed == original
        assert isinstance(parsed, int)

    def test_roundtrip_negative_fraction(self):
        """Test negative fraction round-trip."""
        original = Fraction(-5, 7)
        formatted = format_exact(original)
        parsed = parse_exact(formatted)
        assert parsed == original
        assert isinstance(parsed, Fraction)
