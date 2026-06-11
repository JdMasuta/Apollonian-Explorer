"""
Bridge from the exact engine (core.engine) to the legacy CircleData pipeline.

Reference: REVAMP_BLUEPRINT.md Milestone 2 (first slice).

The service layer and WebSocket endpoint historically consumed
``core.gasket_generator.generate_apollonian_gasket``, which yields
``CircleData`` objects. This module provides the same shape of stream backed
by the inversive-coordinate engine, so persistence and serialization keep
working unchanged while generation becomes exact, duplicate-free, and orders
of magnitude faster (ISSUES.md #2, #3, #5).

This adapter is temporary: schema v2 (Milestone 2 proper) will persist
inversive coordinates and group words directly, at which point CircleData
and this bridge are retired.

Semantics versus the legacy generator:
- 3 curvatures: the triple is completed via the Descartes relation (the minus
  branch, which yields the enclosing circle when one exists) and the quartet
  is placed canonically. The other completion appears as a generation-1
  reflection, so coverage is identical; only generation labels shift.
- 4 curvatures: now fully supported (the legacy path raised
  NotImplementedError). The quadruple must satisfy the Descartes relation.
- generation = reduced word length in the Apollonian group (0 for the seed).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, Iterator, Sequence

import sympy as sp

from core.circle_data import CircleData
from core.engine.inversive import Exact
from core.engine.seeds import seed_from_quadruple, seed_from_triple
from core.engine.walk import WalkBudget, walk


def _approx_fraction(value: Exact, max_denom: int = 10**9) -> Fraction:
    """Fraction view of an exact scalar; lossy for irrationals.

    Equivalent in format to exact_math.to_fraction_lossy but without any
    sympy.simplify call — a single evalf for SymPy scalars. This matters:
    the legacy helpers spend ~0.2s per circle in simplify() (see ERR-009).
    """
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    return Fraction(float(value)).limit_denominator(max_denom)


def _tagged(value: Exact) -> str:
    """Tagged exact string ('int:6' / 'frac:3/2' / 'sym:...') without simplify."""
    if isinstance(value, int):
        return f"int:{value}"
    if isinstance(value, Fraction):
        return f"frac:{value.numerator}/{value.denominator}"
    return f"sym:{value}"


class EngineCircleData(CircleData):
    """CircleData with serialization that never calls sympy.simplify.

    The legacy CircleData.to_dict/to_database_dict route every scalar through
    exact_math helpers that invoke simplify() repeatedly (~0.2s per circle for
    irrational values). Engine output is already in normal form, so this
    subclass serializes directly; behaviorally the formats are identical.
    """

    def radius(self) -> Exact:
        """Signed radius 1/k, matching legacy CircleData semantics."""
        b = self.curvature
        if isinstance(b, (int, Fraction)):
            r = Fraction(1) / b
            return r.numerator if r.denominator == 1 else r
        return sp.Integer(1) / b

    def to_dict(self) -> Dict:
        x, y = self.center
        radius = self.radius()

        def unified(value: Exact) -> str:
            frac = _approx_fraction(value)
            return f"{frac.numerator}/{frac.denominator}"

        return {
            "id": self.id,
            "curvature": unified(self.curvature),
            "center": {"x": unified(x), "y": unified(y)},
            "radius": unified(radius),
            "generation": self.generation,
            "parent_ids": self.parent_ids.copy(),
            "tangent_ids": self.tangent_ids.copy(),
        }

    def to_database_dict(self) -> Dict:
        x, y = self.center
        radius = self.radius()

        curvature_frac = _approx_fraction(self.curvature)
        x_frac = _approx_fraction(x)
        y_frac = _approx_fraction(y)
        radius_frac = _approx_fraction(radius)

        return {
            # INTEGER columns (lossy for irrationals, for indexing)
            "curvature_num": curvature_frac.numerator,
            "curvature_denom": curvature_frac.denominator,
            "center_x_num": x_frac.numerator,
            "center_x_denom": x_frac.denominator,
            "center_y_num": y_frac.numerator,
            "center_y_denom": y_frac.denominator,
            "radius_num": radius_frac.numerator,
            "radius_denom": radius_frac.denominator,
            # TEXT columns (exact, for reconstruction)
            "curvature_exact": _tagged(self.curvature),
            "center_x_exact": _tagged(x),
            "center_y_exact": _tagged(y),
            "radius_exact": _tagged(radius),
        }


def generate_circles(
    curvatures: Sequence[Exact],
    max_depth: int,
    max_circles: int | None = None,
) -> Iterator[CircleData]:
    """Generate a packing as a stream of CircleData via the exact engine.

    Args:
        curvatures: 3 curvatures (completed via Descartes) or 4 curvatures
            (validated as a Descartes quadruple). int, Fraction, or exact
            SymPy values.
        max_depth: maximum generation (reduced word length).
        max_circles: optional hard cap on circles yielded.

    Yields:
        CircleData with exact curvature/center and generation set; parent and
        tangent ids are left empty (schema v2 will carry group words instead).

    Raises:
        ValueError: for invalid counts, non-realizable triples (negative
            discriminant), or invalid quadruples.
    """
    if len(curvatures) == 3:
        seed = seed_from_triple(curvatures[0], curvatures[1], curvatures[2])
    elif len(curvatures) == 4:
        seed = seed_from_quadruple(curvatures[0], curvatures[1], curvatures[2], curvatures[3])
    else:
        raise ValueError(f"Need 3 or 4 initial curvatures, got {len(curvatures)}")

    budget = WalkBudget(max_depth=max_depth, max_circles=max_circles)
    for record in walk(seed, budget):
        circle = record.circle
        if circle.is_line:
            # Lines cannot be represented by CircleData; they only arise from
            # strip seeds, which are not reachable through this adapter
            # (zero curvatures are rejected upstream). Defensive skip.
            continue
        x, y = circle.center()
        yield EngineCircleData(
            curvature=circle.curvature,
            center=(x, y),
            generation=record.generation,
            parent_ids=[],
        )
