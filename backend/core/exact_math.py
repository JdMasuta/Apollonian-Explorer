"""
Hybrid exact arithmetic system for Apollonian Gasket calculations.

This module intelligently chooses the most efficient exact representation:
- int: For integer results (fastest)
- Fraction: For rational results (medium speed, exact)
- SymPy Expr: For irrational results (slower, but preserves sqrt exactness)

The hybrid approach avoids the performance overhead of using SymPy everywhere
while maintaining exactness throughout all calculations.

Reference: .DESIGN_SPEC.md Section 8.4 - Hybrid Exact Arithmetic System
"""

from fractions import Fraction
from typing import Union, Tuple
import sympy as sp
from sympy import Rational, sqrt, simplify, I, re, im


# ============================================================================
# TYPE SYSTEM
# ============================================================================

# Union type representing any exact number
ExactNumber = Union[int, Fraction, sp.Expr]

# Complex exact number (for circle centers)
ExactComplex = Union[
    Tuple[ExactNumber, ExactNumber],  # (real, imag) tuple
    sp.Expr,  # SymPy complex expression
]


# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================

def is_sympy_integer(expr: sp.Expr) -> bool:
    """
    Check if a SymPy expression simplifies to an integer.

    Algorithm:
    1. Simplify the expression
    2. If Rational: check denominator == 1
    3. If Integer: return True
    4. Else: try numerical evaluation to detect perfect simplifications

    Args:
        expr: SymPy expression

    Returns:
        True if expression is exactly an integer

    Examples:
        >>> is_sympy_integer(sp.Rational(6, 1))
        True
        >>> is_sympy_integer(sp.Rational(3, 2))
        False
        >>> is_sympy_integer(sp.sqrt(4))
        True
        >>> is_sympy_integer(sp.sqrt(2))
        False
    """
    simplified = simplify(expr)

    # Check if it's a Rational with denominator 1
    if isinstance(simplified, sp.Rational):
        return simplified.q == 1

    # Check if it's an Integer
    if isinstance(simplified, sp.Integer):
        return True

    # Try numerical evaluation to detect perfect simplifications
    try:
        val = float(simplified.evalf(100))
        # Check if it's an integer and within reasonable bounds
        if abs(val - round(val)) < 1e-50 and abs(val) < 10**15:
            return True
    except:
        pass

    return False


def is_sympy_rational(expr: sp.Expr) -> bool:
    """
    Check if a SymPy expression is exactly rational (no irrationals like sqrt).

    Algorithm:
    1. Simplify the expression
    2. If Rational or Integer: return True
    3. Check SymPy's .is_rational property
    4. Check for presence of sqrt, Pow, or free symbols

    Args:
        expr: SymPy expression

    Returns:
        True if expression is exactly rational (can be represented as p/q)

    Examples:
        >>> is_sympy_rational(sp.Rational(3, 2))
        True
        >>> is_sympy_rational(sp.sqrt(4))
        True  # Simplifies to 2
        >>> is_sympy_rational(sp.sqrt(2))
        False
        >>> is_sympy_rational(sp.Rational(1) + sp.sqrt(2))
        False
    """
    simplified = simplify(expr)

    # Check if it's already a Rational or Integer
    if isinstance(simplified, (sp.Rational, sp.Integer)):
        return True

    # Check if it has no irrational components
    # SymPy's is_rational property checks this
    if hasattr(simplified, 'is_rational') and simplified.is_rational is True:
        return True

    # Check for free symbols or irrational functions (sqrt, etc.)
    if simplified.has(sp.sqrt) or simplified.free_symbols:
        return False

    # Check for non-rational Pow expressions (like x^(1/2))
    for arg in sp.preorder_traversal(simplified):
        if isinstance(arg, sp.Pow):
            # Check if exponent is rational
            if not (isinstance(arg.exp, (sp.Rational, sp.Integer)) and
                    (isinstance(arg.exp, sp.Integer) or arg.exp.q == 1)):
                return False

    return True


