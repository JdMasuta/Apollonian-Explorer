"""
Gasket service layer with business logic and caching.

Reference: .DESIGN_SPEC.md section 9.1 (Caching Strategy)

This module implements the service layer for gasket operations, including:
- Hash-based cache lookup
- Gasket generation
- Database persistence
- Access tracking
"""

import hashlib
import json
from typing import List, Optional
from fractions import Fraction
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import Gasket, Circle
from core.gasket_generator import generate_apollonian_gasket
from core.diophantine_generator import generate_apollonian_gasket as generate_diophantine_gasket
from core.circle_math import fraction_to_tuple
from schemas import GasketResponse, CircleResponse


class GasketService:
    """
    Service for gasket operations with caching.

    Attributes:
        db: SQLAlchemy database session
    """

    def __init__(self, db: Session):
        """
        Initialize service with database session.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def create_or_get_gasket(
        self, curvatures: List[str], max_depth: int
    ) -> GasketResponse:
        """
        Create or retrieve gasket from cache.

        Implements hash-based caching: if a gasket with the same initial
        curvatures exists and has sufficient depth, returns cached version.
        Otherwise, generates new gasket and persists to database.

        Args:
            curvatures: List of curvature strings (e.g., ["1", "1", "1"])
            max_depth: Maximum recursion depth

        Returns:
            GasketResponse with gasket data and circles

        Reference:
            .DESIGN_SPEC.md section 9.1 - Hash-based caching
        """
        # Step 1: Generate cache key (SHA-256 hash of sorted curvatures)
        gasket_hash = self._generate_hash(curvatures)

        # Step 2: Check cache (database lookup by hash)
        existing_gasket = (
            self.db.query(Gasket).filter(Gasket.hash == gasket_hash).first()
        )

        if existing_gasket:
            # Step 3: Check if cached gasket has sufficient depth
            if existing_gasket.max_depth_cached >= max_depth:
                # Cache hit! Update access tracking
                existing_gasket.access_count += 1
                existing_gasket.last_accessed_at = datetime.utcnow()
                self.db.commit()

                # Return cached gasket
                return self._gasket_to_response(existing_gasket, max_depth)

            else:
                # Need to generate more depth
                # For MVP, regenerate entire gasket
                # TODO: In Phase 7, implement incremental generation
                self.db.delete(existing_gasket)
                self.db.commit()

        # Step 4: Cache miss - generate new gasket
        gasket = self._generate_and_persist(curvatures, max_depth, gasket_hash)

        # Step 5: Return response
        return self._gasket_to_response(gasket, max_depth)

    def get_gasket(self, gasket_id: int) -> Optional[GasketResponse]:
        """
        Retrieve gasket by ID.

        Args:
            gasket_id: Gasket database ID

        Returns:
            GasketResponse if found, None otherwise
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()

        if not gasket:
            return None

        # Update access tracking
        gasket.access_count += 1
        gasket.last_accessed_at = datetime.utcnow()
        self.db.commit()

        # Return all cached circles
        max_depth = gasket.max_depth_cached
        return self._gasket_to_response(gasket, max_depth)

    def _generate_hash(self, curvatures: List[str]) -> str:
        """
        Generate SHA-256 hash of curvatures for cache key.

        Curvatures are sorted and canonicalized (as Fractions) before hashing
        to ensure consistent keys regardless of input order.

        Args:
            curvatures: List of curvature strings

        Returns:
            64-character hex SHA-256 hash

        Example:
            >>> _generate_hash(["1", "1", "1"])
            'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'
        """
        # Parse as Fractions for canonical representation
        fracs = [Fraction(c) for c in curvatures]

        # Sort for consistency (order shouldn't matter)
        fracs_sorted = sorted(fracs)

        # Create canonical string: "num1/denom1,num2/denom2,..."
        canonical = ",".join(f"{f.numerator}/{f.denominator}" for f in fracs_sorted)

        # Generate SHA-256 hash
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _generate_and_persist(
        self, curvatures: List[str], max_depth: int, gasket_hash: str
    ) -> Gasket:
        """
        Generate gasket and persist to database.

        Args:
            curvatures: List of curvature strings
            max_depth: Maximum recursion depth
            gasket_hash: Pre-computed hash for cache key

        Returns:
            Persisted Gasket model

        Reference:
            .DESIGN_SPEC.md section 8.2 - Gasket generation algorithm
        """
        # Parse curvatures as Fractions
        fracs = [Fraction(c) for c in curvatures]

        # Generate gasket using core algorithm
        circles_data = list(
            #generate_diophantine_gasket(fracs, max_depth, stream=False)
            generate_apollonian_gasket(fracs, max_depth, stream=False)
        )

        # Create Gasket model
        gasket = Gasket(
            hash=gasket_hash,
            initial_curvatures=json.dumps(curvatures),
            num_circles=len(circles_data),
            max_depth_cached=max_depth,
            access_count=1,
        )
        self.db.add(gasket)
        self.db.flush()  # Get gasket.id

        # Create Circle models
        for circle_data in circles_data:
            # Convert CircleData to Circle model
            center_real, center_imag = circle_data.center

            circle = Circle(
                gasket_id=gasket.id,
                generation=circle_data.generation,
                curvature_num=circle_data.curvature.numerator,
                curvature_denom=circle_data.curvature.denominator,
                center_x_num=center_real.numerator,
                center_x_denom=center_real.denominator,
                center_y_num=center_imag.numerator,
                center_y_denom=center_imag.denominator,
                radius_num=circle_data.radius().numerator,
                radius_denom=circle_data.radius().denominator,
                parent_ids=json.dumps(circle_data.parent_ids),
                tangent_ids=json.dumps(circle_data.tangent_ids),
            )
            self.db.add(circle)

        self.db.commit()
        return gasket

    def _gasket_to_response(
        self, gasket: Gasket, max_depth: int
    ) -> GasketResponse:
        """
        Convert Gasket model to response schema.

        Args:
            gasket: Gasket database model
            max_depth: Maximum depth to include (for filtering circles)

        Returns:
            GasketResponse schema
        """
        # Filter circles by max_depth
        circles = [
            c for c in gasket.circles if c.generation <= max_depth
        ]

        # Convert circles to response schemas
        circle_responses = []
        for circle in circles:
            circle_resp = CircleResponse(
                id=circle.id,
                curvature=f"{circle.curvature_num}/{circle.curvature_denom}",
                center={
                    "x": f"{circle.center_x_num}/{circle.center_x_denom}",
                    "y": f"{circle.center_y_num}/{circle.center_y_denom}",
                },
                radius=f"{circle.radius_num}/{circle.radius_denom}",
                generation=circle.generation,
                parent_ids=json.loads(circle.parent_ids) if circle.parent_ids else [],
                tangent_ids=json.loads(circle.tangent_ids) if circle.tangent_ids else [],
            )
            circle_responses.append(circle_resp)

        # Convert gasket to response
        return GasketResponse(
            id=gasket.id,
            hash=gasket.hash,
            initial_curvatures=json.loads(gasket.initial_curvatures),
            num_circles=len(circle_responses),
            max_depth_cached=gasket.max_depth_cached,
            created_at=gasket.created_at.isoformat() if gasket.created_at else "",
            last_accessed_at=(
                gasket.last_accessed_at.isoformat()
                if gasket.last_accessed_at
                else None
            ),
            access_count=gasket.access_count,
            circles=circle_responses,
        )
