"""
Gasket service layer with business logic and caching (schema v2).

Reference: REVAMP_BLUEPRINT.md Milestone 2; .DESIGN_SPEC.md section 9.1
(hash-based caching strategy).

Generation runs on the exact inversive-coordinate engine (core.engine);
circles persist in their native representation (group word + exact
coordinates + float mirrors, see db/models/circle.py). The cache is
resolution-aware: a cached gasket covers a request when it was generated at
least as deep AND at least as fine a resolution as requested.
"""

import hashlib
import json
from datetime import datetime
from fractions import Fraction
from typing import List, Optional

from sqlalchemy.orm import Session

from core.engine.seeds import seed_from_quadruple, seed_from_triple
from core.engine.walk import WalkBudget, walk
from core.exact_math import ExactNumber
from db import Circle, Gasket
from schemas import CircleResponse, GasketResponse
from services.serializers import record_to_row, row_to_response


def parse_curvature_string(s: str) -> ExactNumber:
    """Parse a curvature string to int (when integral) or Fraction."""
    frac = Fraction(s)
    if frac.denominator == 1:
        return frac.numerator
    return frac


def build_seed(curvatures: List[ExactNumber]):
    """Build a root quartet from 3 (completed) or 4 (validated) curvatures.

    Raises:
        ValueError: for invalid counts, unrealizable triples, or invalid
            quadruples (clear messages from core.engine.seeds).
    """
    if len(curvatures) == 3:
        return seed_from_triple(curvatures[0], curvatures[1], curvatures[2])
    if len(curvatures) == 4:
        return seed_from_quadruple(
            curvatures[0], curvatures[1], curvatures[2], curvatures[3]
        )
    raise ValueError(f"Need 3 or 4 initial curvatures, got {len(curvatures)}")


class GasketService:
    """Service for gasket operations with resolution-aware caching."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Create / retrieve
    # ------------------------------------------------------------------

    def create_or_get_gasket(
        self,
        curvatures: List[str],
        max_depth: int,
        min_radius: Optional[float] = None,
    ) -> GasketResponse:
        """Create or retrieve a gasket from cache.

        A cached gasket covers the request when it was generated at least as
        deep (max_depth) and at least as fine (min_radius) as requested;
        otherwise it is regenerated.
        """
        gasket_hash = self._generate_hash(curvatures)

        existing = self.db.query(Gasket).filter(Gasket.hash == gasket_hash).first()
        if existing:
            if self._covers(existing, max_depth, min_radius):
                existing.access_count += 1
                existing.last_accessed_at = datetime.utcnow()
                # Build the response BEFORE committing: commit() expires ORM
                # attributes (ISSUES.md Issue #1).
                response = self._gasket_to_response(existing, max_depth, min_radius)
                self.db.commit()
                return response
            # Insufficient depth/resolution: regenerate (MVP cache policy)
            self.db.delete(existing)
            self.db.commit()

        gasket = self._generate_and_persist(curvatures, max_depth, min_radius, gasket_hash)
        return self._gasket_to_response(gasket, max_depth, min_radius)

    def get_gasket(self, gasket_id: int) -> Optional[GasketResponse]:
        """Retrieve a gasket by ID with all cached circles."""
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return None

        gasket.access_count += 1
        gasket.last_accessed_at = datetime.utcnow()
        # Response before commit (ISSUES.md Issue #1).
        response = self._gasket_to_response(
            gasket, gasket.max_depth_cached or 0, gasket.min_radius_cached
        )
        self.db.commit()
        return response

    def get_circles_in_viewport(
        self,
        gasket_id: int,
        min_x: Optional[float] = None,
        max_x: Optional[float] = None,
        min_y: Optional[float] = None,
        max_y: Optional[float] = None,
        min_radius: Optional[float] = None,
        limit: int = 20000,
    ) -> Optional[List[CircleResponse]]:
        """Cached circles intersecting a viewport rectangle, above a resolution.

        Filters on the indexed float mirrors; a circle intersects the bbox iff
        its disk overlaps the rectangle. Lines are excluded from bbox queries.

        Returns None when the gasket does not exist.
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return None

        query = self.db.query(Circle).filter(
            Circle.gasket_id == gasket_id, Circle.is_line.is_(False)
        )
        if min_radius is not None:
            query = query.filter(Circle.r_f >= min_radius)
        if min_x is not None:
            query = query.filter(Circle.x_f + Circle.r_f >= min_x)
        if max_x is not None:
            query = query.filter(Circle.x_f - Circle.r_f <= max_x)
        if min_y is not None:
            query = query.filter(Circle.y_f + Circle.r_f >= min_y)
        if max_y is not None:
            query = query.filter(Circle.y_f - Circle.r_f <= max_y)

        rows = query.order_by(Circle.generation, Circle.id).limit(limit).all()
        return [row_to_response(row) for row in rows]

    def delete_gasket(self, gasket_id: int) -> bool:
        """Delete a gasket and its circles. True if a gasket was deleted."""
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return False
        self.db.delete(gasket)
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _covers(gasket: Gasket, max_depth: int, min_radius: Optional[float]) -> bool:
        """Does the cached generation cover the requested depth/resolution?"""
        if (gasket.max_depth_cached or 0) < max_depth:
            return False
        cached_resolution = gasket.min_radius_cached or 0.0
        requested_resolution = min_radius or 0.0
        return cached_resolution <= requested_resolution

    def _generate_hash(self, curvatures: List[str]) -> str:
        """SHA-256 cache key over the sorted, canonicalized curvatures."""
        fracs = sorted(Fraction(c) for c in curvatures)
        canonical = ",".join(f"{f.numerator}/{f.denominator}" for f in fracs)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _generate_and_persist(
        self,
        curvatures: List[str],
        max_depth: int,
        min_radius: Optional[float],
        gasket_hash: str,
    ) -> Gasket:
        """Run the engine walk and persist the packing (schema v2)."""
        parsed = [parse_curvature_string(c) for c in curvatures]
        seed = build_seed(parsed)
        budget = WalkBudget(max_depth=max_depth, min_radius=min_radius)
        records = list(walk(seed, budget))

        gasket = Gasket(
            hash=gasket_hash,
            initial_curvatures=json.dumps(curvatures),
            num_circles=len(records),
            max_depth_cached=max_depth,
            min_radius_cached=min_radius,
            access_count=1,
        )
        self.db.add(gasket)
        self.db.flush()  # obtain gasket.id

        for record in records:
            self.db.add(record_to_row(record, gasket.id))

        self.db.commit()
        return gasket

    def _gasket_to_response(
        self, gasket: Gasket, max_depth: int, min_radius: Optional[float]
    ) -> GasketResponse:
        """Serialize a gasket with circles filtered to the requested budget."""
        circles = [
            row_to_response(row)
            for row in gasket.circles
            if row.generation <= max_depth
            and not row.is_line
            and (min_radius is None or (row.r_f or 0.0) >= min_radius)
        ]

        return GasketResponse(
            id=gasket.id,
            hash=gasket.hash,
            initial_curvatures=json.loads(gasket.initial_curvatures),
            num_circles=len(circles),
            max_depth_cached=gasket.max_depth_cached,
            created_at=gasket.created_at.isoformat() if gasket.created_at else "",
            last_accessed_at=(
                gasket.last_accessed_at.isoformat() if gasket.last_accessed_at else None
            ),
            access_count=gasket.access_count,
            circles=circles,
        )