def sympy_to_exact(expr: sp.Expr) -> ExactNumber:
    """
    Convert SymPy expression to the most efficient exact Python type.

    Conversion priority:
    1. int (if expression is an integer)
    2. Fraction (if expression is rational but not integer)
    3. SymPy Expr (if expression contains irrationals)

    Algorithm:
    1. Simplify expression
    2. Check is_sympy_integer() → return int
    3. Check is_sympy_rational() → return Fraction
    4. Otherwise → return SymPy Expr

    Args:
        expr: SymPy expression to convert

    Returns:
        int, Fraction, or SymPy Expr

    Examples:
        >>> sympy_to_exact(sp.Rational(6, 1))
        6  # Returns int
        >>> sympy_to_exact(sp.Rational(3, 2))
        Fraction(3, 2)
        >>> sympy_to_exact(sp.sqrt(2))
        sqrt(2)  # Returns SymPy Expr
        >>> sympy_to_exact(sp.sqrt(4))
        2  # Returns int (simplifies)
    """
    simplified = simplify(expr)

    # Check for integer
    if is_sympy_integer(simplified):
        if isinstance(simplified, sp.Rational):
            return int(simplified.p)
        elif isinstance(simplified, sp.Integer):
            return int(simplified)
        else:
            # Numerical evaluation
            return int(round(float(simplified.evalf())))

    # Check for rational
    if is_sympy_rational(simplified):
        if isinstance(simplified, sp.Rational):
            return Fraction(int(simplified.p), int(simplified.q))
        else:
            # Shouldn't normally reach here, but safe fallback
            return simplified

    # Must be irrational - keep as SymPy
    return simplified


# ============================================================================
# ARITHMETIC OPERATIONS
# ============================================================================

def smart_add(a: ExactNumber, b: ExactNumber) -> ExactNumber:
    """
    Add two exact numbers, returning the most efficient exact type.

    Algorithm:
    1. If both are int or Fraction: use Python arithmetic
    2. If result is int: return int
    3. If result is Fraction: return Fraction
    4. Otherwise: convert to SymPy, add, simplify, convert back

    Args:
        a, b: Exact numbers (int, Fraction, or SymPy)

    Returns:
        Sum as int, Fraction, or SymPy Expr

    Examples:
        >>> smart_add(1, 2)
        3  # int
        >>> smart_add(Fraction(1, 2), Fraction(1, 3))
        Fraction(5, 6)
        >>> smart_add(sp.sqrt(2), sp.sqrt(3))
        sqrt(2) + sqrt(3)  # SymPy
    """
    # If both are int/Fraction, use Python arithmetic
    if isinstance(a, (int, Fraction)) and isinstance(b, (int, Fraction)):
        result = a + b
        if isinstance(result, int):
            return result
        # Check if Fraction simplifies to integer
        if isinstance(result, Fraction) and result.denominator == 1:
            return int(result.numerator)
        return result  # Fraction

    # Otherwise use SymPy
    a_sp = to_sympy(a)
    b_sp = to_sympy(b)
    result_sp = simplify(a_sp + b_sp)

    return sympy_to_exact(result_sp)


def smart_multiply(a: ExactNumber, b: ExactNumber) -> ExactNumber:
    """
    Multiply two exact numbers, returning the most efficient exact type.

    Algorithm: Same as smart_add() but with multiplication

    Examples:
        >>> smart_multiply(2, 3)
        6  # int
        >>> smart_multiply(Fraction(2, 3), Fraction(3, 4))
        Fraction(1, 2)
        >>> smart_multiply(2, sp.sqrt(3))
        2*sqrt(3)  # SymPy
        >>> smart_multiply(sp.sqrt(2), sp.sqrt(2))
        2  # int (simplifies)
    """
    # If both are int/Fraction, use Python arithmetic
    if isinstance(a, (int, Fraction)) and isinstance(b, (int, Fraction)):
        result = a * b
        if isinstance(result, int):
            return result
        # Check if Fraction simplifies to integer
        if isinstance(result, Fraction) and result.denominator == 1:
            return int(result.numerator)
        return result  # Fraction

    # Otherwise use SymPy
    a_sp = to_sympy(a)
    b_sp = to_sympy(b)
    result_sp = simplify(a_sp * b_sp)

    return sympy_to_exact(result_sp)


