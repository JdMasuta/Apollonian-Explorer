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

#: Denominator bound for lossy float -> fraction conversion. 10^15 captures
#: the full precision of the float64 mirrors, which the frontend's exact
#: (BigInt rational) camera needs for deep zoom.
MAX_DENOMINATOR = 10**15


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
    """Serialize a walk record to the API circle shape (lines unsupported).

    Exactness is decided per component: e.g. the (1,1,1) packing has rational
    bends but irrational centers, so curvature/radius serialize exactly while
    the center falls back to the float mirrors.
    """
    circle = record.circle
    if circle.is_line:
        raise ValueError("Lines cannot be serialized to the circle API shape")

    b = circle.curvature
    b_rational = isinstance(b, (int, Fraction))
    if b_rational:
        b_frac = Fraction(b)
        r_frac = 1 / b_frac  # signed, matching the legacy contract
    else:
        b_frac = Fraction(record.curvature_f).limit_denominator(MAX_DENOMINATOR)
        r_frac = 1 / b_frac if b_frac != 0 else Fraction(0)

    if b_rational and isinstance(circle.kx, (int, Fraction)):
        x_frac = Fraction(circle.kx) / b_frac
    else:
        x_frac = Fraction(record.x_f or 0.0).limit_denominator(MAX_DENOMINATOR)
    if b_rational and isinstance(circle.ky, (int, Fraction)):
        y_frac = Fraction(circle.ky) / b_frac
    else:
        y_frac = Fraction(record.y_f or 0.0).limit_denominator(MAX_DENOMINATOR)

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

    # Exactness per component (e.g. (1,1,1): rational bends, irrational centers)
    b_rational = _parse_rational(row.curvature_exact)
    kx_rational = _parse_rational(row.kx_exact)
    ky_rational = _parse_rational(row.ky_exact)

    if b_rational is not None and b_rational != 0:
        b_frac = b_rational
        r_frac = 1 / b_rational
    else:
        b_frac = Fraction(row.b_f).limit_denominator(MAX_DENOMINATOR)
        r_frac = 1 / b_frac if b_frac != 0 else Fraction(0)

    if b_rational is not None and b_rational != 0 and kx_rational is not None:
        x_frac = kx_rational / b_rational
    else:
        x_frac = Fraction(row.x_f or 0.0).limit_denominator(MAX_DENOMINATOR)
    if b_rational is not None and b_rational != 0 and ky_rational is not None:
        y_frac = ky_rational / b_rational
    else:
        y_frac = Fraction(row.y_f or 0.0).limit_denominator(MAX_DENOMINATOR)

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


def parse_exact(value: str):
    """Parse a stored canonical exact string back to int/Fraction/SymPy."""
    try:
        frac = Fraction(value)
        return frac.numerator if frac.denominator == 1 else frac
    except (ValueError, ZeroDivisionError):
        import sympy as sp

        return sp.sympify(value)


def row_to_inversive(row: Circle):
    """Reconstruct the exact inversive vector from a schema-v2 row."""
    from core.engine.inversive import InversiveCircle

    return InversiveCircle(
        parse_exact(row.cocurvature_exact),
        parse_exact(row.curvature_exact),
        parse_exact(row.kx_exact),
        parse_exact(row.ky_exact),
    )


def vec_to_api_line(circle, word: str, generation: int) -> Dict[str, object]:
    """Serialize a line (b = 0) to the additive 'line' wire shape.

    Inversive line vector: (2d, 0, nx, ny) for the line <p, n> = d.
    """
    def frac_str_of(value: Exact, mirror: float) -> str:
        frac = _exact_or_float(value, mirror)
        return _frac_str(frac)

    nx_f = float(circle.kx)
    ny_f = float(circle.ky)
    if isinstance(circle.cocurvature, (int, Fraction)):
        d_value: Exact = Fraction(circle.cocurvature) / 2
    else:
        d_value = circle.cocurvature / 2
    return {
        "kind": "line",
        "id": None,
        "curvature": "0/1",
        "center": {"x": "0/1", "y": "0/1"},
        "radius": "0/1",
        "normal": {"x": frac_str_of(circle.kx, nx_f), "y": frac_str_of(circle.ky, ny_f)},
        "offset": frac_str_of(d_value, float(circle.cocurvature) / 2.0),
        "generation": generation,
        "word": word,
        "parent_ids": [],
        "tangent_ids": [],
    }


def record_to_api(record: GeneratedCircle, circle_id: Optional[int] = None) -> Dict[str, object]:
    """Serialize any walk record (circle or line) to its wire shape."""
    if record.circle.is_line:
        return vec_to_api_line(record.circle, db_word(record), record.generation)
    payload = record_to_api_circle(record, circle_id)
    payload["kind"] = "circle"
    return payload
