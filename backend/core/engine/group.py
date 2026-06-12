"""
The Apollonian group action on tangent quartets.

Reference: REVAMP_BLUEPRINT.md Phase 2.0 / Milestone 1.

Given a Descartes quartet (v₁, v₂, v₃, v₄) of mutually tangent circles in
inversive coordinates, the "swap" reflection Sⱼ replaces circle j with the
unique other circle tangent to the remaining three:

    Sⱼ:  vⱼ  ←  2(vₐ + v_b + v_c) − vⱼ

This is the entire generation step: ℤ-linear, square-root free, and an exact
involution (Sⱼ² = id). The four reflections generate the Apollonian group,
which is the free product ℤ/2 ∗ ℤ/2 ∗ ℤ/2 ∗ ℤ/2; reduced words in the
generators are in bijection with the circles of the packing (see
core.engine.walk).

The dual Apollonian group and general Möbius transforms (O(3,1) matrices) are
scheduled for Milestone 5 and will live in this module.
"""

from __future__ import annotations

from typing import Tuple

from core.engine.inversive import InversiveCircle

Quartet = Tuple[InversiveCircle, InversiveCircle, InversiveCircle, InversiveCircle]


def reflect(quartet: Quartet, j: int) -> InversiveCircle:
    """Return the reflection Sⱼ applied to quartet member j.

    The result is the *other* circle tangent to the three quartet members
    distinct from j. Componentwise: vⱼ' = 2(vₐ + v_b + v_c) − vⱼ.

    Args:
        quartet: four mutually tangent circles.
        j: index (0-3) of the circle to swap out.

    Returns:
        The new InversiveCircle replacing quartet[j].
    """
    if not 0 <= j <= 3:
        raise ValueError(f"Quartet index must be 0-3, got {j}")
    vj = quartet[j]
    a, b, c = (quartet[m] for m in range(4) if m != j)
    return InversiveCircle(
        2 * (a.cocurvature + b.cocurvature + c.cocurvature) - vj.cocurvature,
        2 * (a.curvature + b.curvature + c.curvature) - vj.curvature,
        2 * (a.kx + b.kx + c.kx) - vj.kx,
        2 * (a.ky + b.ky + c.ky) - vj.ky,
    )


def apply_reflection(quartet: Quartet, j: int) -> Quartet:
    """Return the quartet with member j swapped by Sⱼ."""
    new = reflect(quartet, j)
    members = list(quartet)
    members[j] = new
    return (members[0], members[1], members[2], members[3])


def reflection_coefficients(j: int) -> Tuple[Tuple[int, int, int, int], ...]:
    """The 4×4 integer matrix of Sⱼ acting on stacked quartet vectors.

    Row i gives the coefficients expressing the new vᵢ in terms of the old
    quartet members. Used by tests to verify Sⱼ² = id over ℤ.
    """
    if not 0 <= j <= 3:
        raise ValueError(f"Quartet index must be 0-3, got {j}")
    rows: list[Tuple[int, int, int, int]] = []
    for i in range(4):
        if i != j:
            row = tuple(1 if m == i else 0 for m in range(4))
        else:
            row = tuple(-1 if m == j else 2 for m in range(4))
        rows.append((row[0], row[1], row[2], row[3]))
    return tuple(rows)


def invert(mirror: InversiveCircle, target: InversiveCircle) -> InversiveCircle:
    """Inversion of ``target`` in the circle (or line) ``mirror``.

    Circle inversion is the Lorentz reflection across the mirror's vector in
    the Descartes form (Q(mirror) = -1):

        R(w) = w + 2·B(w, mirror)·mirror

    Exact and linear; preserves Q and all pairwise inner products, so it maps
    packings to packings. Inverting in the unit circle at the origin swaps
    curvature and co-curvature (the definition of co-curvature). Member
    circles through the mirror's center map to lines (b = 0).
    """
    factor = 2 * mirror.inner(target)
    return InversiveCircle(
        target.cocurvature + factor * mirror.cocurvature,
        target.curvature + factor * mirror.curvature,
        target.kx + factor * mirror.kx,
        target.ky + factor * mirror.ky,
    )


def dual_circle(quartet: Quartet, j: int) -> InversiveCircle:
    """The dual circle D_j through the three tangency points of the circles
    other than j: D_j = (va + vb + vc − vj)/2.

    D_j is orthogonal to va, vb, vc (B = 0) and satisfies Q(D_j) = −1;
    inversion in D_j realizes the swap Sj as a Möbius action on the whole
    plane (invert(D_j, vj) == reflect(quartet, j)). The four D_j generate the
    dual Apollonian group; for integral packings their coordinates are
    half-integers.
    """
    if not 0 <= j <= 3:
        raise ValueError(f"Quartet index must be 0-3, got {j}")
    from fractions import Fraction

    vj = quartet[j]
    a, b, c = (quartet[m] for m in range(4) if m != j)
    half = Fraction(1, 2)
    return InversiveCircle(
        (a.cocurvature + b.cocurvature + c.cocurvature - vj.cocurvature) * half,
        (a.curvature + b.curvature + c.curvature - vj.curvature) * half,
        (a.kx + b.kx + c.kx - vj.kx) * half,
        (a.ky + b.ky + c.ky - vj.ky) * half,
    )