def smart_divide(a: ExactNumber, b: ExactNumber) -> ExactNumber:
    """
    Divide two exact numbers, returning the most efficient exact type.

    Algorithm:
    1. If both int and division is exact: return int
    2. If both int/Fraction and result rational: return Fraction
    3. Otherwise: convert to SymPy, divide, simplify, convert back

    Examples:
        >>> smart_divide(6, 2)
        3  # int
        >>> smart_divide(3, 2)
        Fraction(3, 2)
        >>> smart_divide(1, sp.sqrt(2))
        sqrt(2)/2  # SymPy (rationalizes)
    """
    # If both are int/Fraction, use Python arithmetic
    if isinstance(a, (int, Fraction)) and isinstance(b, (int, Fraction)):
        if isinstance(a, int) and isinstance(b, int):
            # Check if division is exact
            if a % b == 0:
                return a // b  # int
            return Fraction(a, b)
        else:
            result = Fraction(a) / Fraction(b) if not isinstance(a, Fraction) or not isinstance(b, Fraction) else a / b
            if isinstance(result, Fraction) and result.denominator == 1:
                return int(result.numerator)
            return result

    # Otherwise use SymPy
    a_sp = to_sympy(a)
    b_sp = to_sympy(b)
    result_sp = simplify(a_sp / b_sp)

    return sympy_to_exact(result_sp)


def smart_sqrt(n: ExactNumber) -> ExactNumber:
    """
    Compute square root, returning exact representation.

    Algorithm:
    1. Convert to SymPy
    2. Apply sqrt()
    3. Simplify
    4. Convert back using sympy_to_exact()

    Args:
        n: Number to take square root of

    Returns:
        int (if perfect square), Fraction (if rational), else SymPy sqrt

    Examples:
        >>> smart_sqrt(4)
        2  # int
        >>> smart_sqrt(9)
        3  # int
        >>> smart_sqrt(2)
        sqrt(2)  # SymPy
        >>> smart_sqrt(Fraction(1, 4))
        Fraction(1, 2)
    """
    n_sp = to_sympy(n)
    result_sp = sqrt(n_sp)
    simplified = simplify(result_sp)

    return sympy_to_exact(simplified)


def smart_power(base: ExactNumber, exp: ExactNumber) -> ExactNumber:
    """
    Raise base to exponent power, returning exact representation.

    Algorithm:
    1. If both int/Fraction, use Python arithmetic
    2. Otherwise convert to SymPy, compute power, simplify, convert back

    Args:
        base: Base number
        exp: Exponent

    Returns:
        int, Fraction, or SymPy Expr

    Examples:
        >>> smart_power(2, 3)
        8  # int
        >>> smart_power(Fraction(1, 2), 2)
        Fraction(1, 4)
        >>> smart_power(sqrt(2), 2)
        2  # int (simplifies)
    """
    # If both are int/Fraction, use Python arithmetic
    if isinstance(base, (int, Fraction)) and isinstance(exp, (int, Fraction)):
        # For integer exponent, use ** operator
        if isinstance(exp, int) or (isinstance(exp, Fraction) and exp.denominator == 1):
            exp_int = int(exp) if isinstance(exp, Fraction) else exp
            result = base ** exp_int
            if isinstance(result, int):
                return result
            return result  # Fraction

    # Otherwise use SymPy
    base_sp = to_sympy(base)
    exp_sp = to_sympy(exp)
    result_sp = simplify(base_sp ** exp_sp)

    return sympy_to_exact(result_sp)


def smart_abs(n: ExactNumber) -> ExactNumber:
    """
    Compute absolute value, preserving exact type.

    Args:
        n: Number to take absolute value of

    Returns:
        Absolute value as int, Fraction, or SymPy Expr

    Examples:
        >>> smart_abs(-5)
        5  # int
        >>> smart_abs(Fraction(-3, 4))
        Fraction(3, 4)
        >>> smart_abs(-sqrt(2))
        sqrt(2)  # SymPy
    """
    if isinstance(n, int):
        return abs(n)
    elif isinstance(n, Fraction):
        return abs(n)
    else:
        # SymPy Expr
        n_sp = to_sympy(n)
        result_sp = sp.Abs(n_sp)
        simplified = simplify(result_sp)
        return sympy_to_exact(simplified)


# ============================================================================
# COMPLEX NUMBER OPERATIONS
# ============================================================================

