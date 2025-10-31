"""
Unit tests for database models.

Reference: backend/db/models/
"""

import pytest
from fractions import Fraction
from sqlalchemy.orm import Session

from db import SessionLocal, create_tables, drop_tables, Gasket, Circle


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    create_tables()

    # Create session
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    drop_tables()


class TestGasketModel:
    """Tests for Gasket model."""

    def test_create_gasket(self, db_session: Session):
        """Test creating a gasket."""
        gasket = Gasket(
            hash="abc123",
            initial_curvatures='["1", "1", "1"]',
            num_circles=50,
            max_depth_cached=3,
        )

        db_session.add(gasket)
        db_session.commit()

        assert gasket.id is not None
        assert gasket.hash == "abc123"
        assert gasket.access_count == 1

    def test_gasket_relationship(self, db_session: Session):
        """Test gasket-circle relationship."""
        gasket = Gasket(
            hash="def456",
            initial_curvatures='["1", "2", "3"]',
        )
        db_session.add(gasket)
        db_session.commit()

        # Add circles
        circle = Circle(
            gasket_id=gasket.id,
            generation=0,
            curvature_num=1,
            curvature_denom=1,
            center_x_num=0,
            center_x_denom=1,
            center_y_num=0,
            center_y_denom=1,
            radius_num=1,
            radius_denom=1,
        )
        db_session.add(circle)
        db_session.commit()

        # Verify relationship
        assert len(gasket.circles) == 1
        assert gasket.circles[0].id == circle.id


class TestCircleModel:
    """Tests for Circle model."""

    def test_create_circle(self, db_session: Session):
        """Test creating a circle."""
        # Create parent gasket first
        gasket = Gasket(
            hash="test123",
            initial_curvatures='["1"]',
        )
        db_session.add(gasket)
        db_session.commit()

        # Create circle
        circle = Circle(
            gasket_id=gasket.id,
            generation=1,
            curvature_num=3,
            curvature_denom=2,
            center_x_num=1,
            center_x_denom=4,
            center_y_num=-1,
            center_y_denom=3,
            radius_num=2,
            radius_denom=3,
        )

        db_session.add(circle)
        db_session.commit()

        assert circle.id is not None
        assert circle.gasket_id == gasket.id

    def test_hybrid_property_curvature(self, db_session: Session):
        """Test curvature hybrid property."""
        gasket = Gasket(hash="test", initial_curvatures='[]')
        db_session.add(gasket)
        db_session.commit()

        circle = Circle(
            gasket_id=gasket.id,
            generation=0,
            curvature_num=3,
            curvature_denom=2,
            center_x_num=0,
            center_x_denom=1,
            center_y_num=0,
            center_y_denom=1,
            radius_num=2,
            radius_denom=3,
        )

        # Test getter
        assert circle.curvature == Fraction(3, 2)

        # Test setter
        circle.curvature = Fraction(5, 7)
        assert circle.curvature_num == 5
        assert circle.curvature_denom == 7

    def test_all_hybrid_properties(self, db_session: Session):
        """Test all hybrid properties."""
        gasket = Gasket(hash="test", initial_curvatures='[]')
        db_session.add(gasket)
        db_session.commit()

        circle = Circle(
            gasket_id=gasket.id,
            generation=0,
            curvature_num=1,
            curvature_denom=1,
            center_x_num=1,
            center_x_denom=2,
            center_y_num=3,
            center_y_denom=4,
            radius_num=5,
            radius_denom=6,
        )

        assert circle.curvature == Fraction(1, 1)
        assert circle.center_x == Fraction(1, 2)
        assert circle.center_y == Fraction(3, 4)
        assert circle.radius == Fraction(5, 6)
