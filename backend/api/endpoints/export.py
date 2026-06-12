"""
Research data export endpoints.

Reference: REVAMP_BLUEPRINT.md Phase 2.4 / Milestone 2.

GET /api/gaskets/{id}/export?format=csv|json streams the full circle table
(exact strings + float mirrors + number-theoretic tags) for analysis in
Pandas, Mathematica, etc. Responses are streamed row-by-row so large packings
do not buffer in memory.
"""

import csv
import io
import json
from fractions import Fraction
from typing import Iterator, Optional

import sympy as sp
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import get_db
from core.engine import ENGINE_VERSION
from db import Circle, Gasket

router = APIRouter()

COLUMNS = [
    "id",
    "generation",
    "word",
    "is_line",
    "curvature_exact",
    "cocurvature_exact",
    "kx_exact",
    "ky_exact",
    "curvature_float",
    "x_float",
    "y_float",
    "radius_float",
    "residue_24",
    "is_prime_bend",
]


def _integer_bend(curvature_exact: str) -> Optional[int]:
    """Integral bend from a canonical exact string, else None."""
    try:
        frac = Fraction(curvature_exact)
    except (ValueError, ZeroDivisionError):
        return None
    if frac.denominator != 1:
        return None
    return frac.numerator


def _row_values(circle: Circle) -> dict:
    bend = _integer_bend(circle.curvature_exact)
    return {
        "id": circle.id,
        "generation": circle.generation,
        "word": circle.word,
        "is_line": circle.is_line,
        "curvature_exact": circle.curvature_exact,
        "cocurvature_exact": circle.cocurvature_exact,
        "kx_exact": circle.kx_exact,
        "ky_exact": circle.ky_exact,
        "curvature_float": circle.b_f,
        "x_float": circle.x_f,
        "y_float": circle.y_f,
        "radius_float": circle.r_f,
        "residue_24": bend % 24 if bend is not None else None,
        "is_prime_bend": bool(sp.isprime(abs(bend))) if bend is not None else None,
    }


def _iter_csv(circles) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    yield buffer.getvalue()
    for circle in circles:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(_row_values(circle))
        yield buffer.getvalue()


def _iter_json(gasket: Gasket, circles) -> Iterator[str]:
    # Reproducibility metadata: seed + engine version + generation budget.
    header = {
        "gasket_id": gasket.id,
        "initial_curvatures": json.loads(gasket.initial_curvatures),
        "engine_version": ENGINE_VERSION,
        "max_depth_cached": gasket.max_depth_cached,
        "min_radius_cached": gasket.min_radius_cached,
    }
    yield json.dumps(header)[:-1] + ', "circles": ['

    first = True
    for circle in circles:
        prefix = "" if first else ","
        first = False
        yield prefix + json.dumps(_row_values(circle))
    yield "]}"


@router.get("/gaskets/{gasket_id}/export")
def export_gasket(
    gasket_id: int,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
):
    """Stream the circle table of a cached gasket as CSV or JSON."""
    gasket = db.query(Gasket).filter(Gasket.id == gasket_id).first()
    if not gasket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "GASKET_NOT_FOUND", "message": f"Gasket {gasket_id} not found"},
        )

    circles = (
        db.query(Circle)
        .filter(Circle.gasket_id == gasket_id)
        .order_by(Circle.generation, Circle.id)
        .yield_per(1000)
    )

    if format == "csv":
        return StreamingResponse(
            _iter_csv(circles),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="gasket_{gasket_id}.csv"'
            },
        )
    return StreamingResponse(
        _iter_json(gasket, circles),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="gasket_{gasket_id}.json"'
        },
    )