def smart_complex_multiply(
    a: ExactComplex,
    b: ExactComplex
) -> Tuple[ExactNumber, ExactNumber]:
    """
    Multiply two complex exact numbers: (a_r + a_i*I) * (b_r + b_i*I).

    Formula: (a_r*b_r - a_i*b_i) + (a_r*b_i + a_i*b_r)*I

    Args:
        a, b: Complex numbers as (real, imag) tuples or SymPy Expr

    Returns:
        (real_part, imag_part) as tuple of ExactNumber

    Example:
        >>> a = (2, 3)  # 2 + 3i
        >>> b = (4, -1)  # 4 - i
        >>> smart_complex_multiply(a, b)
        (11, 10)  # (2*4 - 3*(-1)) + (2*(-1) + 3*4)i = 11 + 10i
    """
    # Extract components
    if isinstance(a, tuple):
        a_r, a_i = a
    elif isinstance(a, sp.Expr):
        a_r = smart_real(a)
        a_i = smart_imag(a)
    else:
        # Assume real number (no imaginary part)
        a_r, a_i = a, 0

    if isinstance(b, tuple):
        b_r, b_i = b
    elif isinstance(b, sp.Expr):
        b_r = smart_real(b)
        b_i = smart_imag(b)
    else:
        b_r, b_i = b, 0

    # (a_r + a_i*I) * (b_r + b_i*I) = (a_r*b_r - a_i*b_i) + (a_r*b_i + a_i*b_r)*I
    real_part = smart_add(
        smart_multiply(a_r, b_r),
        smart_multiply(smart_multiply(-1, a_i), b_i)
    )
    imag_part = smart_add(
        smart_multiply(a_r, b_i),
        smart_multiply(a_i, b_r)
    )

    return (real_part, imag_part)


def smart_complex_sqrt(z: ExactComplex) -> Tuple[ExactNumber, ExactNumber]:
    """
    Compute square root of complex number.

    For complex sqrt, result is typically irrational, so delegates to SymPy.

    Args:
        z: Complex number as (real, imag) tuple or SymPy Expr

    Returns:
        (real_part, imag_part) as tuple of ExactNumber

    Example:
        >>> smart_complex_sqrt((3, 4))  # sqrt(3 + 4i)
        (2, 1)  # Exact: 2 + i
    """
    # Convert to SymPy complex
    if isinstance(z, tuple):
        z_r, z_i = z
        z_sp = to_sympy(z_r) + to_sympy(z_i) * I
    elif isinstance(z, sp.Expr):
        z_sp = z
    else:
        z_sp = to_sympy(z)

    # Take sqrt
    result_sp = sqrt(z_sp)
    simplified = simplify(result_sp)

    # Extract real and imaginary parts
    real_part = sympy_to_exact(simplify(re(simplified)))
    imag_part = sympy_to_exact(simplify(im(simplified)))

    return (real_part, imag_part)


def smart_real(z: ExactComplex) -> ExactNumber:
    """
    Extract real part of complex number.

    Args:
        z: Complex number as (real, imag) tuple or SymPy Expr

    Returns:
        Real part as ExactNumber
    """
    if isinstance(z, tuple):
        return z[0]
    elif isinstance(z, sp.Expr):
        return sympy_to_exact(simplify(re(z)))
    else:
        # Assume real number
        return z


def smart_imag(z: ExactComplex) -> ExactNumber:
    """
    Extract imaginary part of complex number.

    Args:
        z: Complex number as (real, imag) tuple or SymPy Expr

    Returns:
        Imaginary part as ExactNumber
    """
    if isinstance(z, tuple):
        return z[1]
    elif isinstance(z, sp.Expr):
        return sympy_to_exact(simplify(im(z)))
    else:
        # Assume real number (no imaginary part)
        return 0


def smart_complex_divide(
    a: ExactComplex,
    b: ExactComplex
) -> Tuple[ExactNumber, ExactNumber]:
    """
    Divide two complex exact numbers: (a_r + a_i*I) / (b_r + b_i*I).

    Formula: (a_r + a_i*I) / (b_r + b_i*I) = ((a_r*b_r + a_i*b_i) + (a_i*b_r - a_r*b_i)*I) / (b_r^2 + b_i^2)

    Args:
        a, b: Complex numbers as (real, imag) tuples or SymPy Expr

    Returns:
        (real_part, imag_part) as tuple of ExactNumber

    Example:
        >>> smart_complex_divide((10, 5), (2, 1))  # (10 + 5i) / (2 + i)
        (5, 0)  # 5 + 0i
    """
    # Extract components of a
    if isinstance(a, tuple):
        a_r, a_i = a
    elif isinstance(a, sp.Expr):
        a_r = smart_real(a)
        a_i = smart_imag(a)
    else:
        a_r, a_i = a, 0

    # Extract components of b
    if isinstance(b, tuple):
        b_r, b_i = b
    elif isinstance(b, sp.Expr):
        b_r = smart_real(b)
        b_i = smart_imag(b)
    else:
        b_r, b_i = b, 0

    # Calculate denominator: b_r^2 + b_i^2
    denom = smart_add(
        smart_multiply(b_r, b_r),
        smart_multiply(b_i, b_i)
    )

    # Calculate numerator real part: a_r*b_r + a_i*b_i
    num_real = smart_add(
        smart_multiply(a_r, b_r),
        smart_multiply(a_i, b_i)
    )

    # Calculate numerator imaginary part: a_i*b_r - a_r*b_i
    num_imag = smart_add(
        smart_multiply(a_i, b_r),
        smart_multiply(-1, smart_multiply(a_r, b_i))
    )

    # Divide by denominator
    real_part = smart_divide(num_real, denom)
    imag_part = smart_divide(num_imag, denom)

    return (real_part, imag_part)


