"""
Research metrics over generated circles.

Reference: REVAMP_BLUEPRINT.md Phase 2.3 (coloring metrics) and 2.4
(analytics). This module hosts the backend-computed per-circle scalars used
for coloring and statistics. It is intentionally small in Milestone 1 and
grows in Milestone 4 (histograms, N(T), Hausdorff-dimension fit).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

import sympy as sp

from core.engine.inversive import InversiveCircle


def integer_bend(circle: InversiveCircle) -> Optional[int]:
    """The curvature as an int when it is exactly integral, else None."""
    b = circle.curvature
    if isinstance(b, int):
        return b
    if isinstance(b, Fraction) and b.denominator == 1:
        return b.numerator
    if isinstance(b, sp.Expr):
        simplified = sp.simplify(b)
        if isinstance(simplified, sp.Integer):
            return int(simplified)
    return None


def bend_residue(circle: InversiveCircle, modulus: int) -> Optional[int]:
    """Curvature residue mod ``modulus`` for integral bends, else None.

    Residues mod 24 classify the admissible bends of a primitive integral
    packing (the local-global phenomenon).
    """
    if modulus <= 0:
        raise ValueError(f"Modulus must be positive, got {modulus}")
    bend = integer_bend(circle)
    if bend is None:
        return None
    return bend % modulus


def is_prime_bend(circle: InversiveCircle) -> Optional[bool]:
    """True/False for integral bends (primality of |bend|), None otherwise."""
    bend = integer_bend(circle)
    if bend is None:
        return None
    return bool(sp.isprime(abs(bend)))
