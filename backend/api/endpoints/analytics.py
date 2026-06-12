"""
Research analytics endpoints.

Reference: REVAMP_BLUEPRINT.md Phase 2.4 / Milestone 2.

GET /api/gaskets/{id}/analytics returns:
- a curvature (bend) histogram,
- the counting function N(T) = #{circles : bend <= T} on log-spaced T,
- a least-squares estimate of the growth exponent delta from
  log N(T) ~ delta * log T + c. For Apollonian packings, N(T) ~ c·T^δ with
  δ ≈ 1.305688 — the packing's Hausdorff dimension (Kontorovich-Oh;
  McMullen's value). The estimate converges from below at modest T.
"""

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db
from db import Circle, Gasket

router = APIRouter()

#: McMullen's value for the Hausdorff dimension of the Apollonian gasket.
DELTA_REFERENCE = 1.305688


def _fit_exponent(bends: List[float], t_values: List[float]) -> Optional[float]:
    """Least-squares slope of log N(T) vs log T (None if degenerate)."""
    points = []
    n = len(bends)
    index = 0
    for t in t_values:
        while index < n and bends[index] <= t:
            index += 1
        if index > 0 and t > 0:
            points.append((math.log(t), math.log(index)))
    if len(points) < 2:
        return None
    mean_x = sum(p[0] for p in points) / len(points)
    mean_y = sum(p[1] for p in points) / len(points)
    sxx = sum((p[0] - mean_x) ** 2 for p in points)
    if sxx == 0:
        return None
    sxy = sum((p[0] - mean_x) * (p[1] - mean_y) for p in points)
    return sxy / sxx


@router.get("/gaskets/{gasket_id}/analytics")
def get_analytics(
    gasket_id: int,
    bins: int = Query(default=20, ge=2, le=200),
    t_points: int = Query(default=24, ge=4, le=200),
    db: Session = Depends(get_db),
):
    """Curvature statistics for a cached gasket (positive bends only)."""
    gasket = db.query(Gasket).filter(Gasket.id == gasket_id).first()
    if not gasket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket {gasket_id} not found"},
        )

    rows = (
        db.query(Circle.b_f, Circle.generation)
        .filter(Circle.gasket_id == gasket_id, Circle.b_f > 0)
        .order_by(Circle.b_f)
        .all()
    )
    bends = [row[0] for row in rows]
    max_generation = max((row[1] for row in rows), default=0)
    if not bends:
        return {
            "gasket_id": gasket_id,
            "total_circles": 0,
            "histogram": {"bin_edges": [], "counts": []},
            "counting_function": [],
            "dimension_estimate": None,
            "dimension_reference": DELTA_REFERENCE,
        }

    # Histogram over [min, max] with uniform bins
    low, high = bends[0], bends[-1]
    width = (high - low) / bins if high > low else 1.0
    counts = [0] * bins
    for b in bends:
        slot = min(int((b - low) / width), bins - 1) if high > low else 0
        counts[slot] += 1
    bin_edges = [low + i * width for i in range(bins + 1)]

    # Counting function N(T) on log-spaced T values
    t_values = [
        math.exp(math.log(max(low, 1e-9)) + (math.log(high) - math.log(max(low, 1e-9))) * i / (t_points - 1))
        for i in range(t_points)
    ] if high > low else [high]
    # exp/log round-off can land the last T just below the max bend;
    # pin it so N(T_max) counts every circle.
    t_values[-1] = high
    counting = []
    index = 0
    for t in t_values:
        while index < len(bends) and bends[index] <= t:
            index += 1
        counting.append({"T": t, "N": index})

    # Exponent fit window: the cache is truncated, so N(T) saturates (or,
    # after local cusp/deepen refinements, over-densifies) at large T. The
    # enumeration is provably COMPLETE for bends below 1/min_radius_cached
    # (resolution pruning keeps every circle above that radius), so prefer
    # that bound; fall back to the depth heuristic (min bend of the deepest
    # generation) for unpruned caches.
    if gasket.min_radius_cached:
        t_complete = 1.0 / gasket.min_radius_cached
    else:
        t_complete = min(
            (row[0] for row in rows if row[1] == max_generation), default=high
        )
    fit_ts = [t for t in t_values if low < t <= t_complete]
    estimate = _fit_exponent(bends, fit_ts or t_values)

    return {
        "gasket_id": gasket_id,
        "total_circles": len(bends),
        "histogram": {"bin_edges": bin_edges, "counts": counts},
        "counting_function": counting,
        "dimension_estimate": estimate,
        "dimension_reference": DELTA_REFERENCE,
    }