def smart_complex_conjugate(z: ExactComplex) -> Tuple[ExactNumber, ExactNumber]:
    """
    Compute complex conjugate: (a + bi)* = a - bi.

    Args:
        z: Complex number as (real, imag) tuple or SymPy Expr

    Returns:
        (real_part, -imag_part) as tuple of ExactNumber

    Example:
        >>> smart_complex_conjugate((3, 4))
        (3, -4)  # (3 + 4i)* = 3 - 4i
    """
    if isinstance(z, tuple):
        real, imag = z
        return (real, smart_multiply(-1, imag))
    elif isinstance(z, sp.Expr):
        conj_sp = sp.conjugate(z)
        real_part = sympy_to_exact(simplify(re(conj_sp)))
        imag_part = sympy_to_exact(simplify(im(conj_sp)))
        return (real_part, imag_part)
    else:
        # Real number, conjugate is itself
        return (z, 0)


def smart_abs_squared(z: ExactComplex) -> ExactNumber:
    """
    Compute |z|^2 = z * conjugate(z) = a^2 + b^2.

    Args:
        z: Complex number as (real, imag) tuple or SymPy Expr

    Returns:
        |z|^2 as ExactNumber

    Example:
        >>> smart_abs_squared((3, 4))
        25  # |3 + 4i|^2 = 9 + 16 = 25
    """
    if isinstance(z, tuple):
        real, imag = z
    elif isinstance(z, sp.Expr):
        real = smart_real(z)
        imag = smart_imag(z)
    else:
        # Real number
        real, imag = z, 0

    # |z|^2 = real^2 + imag^2
    return smart_add(
        smart_multiply(real, real),
        smart_multiply(imag, imag)
    )


# ============================================================================
# CONVERSION FUNCTIONS
# ============================================================================

def to_sympy(n: ExactNumber) -> sp.Expr:
    """
    Convert any exact number to SymPy expression.

    Args:
        n: int, Fraction, or SymPy Expr

    Returns:
        SymPy expression

    Examples:
        >>> to_sympy(42)
        42
        >>> to_sympy(Fraction(3, 2))
        3/2
        >>> to_sympy(sp.sqrt(2))
        sqrt(2)  # unchanged
    """
    if isinstance(n, sp.Expr):
        return n
    elif isinstance(n, Fraction):
        return sp.Rational(n.numerator, n.denominator)
    elif isinstance(n, int):
        return sp.Integer(n)
    elif isinstance(n, float):
        # Discouraged but supported
        return sp.Float(n)
    else:
        raise TypeError(f"Cannot convert {type(n)} to SymPy")


def to_string(n: ExactNumber) -> str:
    """
    Convert exact number to string representation.

    Format:
    - int: "42"
    - Fraction: "3/2"
    - SymPy: "sqrt(2)" or "1 + sqrt(3)"

    Args:
        n: Exact number

    Returns:
        String representation

    Examples:
        >>> to_string(42)
        "42"
        >>> to_string(Fraction(3, 2))
        "3/2"
        >>> to_string(sp.sqrt(2))
        "sqrt(2)"
        >>> to_string(sp.Rational(1, 2) + sp.sqrt(3))
        "1/2 + sqrt(3)"
    """
    if isinstance(n, int):
        return str(n)
    elif isinstance(n, Fraction):
        return f"{n.numerator}/{n.denominator}"
    elif isinstance(n, sp.Expr):
        return str(n)
    else:
        raise TypeError(f"Cannot convert {type(n)} to string")


