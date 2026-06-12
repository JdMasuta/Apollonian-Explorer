"""
Serialization between engine records, schema-v2 rows, and API responses.

Reference: REVAMP_BLUEPRINT.md Milestone 2.

The wire format is unchanged from v1 (every numeric field a "num/denom"
string — see backend/tests/test_ws_contract.py and the frontend TypeScript
interfaces in websocketService.ts), with one additive field: ``word``.

Exactness policy:
- rational scalars (int/Fraction) serialize exactly;
- irrational scalars use the walk's float mirrors (a single
  ``limit_denominator``; never a per-circle SymPy ``evalf`` — ERR-009/014).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, Optional

from core.engine.inversive import Exact, exact_str
from core.engine.walk import GeneratedCircle
from db.models.circle import Circle
from schemas import CircleResponse

#: Denominator bound for lossy float -> fraction conversion.
MAX_DENOMINATOR = 10**9


def db_word(record: GeneratedCircle) -> str:
    """Unique-per-gasket identity: 'S0'..'S3' for seeds, the reduced word otherwise."""
    if record.generation == 0:
        return f"S{record.seed_index}"
    return record.word


def _frac_str(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _exact_or_float(value: Exact, mirror: float) -> Fraction:
    """Exact Fraction for rational scalars, float-mirror approximation otherwise."""
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    return Fraction(mirror).limit_denominator(MAX_DENOMINATOR)


def record_to_api_circle(
    record: GeneratedCircle, circle_id: Optional[int] = None
) -> Dict[str, object]:
    """Serialize a walk record to the API circle shape (lines unsupported)."""
    circle = record.circle
    if circle.is_line:
        raise ValueError("Lines cannot be serialized to the circle API shape")

    b = circle.curvature
    if isinstance(b, (int, Fraction)):
        b_frac = Fraction(b)
        x, y = circle.center()
        x_frac = Fraction(x)
        y_frac = Fraction(y)
        r_frac = 1 / b_frac  # signed, matching the legacy contract
    else:
        b_frac = Fraction(record.curvature_f).limit_denominator(MAX_DENOMINATOR)
        x_frac = Fraction(record.x_f or 0.0).limit_denominator(MAX_DENOMINATOR)
        y_frac = Fraction(record.y_f or 0.0).limit_denominator(MAX_DENOMINATOR)
        r_frac = 1 / b_frac if b_frac != 0 else Fraction(0)

    return {
        "id": circle_id,
        "curvature": _frac_str(b_frac),
        "center": {"x": _frac_str(x_frac), "y": _frac_str(y_frac)},
        "radius": _frac_str(r_frac),
        "generation": record.generation,
        "word": db_word(record),
        "parent_ids": [],
        "tangent_ids": [],
    }


def record_to_row(record: GeneratedCircle, gasket_id: int) -> Circle:
    """Build a schema-v2 Circle row from a walk record."""
    circle = record.circle
    return Circle(
        gasket_id=gasket_id,
        generation=record.generation,
        word=db_word(record),
        is_line=circle.is_line,
        cocurvature_exact=exact_str(circle.cocurvature),
        curvature_exact=exact_str(circle.curvature),
        kx_exact=exact_str(circle.kx),
        ky_exact=exact_str(circle.ky),
        b_f=record.curvature_f,
        x_f=record.x_f,
        y_f=record.y_f,
        r_f=record.r_f,
    )


def _parse_rational(exact: str) -> Optional[Fraction]:
    """Fraction for canonical rational strings ('6', '-3/2'); None for SymPy."""
    try:
        return Fraction(exact)
    except (ValueError, ZeroDivisionError):
        return None


def row_to_response(row: Circle) -> CircleResponse:
    """Serialize a schema-v2 row to the API response shape (lines unsupported)."""
    if row.is_line:
        raise ValueError("Lines cannot be serialized to the circle API shape")

    b_rational = _parse_rational(row.curvature_exact)
    kx_rational = _parse_rational(row.kx_exact)
    ky_rational = _parse_rational(row.ky_exact)

    if b_rational is not None and b_rational != 0 and kx_rational is not None and ky_rational is not None:
        b_frac = b_rational
        x_frac = kx_rational / b_rational
        y_frac = ky_rational / b_rational
        r_frac = 1 / b_rational
    else:
        b_frac = Fraction(row.b_f).limit_denominator(MAX_DENOMINATOR)
        x_frac = Fraction(row.x_f or 0.0).limit_denominator(MAX_DENOMINATOR)
        y_frac = Fraction(row.y_f or 0.0).limit_denominator(MAX_DENOMINATOR)
        r_frac = 1 / b_frac if b_frac != 0 else Fraction(0)

    return CircleResponse(
        id=row.id,
        curvature=_frac_str(b_frac),
        center={"x": _frac_str(x_frac), "y": _frac_str(y_frac)},
        radius=_frac_str(r_frac),
        generation=row.generation,
        word=row.word,
        parent_ids=[],
        tangent_ids=[],
    )
