"""
Unit tests for CircleData class.

Reference: backend/core/circle_data.py
"""

import pytest
from fractions import Fraction
from core.circle_data import CircleData


class TestCircleDataInitialization:
    """Tests for CircleData initialization."""

    def test_minimal_initialization(self):
        """Test creating circle with minimal required fields."""
        circle = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.curvature == Fraction(1)
        assert circle.center == (Fraction(0), Fraction(0))
        assert circle.generation == 0
        assert circle.parent_ids == []
        assert circle.id is None
        assert circle.tangent_ids == []

    def test_full_initialization(self):
        """Test creating circle with all fields."""
        circle = CircleData(
            curvature=Fraction(3, 2),
            center=(Fraction(1, 4), Fraction(-1, 3)),
            generation=2,
            parent_ids=[1, 2, 3],
            id=5,
            tangent_ids=[1, 2, 3, 4],
        )

        assert circle.curvature == Fraction(3, 2)
        assert circle.center == (Fraction(1, 4), Fraction(-1, 3))
        assert circle.generation == 2
        assert circle.parent_ids == [1, 2, 3]
        assert circle.id == 5
        assert circle.tangent_ids == [1, 2, 3, 4]

    def test_negative_curvature(self):
        """Test circle with negative curvature (enclosing circle)."""
        circle = CircleData(
            curvature=Fraction(-1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.curvature == Fraction(-1)


class TestCircleDataRadius:
    """Tests for radius calculation."""

    def test_radius_unit_curvature(self):
        """Test radius with curvature = 1."""
        circle = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.radius() == Fraction(1, 1)

    def test_radius_simple_curvature(self):
        """Test radius with curvature = 2."""
        circle = CircleData(
            curvature=Fraction(2),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.radius() == Fraction(1, 2)

    def test_radius_fractional_curvature(self):
        """Test radius with fractional curvature."""
        circle = CircleData(
            curvature=Fraction(3, 2),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.radius() == Fraction(2, 3)

    def test_radius_negative_curvature(self):
        """Test radius with negative curvature."""
        circle = CircleData(
            curvature=Fraction(-1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle.radius() == Fraction(-1, 1)

    def test_radius_zero_curvature_raises(self):
        """Test that zero curvature raises error."""
        circle = CircleData(
            curvature=Fraction(0),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        with pytest.raises(ZeroDivisionError):
            circle.radius()


class TestCircleDataHash:
    """Tests for hash generation."""

    def test_hash_origin_circle(self):
        """Test hash for circle at origin."""
        circle = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        hash_val = circle.hash_key()
        assert isinstance(hash_val, str)
        assert len(hash_val) == 32  # MD5 hex length

    def test_identical_circles_same_hash(self):
        """Test that identical circles produce same hash."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        circle2 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=1,  # Different generation shouldn't affect hash
            parent_ids=[1, 2],  # Different parent_ids shouldn't affect hash
        )

        assert circle1.hash_key() == circle2.hash_key()

    def test_different_curvature_different_hash(self):
        """Test that different curvatures produce different hash."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        circle2 = CircleData(
            curvature=Fraction(2),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        assert circle1.hash_key() != circle2.hash_key()

    def test_different_center_different_hash(self):
        """Test that different centers produce different hash."""
        circle1 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        circle2 = CircleData(
            curvature=Fraction(1),
            center=(Fraction(1), Fraction(0)),
            generation=0,
        )

        assert circle1.hash_key() != circle2.hash_key()


class TestCircleDataSerialization:
    """Tests for to_dict serialization."""

    def test_to_dict_simple(self):
        """Test serialization of simple circle."""
        circle = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        data = circle.to_dict()

        assert data["id"] is None
        assert data["curvature"] == "1/1"
        assert data["center"]["x"] == "0/1"
        assert data["center"]["y"] == "0/1"
        assert data["radius"] == "1/1"
        assert data["generation"] == 0
        assert data["parent_ids"] == []
        assert data["tangent_ids"] == []

    def test_to_dict_full(self):
        """Test serialization with all fields."""
        circle = CircleData(
            curvature=Fraction(3, 2),
            center=(Fraction(1, 4), Fraction(-1, 3)),
            generation=2,
            parent_ids=[1, 2, 3],
            id=5,
            tangent_ids=[1, 2, 3, 4],
        )

        data = circle.to_dict()

        assert data["id"] == 5
        assert data["curvature"] == "3/2"
        assert data["center"]["x"] == "1/4"
        assert data["center"]["y"] == "-1/3"
        assert data["radius"] == "2/3"
        assert data["generation"] == 2
        assert data["parent_ids"] == [1, 2, 3]
        assert data["tangent_ids"] == [1, 2, 3, 4]

    def test_to_dict_immutable(self):
        """Test that to_dict returns copies of lists."""
        circle = CircleData(
            curvature=Fraction(1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
            parent_ids=[1, 2],
            tangent_ids=[3, 4],
        )

        data = circle.to_dict()

        # Modify returned lists
        data["parent_ids"].append(999)
        data["tangent_ids"].append(999)

        # Original should be unchanged
        assert circle.parent_ids == [1, 2]
        assert circle.tangent_ids == [3, 4]

    def test_to_dict_negative_curvature(self):
        """Test serialization with negative curvature."""
        circle = CircleData(
            curvature=Fraction(-1),
            center=(Fraction(0), Fraction(0)),
            generation=0,
        )

        data = circle.to_dict()

        assert data["curvature"] == "-1/1"
        assert data["radius"] == "-1/1"


class TestCircleDataRepr:
    """Tests for string representation."""

    def test_repr_contains_key_info(self):
        """Test that repr includes important fields."""
        circle = CircleData(
            curvature=Fraction(3, 2),
            center=(Fraction(1, 4), Fraction(-1, 3)),
            generation=2,
            id=5,
        )

        repr_str = repr(circle)

        assert "id=5" in repr_str
        assert "k=3/2" in repr_str
        assert "gen=2" in repr_str
        assert "1/4" in repr_str
        assert "-1/3" in repr_str