def format_exact(n: ExactNumber) -> str:
    """
    Format exact number as tagged string for database storage.

    Tagged Format:
    - int: "int:42"
    - Fraction: "frac:3/2"
    - SymPy: "sym:sqrt(2)"

    Args:
        n: Exact number

    Returns:
        Tagged string

    Examples:
        >>> format_exact(6)
        "int:6"
        >>> format_exact(Fraction(3, 2))
        "frac:3/2"
        >>> format_exact(sp.sqrt(2))
        "sym:sqrt(2)"
        >>> format_exact(sp.Rational(7, 6) + 2*sp.sqrt(2)/3)
        "sym:7/6 + 2*sqrt(2)/3"
    """
    if isinstance(n, int):
        return f"int:{n}"
    elif isinstance(n, Fraction):
        return f"frac:{n.numerator}/{n.denominator}"
    elif isinstance(n, sp.Expr):
        return f"sym:{str(n)}"
    else:
        raise TypeError(f"Cannot format {type(n)} as exact string")


def parse_exact(s: str) -> ExactNumber:
    """
    Parse tagged exact number string from database.

    Args:
        s: Tagged string ("int:42", "frac:3/2", or "sym:sqrt(2)")

    Returns:
        int, Fraction, or SymPy Expr

    Raises:
        ValueError: If format is unrecognized

    Examples:
        >>> parse_exact("int:6")
        6
        >>> parse_exact("frac:3/2")
        Fraction(3, 2)
        >>> parse_exact("sym:sqrt(2)")
        sqrt(2)
        >>> parse_exact("sym:7/6 + 2*sqrt(2)/3")
        7/6 + 2*sqrt(2)/3
    """
    if s.startswith("int:"):
        return int(s[4:])
    elif s.startswith("frac:"):
        parts = s[5:].split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid fraction format: {s}")
        return Fraction(int(parts[0]), int(parts[1]))
    elif s.startswith("sym:"):
        return sp.sympify(s[4:])
    else:
        raise ValueError(f"Unknown exact format: {s}")


def to_numerator_denominator(n: ExactNumber) -> Tuple[int, int]:
    """
    Extract numerator and denominator (LOSSY for irrationals).

    ⚠️ WARNING: This is LOSSY for irrational SymPy expressions!
    Only use for backwards compatibility with old database schema.

    Args:
        n: Exact number

    Returns:
        (numerator, denominator) tuple

    Behavior:
    - int: (n, 1)
    - Fraction: (numerator, denominator)
    - SymPy rational: Extract p, q
    - SymPy irrational: Approximate with .limit_denominator(10^9) ⚠️ LOSSY

    Examples:
        >>> to_numerator_denominator(6)
        (6, 1)
        >>> to_numerator_denominator(Fraction(3, 2))
        (3, 2)
        >>> to_numerator_denominator(sp.sqrt(2))
        (14142135, 10000000)  # ⚠️ APPROXIMATION!
    """
    if isinstance(n, int):
        return (n, 1)
    elif isinstance(n, Fraction):
        return (n.numerator, n.denominator)
    elif isinstance(n, sp.Expr):
        # Check if it's actually rational
        if is_sympy_rational(n):
            exact = sympy_to_exact(n)
            if isinstance(exact, int):
                return (exact, 1)
            else:  # Fraction
                return (exact.numerator, exact.denominator)
        else:
            # Must convert lossily - WARNING!
            float_val = float(n.evalf(50))
            frac = Fraction(float_val).limit_denominator(10**9)
            return (frac.numerator, frac.denominator)
    else:
        raise TypeError(f"Cannot convert {type(n)} to num/denom")


def to_fraction_lossy(n: ExactNumber, max_denom: int = 10**9) -> Fraction:
    """
    Convert exact number to Fraction (LOSSY for irrationals).

    ⚠️ WARNING: This loses exactness for irrational numbers!
    Only use for final output/visualization, never for internal calculations.

    Args:
        n: Exact number
        max_denom: Maximum denominator for approximation

    Returns:
        Fraction approximation

    Examples:
        >>> to_fraction_lossy(6)
        Fraction(6, 1)
        >>> to_fraction_lossy(Fraction(3, 2))
        Fraction(3, 2)
        >>> to_fraction_lossy(sp.sqrt(2))
        Fraction(14142135, 10000000)  # ⚠️ APPROXIMATION!
    """
    if isinstance(n, int):
        return Fraction(n)
    elif isinstance(n, Fraction):
        return n
    elif isinstance(n, sp.Expr):
        # Lossy conversion
        float_val = float(n.evalf(50))
        return Fraction(float_val).limit_denominator(max_denom)
    else:
        raise TypeError(f"Cannot convert {type(n)} to Fraction")
