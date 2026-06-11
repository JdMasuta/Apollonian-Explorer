"""
Augmented curvature-center ("inversive") coordinates for circles and lines.

Reference: REVAMP_BLUEPRINT.md Phase 2.0; Lagarias, Mallows & Wilks,
"Beyond the Descartes Circle Theorem" (Amer. Math. Monthly 109, 2002).

A circle with curvature b != 0 and center (x, y) is represented by the vector

    v = (cocurvature, curvature, kx, ky) = (b̄, b, b·x, b·y)

where the co-curvature b̄ = b(x² + y²) − 1/b is the curvature of the image of
the circle under inversion in the unit circle. A line with unit normal
(nx, ny) and signed offset d (the line {p : <p, n> = d}) is the b = 0 case,
represented as (2d, 0, nx, ny).

Every valid vector satisfies the Descartes quadratic form

    Q(v) = b̄·b − kx² − ky² = −1                          (exactly)

and two distinct oriented circles/lines of a packing are tangent iff the
associated bilinear form equals +1:

    B(v, w) = (b̄_v·b_w + b_v·b̄_w)/2 − kx_v·kx_w − ky_v·ky_w = 1   (exactly)

Both invariants are exact integer/rational identities -- the engine never
compares with floating-point tolerances.

Scalars are ``int``/``fractions.Fraction`` for rational packings (every
integral Apollonian packing has integer coordinates in this representation)
and SymPy expressions for irrational seeds. Because the Apollonian group acts
ℤ-linearly (see core.engine.group), the scalar domain chosen at seed time is
closed under generation: no new square roots ever appear.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple, Union

import sympy as sp

# Exact scalar domain: int and Fraction for rational packings, SymPy Expr for
# packings whose canonical placement involves square roots.
Exact = Union[int, Fraction, sp.Expr]


def _exact_div(numerator: Exact, denominator: Exact) -> Exact:
    """Exact division within the scalar domain (never floating point)."""
    if isinstance(numerator, (int, Fraction)) and isinstance(denominator, (int, Fraction)):
        return Fraction(numerator) / Fraction(denominator)
    quotient = sp.sympify(numerator) / sp.sympify(denominator)
    return from_sympy_scalar(quotient)


def from_sympy_scalar(value: sp.Expr) -> Exact:
    """Demote a SymPy scalar to int/Fraction when it is exactly rational."""
    if isinstance(value, sp.Integer):
        return int(value)
    if isinstance(value, sp.Rational):
        return Fraction(int(value.p), int(value.q))
    return value


def exact_to_sympy(value: Exact) -> sp.Expr:
    """Promote an exact scalar to a SymPy expression."""
    if isinstance(value, Fraction):
        return sp.Rational(value.numerator, value.denominator)
    return sp.sympify(value)


def exact_str(value: Exact) -> str:
    """Canonical string form: '6', '-3/2', or a SymPy srepr-able expression."""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Fraction):
        return str(value)
    return str(sp.nsimplify(value))


@dataclass(frozen=True)
class InversiveCircle:
    """A circle (or line) in augmented curvature-center coordinates."""

    cocurvature: Exact
    curvature: Exact
    kx: Exact
    ky: Exact

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @staticmethod
    def from_curvature_center(curvature: Exact, x: Exact, y: Exact) -> "InversiveCircle":
        """Build the coordinate vector of a circle from curvature and center.

        Raises:
            ValueError: if curvature is zero (use :meth:`line` for lines).
        """
        if curvature == 0:
            raise ValueError("Curvature 0 is a line; use InversiveCircle.line(nx, ny, d)")
        if isinstance(curvature, (int, Fraction)) and isinstance(x, (int, Fraction)) and isinstance(
            y, (int, Fraction)
        ):
            b = Fraction(curvature)
            cocurv: Exact = b * (Fraction(x) ** 2 + Fraction(y) ** 2) - 1 / b
            kx: Exact = b * Fraction(x)
            ky: Exact = b * Fraction(y)
            return InversiveCircle(_demote(cocurv), _demote(b), _demote(kx), _demote(ky))
        b_s = exact_to_sympy(curvature)
        x_s = exact_to_sympy(x)
        y_s = exact_to_sympy(y)
        cocurv_s = sp.expand(b_s * (x_s**2 + y_s**2) - 1 / b_s)
        return InversiveCircle(
            from_sympy_scalar(sp.nsimplify(cocurv_s)),
            curvature,
            from_sympy_scalar(sp.nsimplify(b_s * x_s)),
            from_sympy_scalar(sp.nsimplify(b_s * y_s)),
        )

    @staticmethod
    def line(nx: Exact, ny: Exact, d: Exact) -> "InversiveCircle":
        """Build the coordinate vector of the line {p : <p, (nx, ny)> = d}.

        The normal must be a unit vector (checked exactly). The orientation of
        the normal selects which half-plane is "inside"; tangency to circles on
        the normal side then satisfies B = 1.

        Raises:
            ValueError: if (nx, ny) is not exactly a unit vector.
        """
        norm_sq = _mul(nx, nx) + _mul(ny, ny)
        if not _exact_eq(norm_sq, 1):
            raise ValueError(f"Line normal must be a unit vector, got |n|^2 = {norm_sq}")
        return InversiveCircle(_mul(2, d), 0, nx, ny)

    # ------------------------------------------------------------------
    # Geometry accessors
    # ------------------------------------------------------------------

    @property
    def is_line(self) -> bool:
        """True if this vector represents a line (zero curvature)."""
        return self.curvature == 0

    def center(self) -> Tuple[Exact, Exact]:
        """Exact center (x, y) = (kx/b, ky/b).

        Raises:
            ValueError: for lines (no center).
        """
        if self.is_line:
            raise ValueError("A line has no center")
        return (_exact_div(self.kx, self.curvature), _exact_div(self.ky, self.curvature))

    def radius(self) -> Exact:
        """Exact radius 1/|b|.

        Raises:
            ValueError: for lines (infinite radius).
        """
        if self.is_line:
            raise ValueError("A line has infinite radius")
        b = self.curvature
        if isinstance(b, (int, Fraction)):
            return _demote(1 / abs(Fraction(b)))
        return from_sympy_scalar(1 / sp.Abs(exact_to_sympy(b)))

    # ------------------------------------------------------------------
    # Exact invariants
    # ------------------------------------------------------------------

    def q_form(self) -> Exact:
        """Descartes quadratic form Q(v) = b̄·b − kx² − ky²; −1 for valid vectors."""
        return _demote_maybe(
            _mul(self.cocurvature, self.curvature) - _mul(self.kx, self.kx) - _mul(self.ky, self.ky)
        )

    def is_valid(self) -> bool:
        """True iff Q(v) == −1 exactly."""
        return _exact_eq(self.q_form(), -1)

    def inner(self, other: "InversiveCircle") -> Exact:
        """Bilinear Descartes form B(v, w). Tangent circles give exactly 1."""
        value = (
            _exact_div(
                _mul(self.cocurvature, other.curvature) + _mul(self.curvature, other.cocurvature),
                2,
            )
            - _mul(self.kx, other.kx)
            - _mul(self.ky, other.ky)
        )
        return _demote_maybe(value)

    def is_tangent_to(self, other: "InversiveCircle") -> bool:
        """Exact tangency test: B(v, w) == 1."""
        return _exact_eq(self.inner(other), 1)

    # ------------------------------------------------------------------
    # Approximation & serialization (presentation layer only)
    # ------------------------------------------------------------------

    def approx(self) -> Tuple[float, float, float]:
        """(x, y, radius) as floats for rendering/pruning. Lines raise."""
        x, y = self.center()
        return (float(x), float(y), float(self.radius()))

    def curvature_float(self) -> float:
        """Curvature as float (works for all scalar domains)."""
        return float(self.curvature)

    def as_dict(self) -> dict[str, object]:
        """Serializable form with exact strings plus float mirrors."""
        if self.is_line:
            return {
                "kind": "line",
                "curvature": "0",
                "normal": {"x": exact_str(self.kx), "y": exact_str(self.ky)},
                "offset": exact_str(_exact_div(self.cocurvature, 2)),
            }
        x, y = self.center()
        return {
            "kind": "circle",
            "curvature": exact_str(self.curvature),
            "cocurvature": exact_str(self.cocurvature),
            "center": {"x": exact_str(x), "y": exact_str(y)},
            "radius": exact_str(self.radius()),
            "curvature_float": float(self.curvature),
            "x_float": float(x),
            "y_float": float(y),
        }


# ----------------------------------------------------------------------
# Scalar helpers (module-private)
# ----------------------------------------------------------------------


def _demote(value: Exact) -> Exact:
    """Fraction -> int when the denominator is 1 (fast integer path)."""
    if isinstance(value, Fraction) and value.denominator == 1:
        return value.numerator
    return value


def _demote_maybe(value: Exact) -> Exact:
    if isinstance(value, Fraction):
        return _demote(value)
    if isinstance(value, sp.Expr):
        return from_sympy_scalar(sp.nsimplify(sp.expand(value)))
    return value


def _mul(a: Exact, b: Exact) -> Exact:
    if isinstance(a, (int, Fraction)) and isinstance(b, (int, Fraction)):
        return a * b
    return exact_to_sympy(a) * exact_to_sympy(b)


def _exact_eq(value: Exact, target: int) -> bool:
    if isinstance(value, (int, Fraction)):
        return value == target
    return bool(sp.simplify(sp.sympify(value) - target) == 0)
