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
from core.exact_math import ExactNumber
from schemas import GasketResponse, CircleResponse


def parse_curvature_string(s: str) -> ExactNumber:
    """
    Parse curvature string to ExactNumber, preserving int vs Fraction types.

    Args:
        s: Curvature string (e.g., "6", "3/2", "-1")

    Returns:
        int if string represents integer, Fraction otherwise

    Examples:
        >>> parse_curvature_string("6")
        6  # int
        >>> parse_curvature_string("3/2")
        Fraction(3, 2)
        >>> parse_curvature_string("-1")
        -1  # int
    """
    # Try parsing as Fraction first (handles both "6" and "3/2")
    frac = Fraction(s)

    # If denominator is 1, return as int
    if frac.denominator == 1:
        return frac.numerator  # Returns int
    else:
        return frac  # Returns Fraction


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
        # Parse curvatures as ExactNumbers (int or Fraction)
        # Preserves int type for integers, uses Fraction for rationals
        parsed_curvatures = [parse_curvature_string(c) for c in curvatures]

        # Generate gasket using core algorithm
        circles_data = list(
            #generate_diophantine_gasket(parsed_curvatures, max_depth, stream=False)
            generate_apollonian_gasket(parsed_curvatures, max_depth, stream=False)
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
            # Convert CircleData to Circle model using hybrid exact arithmetic
            # to_database_dict() provides both INTEGER and TEXT column values
            db_dict = circle_data.to_database_dict()

            circle = Circle(
                gasket_id=gasket.id,
                generation=circle_data.generation,
                # INTEGER columns (for indexing and backward compatibility)
                curvature_num=db_dict["curvature_num"],
                curvature_denom=db_dict["curvature_denom"],
                center_x_num=db_dict["center_x_num"],
                center_x_denom=db_dict["center_x_denom"],
                center_y_num=db_dict["center_y_num"],
                center_y_denom=db_dict["center_y_denom"],
                radius_num=db_dict["radius_num"],
                radius_denom=db_dict["radius_denom"],
                # TEXT columns (for exact storage, Phase 3 migration)
                curvature_exact=db_dict["curvature_exact"],
                center_x_exact=db_dict["center_x_exact"],
                center_y_exact=db_dict["center_y_exact"],
                radius_exact=db_dict["radius_exact"],
                # Metadata
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

    def delete_gasket(self, gasket_id: int) -> bool:
        """
        Delete a gasket and its associated circles from the database.

        Args:
            gasket_id: ID of the gasket to delete

        Returns:
            True if a gasket was deleted, False if not found.
        """
        gasket = self.db.query(Gasket).filter(Gasket.id == gasket_id).first()
        if not gasket:
            return False

        # Delete gasket (CASCADE should remove circles if configured)
        self.db.delete(gasket)
        self.db.commit()
        return True
