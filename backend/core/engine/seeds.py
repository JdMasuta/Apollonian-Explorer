"""
Seed (root quartet) construction for Apollonian packings.

Reference: REVAMP_BLUEPRINT.md Phase 2.2 / Milestone 1.

All square roots in the engine are taken here, once, at seed time. After a
seed is built, generation (core.engine.walk) is purely linear.

Supported seeds:
- Named presets (``seed_from_preset``), including the unbounded Apollonian
  strip (``seed_strip``) built from two parallel lines.
- Descartes quadruples (``seed_from_quadruple``): four curvatures satisfying
  2(k₁²+k₂²+k₃²+k₄²) = (k₁+k₂+k₃+k₄)², placed canonically.
- Curvature triples (``seed_from_triple``): completed to a quadruple via the
  Descartes relation k₄ = k₁+k₂+k₃ ± 2√(k₁k₂+k₂k₃+k₃k₁).

Canonical placement: the first circle is centered at the origin, the second
on the positive x-axis, the third in the upper half-plane; the fourth is
selected exactly by requiring B(v₄, v₃) = 1 (tangency as an algebraic
identity, not a float check).

Every constructed seed is verified exactly: Q(vᵢ) = −1 and B(vᵢ, vⱼ) = 1 for
all pairs. Construction fails loudly rather than returning an approximately
tangent configuration (the failure mode of the legacy generator, see
ISSUES.md Issue #2).
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Dict, List, Sequence, Tuple

import sympy as sp

from core.engine.group import Quartet
from core.engine.inversive import Exact, InversiveCircle, exact_to_sympy, from_sympy_scalar

#: Named seed presets: classic bounded gaskets by root quadruple.
PRESETS: Dict[str, Tuple[int, int, int, int]] = {
    # The standard textbook gasket.
    "classic": (-1, 2, 2, 3),
    # Further primitive integral root quadruples (Graham-Lagarias-Mallows-
    # Wilks-Yan catalogue).
    "soddy-0-0-1-1-strip": (0, 0, 1, 1),  # handled by seed_strip()
    "minus2-3-6-7": (-2, 3, 6, 7),
    "minus3-4-12-13": (-3, 4, 12, 13),
    "minus3-5-8-8": (-3, 5, 8, 8),
    "minus6-10-15-19": (-6, 10, 15, 19),
    "minus11-21-24-28": (-11, 21, 24, 28),
}


def is_descartes_quadruple(k1: Exact, k2: Exact, k3: Exact, k4: Exact) -> bool:
    """Exact check of the Descartes relation 2Σkᵢ² = (Σkᵢ)²."""
    lhs = 2 * (_sq(k1) + _sq(k2) + _sq(k3) + _sq(k4))
    rhs = _sq(k1 + k2 + k3 + k4)
    diff = lhs - rhs
    if isinstance(diff, (int, Fraction)):
        return diff == 0
    return bool(sp.simplify(diff) == 0)


def complete_triple(k1: Exact, k2: Exact, k3: Exact) -> Tuple[Exact, Exact]:
    """Both Descartes completions k₄ = (k₁+k₂+k₃) ± 2√(k₁k₂+k₂k₃+k₃k₁).

    Returns:
        (k4_plus, k4_minus). Rational results are returned as int/Fraction;
        irrational results as exact SymPy expressions.

    Raises:
        ValueError: if the discriminant is negative (no real completion).
    """
    disc = k1 * k2 + k2 * k3 + k3 * k1
    if isinstance(disc, (int, Fraction)):
        if disc < 0:
            raise ValueError(f"No real Descartes completion: discriminant {disc} < 0")
        root = _rational_sqrt(disc)
    else:
        disc_s = sp.nsimplify(disc)
        if disc_s.is_negative:
            raise ValueError(f"No real Descartes completion: discriminant {disc_s} < 0")
        root = from_sympy_scalar(sp.sqrt(disc_s))
    s = k1 + k2 + k3
    return (_norm(s + 2 * root), _norm(s - 2 * root))


def seed_from_preset(name: str) -> Quartet:
    """Build a named preset seed (see PRESETS)."""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Available: {sorted(PRESETS)}")
    quadruple = PRESETS[name]
    if 0 in quadruple:
        return seed_strip()
    return seed_from_quadruple(*quadruple)


def seed_from_quadruple(k1: Exact, k2: Exact, k3: Exact, k4: Exact) -> Quartet:
    """Canonically place a Descartes quadruple as a tangent quartet.

    The curvatures are used in the given order: circle 1 at the origin,
    circle 2 on the positive x-axis, circle 3 in the upper half-plane,
    circle 4 selected exactly by tangency to circle 3.

    Raises:
        ValueError: if the quadruple fails the Descartes relation, contains a
            zero curvature (use seed_strip for line configurations), contains
            more than one non-positive curvature, or fails exact verification
            after placement.
    """
    ks = [_norm(k) for k in (k1, k2, k3, k4)]
    if any(k == 0 for k in ks):
        raise ValueError(
            "Zero curvatures (lines) are not supported by quadruple placement; "
            "use seed_strip() for the Apollonian strip"
        )
    if not is_descartes_quadruple(*ks):
        raise ValueError(f"Curvatures {ks} do not satisfy the Descartes quadratic relation")
    if sum(1 for k in ks if _is_negative(k)) > 1:
        raise ValueError(f"At most one enclosing (negative) curvature allowed, got {ks}")

    # Place with the enclosing circle (if any) first so internal tangency
    # distances are well-defined.
    order = sorted(range(4), key=lambda i: _to_float(ks[i]))
    ka, kb, kc, kd = (ks[i] for i in order)

    # Circle a at origin; circle b on the positive x-axis.
    pa = (_z(), _z())
    pb = (_tangent_distance(ka, kb), _z())

    # Circle c via the two tangency distance constraints (upper half-plane).
    pc = _third_position(ka, kb, kc, pb[0])

    # Circle d via distances to a and b; the sign of y_d is fixed exactly by
    # tangency to circle c.
    pd_x, pd_y_abs = _fourth_position(ka, kb, kd, pb[0])
    vc = InversiveCircle.from_curvature_center(kc, *pc)
    candidate_up = InversiveCircle.from_curvature_center(kd, pd_x, pd_y_abs)
    candidate_dn = InversiveCircle.from_curvature_center(kd, pd_x, -pd_y_abs)
    if candidate_up.is_tangent_to(vc):
        vd = candidate_up
    elif candidate_dn.is_tangent_to(vc):
        vd = candidate_dn
    else:
        raise ValueError(f"Cannot realize quadruple {ks}: no tangent placement for k₄ = {kd}")

    va = InversiveCircle.from_curvature_center(ka, *pa)
    vb = InversiveCircle.from_curvature_center(kb, *pb)
    placed = {order[0]: va, order[1]: vb, order[2]: vc, order[3]: vd}
    quartet = (placed[0], placed[1], placed[2], placed[3])
    _verify(quartet)
    return quartet


def seed_from_triple(k1: Exact, k2: Exact, k3: Exact) -> Quartet:
    """Complete a curvature triple and place the resulting quartet.

    The minus branch of the Descartes completion is chosen, which yields the
    enclosing circle when one exists (e.g. (1, 1, 1) → k₄ = 3 − 2√3 < 0).
    """
    _, k4 = complete_triple(k1, k2, k3)
    return seed_from_quadruple(k1, k2, k3, k4)


def seed_strip() -> Quartet:
    """The Apollonian strip: root quadruple (0, 0, 1, 1).

    Two horizontal lines y = 0 and y = 2 with two unit circles between them,
    centered at (0, 1) and (2, 1). Generates the unbounded strip packing
    (Ford-circle-like configurations appear in its orbit).
    """
    line_bottom = InversiveCircle.line(0, -1, 0)  # y = 0, inside is y > 0
    line_top = InversiveCircle.line(0, 1, 2)  # y = 2, inside is y < 2
    c1 = InversiveCircle.from_curvature_center(1, 0, 1)
    c2 = InversiveCircle.from_curvature_center(1, 2, 1)
    quartet = (line_bottom, line_top, c1, c2)
    _verify(quartet)
    return quartet


# ----------------------------------------------------------------------
# Placement helpers
# ----------------------------------------------------------------------


def _tangent_distance(ki: Exact, kj: Exact) -> Exact:
    """Exact center distance of two tangent circles.

    External tangency (both curvatures positive): rᵢ + rⱼ.
    Internal tangency (one negative, enclosing): |r_neg| − r_pos.
    """
    ri = _inv_abs(ki)
    rj = _inv_abs(kj)
    if _is_negative(ki):
        return _norm(ri - rj)
    if _is_negative(kj):
        return _norm(rj - ri)
    return _norm(ri + rj)


def _third_position(ka: Exact, kb: Exact, kc: Exact, dab: Exact) -> Tuple[Exact, Exact]:
    """Position of the third circle from its two tangency distances.

    Standard two-circle intersection: with circle a at the origin and circle b
    at (dab, 0),

        x = (dab² + dac² − dbc²) / (2·dab),   y = +√(dac² − x²)
    """
    dac = _tangent_distance(ka, kc)
    dbc = _tangent_distance(kb, kc)
    x = _div(_sq(dab) + _sq(dac) - _sq(dbc), 2 * dab)
    y_sq = _norm(_sq(dac) - _sq(x))
    return (x, _sqrt_nonneg(y_sq))


def _fourth_position(ka: Exact, kb: Exact, kd: Exact, dab: Exact) -> Tuple[Exact, Exact]:
    """x-coordinate and |y| of the fourth circle from distances to a and b."""
    dad = _tangent_distance(ka, kd)
    dbd = _tangent_distance(kb, kd)
    x = _div(_sq(dab) + _sq(dad) - _sq(dbd), 2 * dab)
    y_sq = _norm(_sq(dad) - _sq(x))
    return (x, _sqrt_nonneg(y_sq))


def _verify(quartet: Sequence[InversiveCircle]) -> None:
    """Exact post-conditions: Q(vᵢ) = −1 and pairwise B(vᵢ, vⱼ) = 1."""
    for i, v in enumerate(quartet):
        if not v.is_valid():
            raise ValueError(f"Seed circle {i} violates Q(v) = -1: Q = {v.q_form()}")
    for i in range(4):
        for j in range(i + 1, 4):
            if not quartet[i].is_tangent_to(quartet[j]):
                raise ValueError(
                    f"Seed circles {i} and {j} are not tangent: "
                    f"B = {quartet[i].inner(quartet[j])}"
                )


# ----------------------------------------------------------------------
# Exact scalar helpers
# ----------------------------------------------------------------------


def _z() -> Exact:
    return 0


def _norm(value: Exact) -> Exact:
    if isinstance(value, Fraction) and value.denominator == 1:
        return value.numerator
    if isinstance(value, sp.Expr):
        return from_sympy_scalar(sp.nsimplify(sp.expand(value)))
    return value


def _sq(value: Exact) -> Exact:
    return value * value


def _div(numerator: Exact, denominator: Exact) -> Exact:
    if isinstance(numerator, (int, Fraction)) and isinstance(denominator, (int, Fraction)):
        return _norm(Fraction(numerator) / Fraction(denominator))
    return _norm(exact_to_sympy(numerator) / exact_to_sympy(denominator))


def _inv_abs(k: Exact) -> Exact:
    if isinstance(k, (int, Fraction)):
        return _norm(1 / abs(Fraction(k)))
    return _norm(1 / sp.Abs(exact_to_sympy(k)))


def _is_negative(k: Exact) -> bool:
    if isinstance(k, (int, Fraction)):
        return k < 0
    result = sp.nsimplify(k).is_negative
    if result is None:
        return float(k) < 0
    return bool(result)


def _to_float(k: Exact) -> float:
    return float(k)


def _rational_sqrt(value: Exact) -> Exact:
    """√value for non-negative rational value: Fraction if perfect, else SymPy."""
    frac = Fraction(value)
    num_root = math.isqrt(frac.numerator)
    den_root = math.isqrt(frac.denominator)
    if num_root * num_root == frac.numerator and den_root * den_root == frac.denominator:
        return _norm(Fraction(num_root, den_root))
    return from_sympy_scalar(sp.sqrt(sp.Rational(frac.numerator, frac.denominator)))


def _sqrt_nonneg(value: Exact) -> Exact:
    if isinstance(value, (int, Fraction)):
        if value < 0:
            raise ValueError(f"Negative radicand {value}: configuration is not realizable")
        return _rational_sqrt(value)
    value_s = sp.nsimplify(value)
    if value_s.is_negative:
        raise ValueError(f"Negative radicand {value_s}: configuration is not realizable")
    return from_sympy_scalar(sp.sqrt(value_s))


__all__: List[str] = [
    "PRESETS",
    "is_descartes_quadruple",
    "complete_triple",
    "seed_from_preset",
    "seed_from_quadruple",
    "seed_from_triple",
    "seed_strip",
]
