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

from core.engine.cusp import cusp_chain
from core.engine.group import invert
from core.engine.seeds import seed_from_quadruple, seed_from_triple, seed_strip
from core.engine.walk import WalkBudget, replay_word, walk
from core.exact_math import ExactNumber
from db import Circle, Gasket
from schemas import CircleResponse, GasketResponse
from services.serializers import (
    db_word,
    record_to_api,
    record_to_api_circle,
    record_to_row,
    row_to_inversive,
    row_to_response,
    vec_to_api_line,
)

def _float_frac_str(value: float) -> str:
    frac = Fraction(value).limit_denominator(10**15)
    return f"{frac.numerator}/{frac.denominator}"


#: Hard cap on circles a single deepen request may produce (server defense
#: against shallow-word + deep-resolution requests).
DEEPEN_MAX_CIRCLES = 30000


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
        if sorted(curvatures, key=float) == [0, 0, 1, 1]:
            # The Apollonian strip: two parallel lines + two unit circles.
            return seed_strip()
        return seed_from_quadruple(
            curvatures[0], curvatures[1], curvatures[2], curvatures[3]
        )
    raise ValueError(f"Need 3 or 4 initial curvatures, got {len(curvatures)}")


def persist_walk_records(
    curvatures: List[str],
    max_depth: int,
    min_radius: Optional[float],
    records: list,
) -> Optional[int]:
    """Persist a completed WebSocket run (worker thread; own session).

    Cache-aware: if a gasket with the same curvature hash exists, only new
    words are inserted. Coverage metadata merges conservatively (max depth,
    COARSER resolution), which never over-claims coverage. Returns the
    gasket id, or None if persistence failed (streaming already succeeded;
    persistence is best-effort).
    """
    from db.base import SessionLocal

    session = SessionLocal()
    try:
        service = GasketService(session)
        gasket_hash = service._generate_hash(curvatures)
        gasket = session.query(Gasket).filter(Gasket.hash == gasket_hash).first()

        if gasket is None:
            gasket = Gasket(
                hash=gasket_hash,
                initial_curvatures=json.dumps(curvatures),
                num_circles=0,
                max_depth_cached=max_depth,
                min_radius_cached=min_radius,
                access_count=1,
            )
            session.add(gasket)
            session.flush()
            existing_words: set = set()
        else:
            if service._covers(gasket, max_depth, min_radius):
                gasket.access_count += 1
                gasket.last_accessed_at = datetime.utcnow()
                gasket_id = gasket.id
                session.commit()
                return gasket_id
            existing_words = {
                row[0]
                for row in session.query(Circle.word).filter(Circle.gasket_id == gasket.id)
            }
            gasket.max_depth_cached = max(gasket.max_depth_cached or 0, max_depth)
            if gasket.min_radius_cached is None or min_radius is None:
                # One of the budgets was unpruned: the merged cache is only
                # safely claimable at the coarser (pruned) resolution unless
                # both were unpruned.
                merged = None if (gasket.min_radius_cached is None and min_radius is None) else (
                    min_radius if gasket.min_radius_cached is None else gasket.min_radius_cached
                )
                gasket.min_radius_cached = merged
            else:
                gasket.min_radius_cached = max(gasket.min_radius_cached, min_radius)

        added = 0
        for record in records:
            if db_word(record) in existing_words:
                continue
            session.add(record_to_row(record, gasket.id))
            added += 1
        gasket.num_circles = (gasket.num_circles or 0) + added
        gasket_id = gasket.id
        session.commit()
        return gasket_id
    except Exception:
        # Best-effort: streaming already succeeded. But never silently —
        # a persistence bug otherwise hides behind gasket_id = null.
        import logging
        import traceback

        logging.getLogger("apollonian.persist").error(
            "WS persistence failed:\n%s", traceback.format_exc()
        )
        session.rollback()
        return None
    finally:
        session.close()


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
        include_circles: bool = True,
    ) -> GasketResponse:
        """Create or retrieve a gasket from cache.

        A cached gasket covers the request when it was generated at least as
        deep (max_depth) and at least as fine (min_radius) as requested.
        When coverage is insufficient, the cache is expanded INCREMENTALLY:
        the walk reruns with the union budget and only circles with new
        group words are inserted (UNIQUE(gasket_id, word) is the identity).

        Args:
            include_circles: when False, the response carries no circle list
                (used by the deepening flow, which follows up with a
                viewport query instead of downloading the whole packing).
        """
        gasket_hash = self._generate_hash(curvatures)

        existing = self.db.query(Gasket).filter(Gasket.hash == gasket_hash).first()
        if existing:
            if not self._covers(existing, max_depth, min_radius):
                self._expand(existing, curvatures, max_depth, min_radius)
            existing.access_count += 1
            existing.last_accessed_at = datetime.utcnow()
            # Build the response BEFORE committing: commit() expires ORM
            # attributes (ISSUES.md Issue #1).
            response = self._gasket_to_response(
                existing, max_depth, min_radius, include_circles
            )
            self.db.commit()
            return response

        gasket = self._generate_and_persist(curvatures, max_depth, min_radius, gasket_hash)
        return self._gasket_to_response(gasket, max_depth, min_radius, include_circles)

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

    def deepen(
        self,
        gasket_id: int,
        word: str,
        min_radius: float,
        max_extra_depth: int = 24,
    ) -> Optional[dict]:
        """Locally refine the packing around a cached circle.

        Resumes the walk at the tree node identified by ``word`` (schema v2
        words ARE the tree addresses) with a resolution budget. This is how
        deep zoom stays output-sensitive: a GLOBAL resolution of epsilon
        costs ~(1/eps)^1.3057 circles, but the subtree below a
        viewport-scale circle at the same epsilon is bounded by the
        viewport/pixel ratio (REVAMP_BLUEPRINT.md M3).

        New circles are persisted (word-deduplicated); ALL subtree circles
        within the budget are returned so the client gets the full local
        picture without a second query.

        Returns None when the gasket doesn't exist; raises ValueError for
        invalid words.
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return None

        curvatures = json.loads(gasket.initial_curvatures)
        parsed = [parse_curvature_string(c) for c in curvatures]
        seed = build_seed(parsed)

        # Seed words (S0..S3) have no subtree address: walk from the root.
        start_word = "" if word.startswith("S") else word
        if start_word:
            # Fail fast on malformed words (replay also validates).
            replay_word(seed, start_word)

        absolute_depth = min(len(start_word) + max_extra_depth, 120)
        budget = WalkBudget(
            max_depth=absolute_depth,
            min_radius=min_radius,
            max_circles=DEEPEN_MAX_CIRCLES,
        )
        records = list(walk(seed, budget, start_word=start_word))
        truncated = len(records) >= DEEPEN_MAX_CIRCLES

        word_query = self.db.query(Circle.word).filter(Circle.gasket_id == gasket.id)
        if start_word:
            word_query = word_query.filter(Circle.word.like(f"{start_word}%"))
        existing_words = {row[0] for row in word_query}

        added = 0
        for record in records:
            if db_word(record) in existing_words:
                continue
            self.db.add(record_to_row(record, gasket.id))
            added += 1
        gasket.num_circles = (gasket.num_circles or 0) + added
        if gasket.max_depth_cached is not None and absolute_depth > gasket.max_depth_cached:
            gasket.max_depth_cached = absolute_depth
        self.db.commit()

        circles = [
            record_to_api_circle(record)
            for record in records
            if not record.circle.is_line
        ]
        return {
            "gasket_id": gasket.id,
            "count": len(circles),
            "added": added,
            "truncated": truncated,
            "circles": circles,
        }

    def deepen_cusp(
        self,
        gasket_id: int,
        word_a: str,
        word_b: str,
        min_radius: float,
    ) -> Optional[dict]:
        """Parabolic cusp-chain refinement around the tangency of two circles.

        Reference: ISSUES.md #6 / REVAMP_BLUEPRINT.md M5. O(1) exact closed
        form per chain element (core.engine.cusp); new circles persist under
        their verified tree words.
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return None

        curvatures = json.loads(gasket.initial_curvatures)
        seed = build_seed([parse_curvature_string(c) for c in curvatures])
        result = cusp_chain(seed, word_a, word_b, min_radius)

        words = [record.word for record in result.records]
        existing = {
            row[0]
            for row in self.db.query(Circle.word).filter(
                Circle.gasket_id == gasket.id, Circle.word.in_(words)
            )
        } if words else set()
        added = 0
        for record in result.records:
            if record.word in existing:
                continue
            self.db.add(record_to_row(record, gasket.id))
            added += 1
        gasket.num_circles = (gasket.num_circles or 0) + added
        self.db.commit()

        return {
            "gasket_id": gasket.id,
            "count": len(result.records),
            "added": added,
            "verified_words": result.verified_words,
            "circles": [record_to_api(record) for record in result.records],
        }

    def transform_packing(
        self, gasket_id: int, mirror_word: str, limit: int = 20000
    ) -> Optional[dict]:
        """Invert the cached packing in one of its circles (Möbius action).

        Reference: REVAMP_BLUEPRINT.md M5. Inversion is the exact Lorentz
        reflection on inversive vectors; the result is a DIFFERENT packing,
        so it is returned transiently (never persisted) with synthetic
        'T:'-prefixed identities. Member circles through the mirror's center
        map to lines (serialized with the additive 'line' shape).
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return None

        mirror_row = (
            self.db.query(Circle)
            .filter(Circle.gasket_id == gasket_id, Circle.word == mirror_word)
            .first()
        )
        if mirror_row is None:
            raise ValueError(f"No cached circle with word {mirror_word!r}")
        mirror = row_to_inversive(mirror_row)

        rows = (
            self.db.query(Circle)
            .filter(Circle.gasket_id == gasket_id)
            .order_by(Circle.generation, Circle.id)
            .limit(limit)
            .all()
        )
        circles = []
        lines = 0
        for row in rows:
            image = invert(mirror, row_to_inversive(row))
            word = f"T:{row.word}"
            if image.is_line:
                lines += 1
                circles.append(vec_to_api_line(image, word, row.generation))
                continue
            b_f = float(image.curvature)
            payload = {
                "kind": "circle",
                "id": None,
                "curvature": _float_frac_str(b_f),
                "center": {
                    "x": _float_frac_str(float(image.kx) / b_f),
                    "y": _float_frac_str(float(image.ky) / b_f),
                },
                "radius": _float_frac_str(1.0 / b_f),
                "generation": row.generation,
                "word": word,
                "parent_ids": [],
                "tangent_ids": [],
            }
            circles.append(payload)

        return {
            "gasket_id": gasket.id,
            "mirror_word": mirror_word,
            "count": len(circles),
            "lines": lines,
            "circles": circles,
        }

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

    def _expand(
        self,
        gasket: Gasket,
        curvatures: List[str],
        max_depth: int,
        min_radius: Optional[float],
    ) -> None:
        """Expand a cached gasket to cover a deeper/finer budget incrementally.

        Reruns the walk with the union of the cached and requested budgets
        and inserts only circles whose word is not yet stored. After
        expansion the gasket covers both the old and the new request.
        """
        union_depth = max(gasket.max_depth_cached or 0, max_depth)
        if gasket.min_radius_cached is None or min_radius is None:
            union_min_radius = None
        else:
            union_min_radius = min(gasket.min_radius_cached, min_radius)

        parsed = [parse_curvature_string(c) for c in curvatures]
        seed = build_seed(parsed)
        budget = WalkBudget(max_depth=union_depth, min_radius=union_min_radius)

        existing_words = {
            row[0]
            for row in self.db.query(Circle.word).filter(Circle.gasket_id == gasket.id)
        }
        added = 0
        for record in walk(seed, budget):
            if db_word(record) in existing_words:
                continue
            self.db.add(record_to_row(record, gasket.id))
            added += 1

        gasket.max_depth_cached = union_depth
        gasket.min_radius_cached = union_min_radius
        gasket.num_circles = (gasket.num_circles or 0) + added
        self.db.flush()

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
        self,
        gasket: Gasket,
        max_depth: int,
        min_radius: Optional[float],
        include_circles: bool = True,
    ) -> GasketResponse:
        """Serialize a gasket with circles filtered to the requested budget."""
        circles: List[CircleResponse] = []
        if include_circles:
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
            num_circles=len(circles) if include_circles else (gasket.num_circles or 0),
            max_depth_cached=gasket.max_depth_cached,
            created_at=gasket.created_at.isoformat() if gasket.created_at else "",
            last_accessed_at=(
                gasket.last_accessed_at.isoformat() if gasket.last_accessed_at else None
            ),
            access_count=gasket.access_count,
            circles=circles,
        )
