"""
Unit tests for database models (schema v2 — inversive coordinates).

Reference: backend/db/models/, REVAMP_BLUEPRINT.md Milestone 2.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import SessionLocal, create_tables, drop_tables, Gasket, Circle


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    drop_tables()
    create_tables()
    session = SessionLocal()

    yield session

    session.close()
    drop_tables()


def make_circle(gasket_id: int, word: str = "S0", **overrides) -> Circle:
    """A valid v2 circle row (the classic bend-3 circle by default)."""
    values = dict(
        gasket_id=gasket_id,
        generation=0,
        word=word,
        is_line=False,
        cocurvature_exact="1",
        curvature_exact="3",
        kx_exact="0",
        ky_exact="2",
        b_f=3.0,
        x_f=0.0,
        y_f=2.0 / 3.0,
        r_f=1.0 / 3.0,
    )
    values.update(overrides)
    return Circle(**values)


class TestGasketModel:
    """Tests for Gasket model."""

    def test_create_gasket(self, db_session: Session):
        gasket = Gasket(
            hash="abc123",
            initial_curvatures='["1", "1", "1"]',
            num_circles=50,
            max_depth_cached=3,
            min_radius_cached=0.01,
        )

        db_session.add(gasket)
        db_session.commit()

        assert gasket.id is not None
        assert gasket.hash == "abc123"
        assert gasket.access_count == 1
        assert gasket.min_radius_cached == 0.01

    def test_min_radius_cached_nullable(self, db_session: Session):
        """NULL min_radius_cached means 'no resolution pruning'."""
        gasket = Gasket(hash="xyz", initial_curvatures='["1", "2", "3"]')
        db_session.add(gasket)
        db_session.commit()
        assert gasket.min_radius_cached is None

    def test_gasket_relationship(self, db_session: Session):
        gasket = Gasket(hash="def456", initial_curvatures='["1", "2", "3"]')
        db_session.add(gasket)
        db_session.commit()

        db_session.add(make_circle(gasket.id))
        db_session.commit()

        assert len(gasket.circles) == 1
        assert gasket.circles[0].word == "S0"


class TestCircleModel:
    """Tests for the v2 Circle model."""

    def test_create_circle(self, db_session: Session):
        gasket = Gasket(hash="test123", initial_curvatures='["1"]')
        db_session.add(gasket)
        db_session.commit()

        circle = make_circle(gasket.id, word="012")
        db_session.add(circle)
        db_session.commit()

        assert circle.id is not None
        assert circle.gasket_id == gasket.id
        assert circle.curvature_exact == "3"
        assert circle.b_f == 3.0

    def test_word_unique_per_gasket(self, db_session: Session):
        """The reduced word is the circle's identity within a gasket."""
        gasket = Gasket(hash="uniq", initial_curvatures='["1"]')
        db_session.add(gasket)
        db_session.commit()

        db_session.add(make_circle(gasket.id, word="01"))
        db_session.commit()

        db_session.add(make_circle(gasket.id, word="01"))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_same_word_allowed_across_gaskets(self, db_session: Session):
        g1 = Gasket(hash="g1", initial_curvatures='["1"]')
        g2 = Gasket(hash="g2", initial_curvatures='["2"]')
        db_session.add_all([g1, g2])
        db_session.commit()

        db_session.add(make_circle(g1.id, word="01"))
        db_session.add(make_circle(g2.id, word="01"))
        db_session.commit()  # no IntegrityError

    def test_line_row(self, db_session: Session):
        """Lines store NULL center/radius mirrors."""
        gasket = Gasket(hash="strip", initial_curvatures='["0", "0", "1", "1"]')
        db_session.add(gasket)
        db_session.commit()

        line = make_circle(
            gasket.id,
            word="S1",
            is_line=True,
            cocurvature_exact="0",
            curvature_exact="0",
            kx_exact="0",
            ky_exact="-1",
            b_f=0.0,
            x_f=None,
            y_f=None,
            r_f=None,
        )
        db_session.add(line)
        db_session.commit()

        assert line.is_line is True
        assert line.x_f is None and line.r_f is None

    def test_cascade_delete(self, db_session: Session):
        gasket = Gasket(hash="cascade", initial_curvatures='["1"]')
        db_session.add(gasket)
        db_session.commit()
        db_session.add(make_circle(gasket.id))
        db_session.commit()

        db_session.delete(gasket)
        db_session.commit()

        assert db_session.query(Circle).count() == 0
