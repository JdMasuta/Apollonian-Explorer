"""
Unit tests for Pydantic schemas.

Reference: backend/schemas/
"""

import pytest
from pydantic import ValidationError

from schemas import GasketCreate, GasketResponse, CircleResponse


class TestGasketCreate:
    """Tests for GasketCreate schema."""

    def test_valid_three_curvatures(self):
        """Test valid request with 3 curvatures."""
        data = GasketCreate(curvatures=["1", "1", "1"], max_depth=5)

        assert data.curvatures == ["1", "1", "1"]
        assert data.max_depth == 5

    def test_valid_four_curvatures(self):
        """Test valid request with 4 curvatures."""
        data = GasketCreate(curvatures=["1", "2", "3", "4"], max_depth=7)

        assert data.curvatures == ["1", "2", "3", "4"]
        assert data.max_depth == 7

    def test_valid_fractional_curvatures(self):
        """Test valid request with fractional curvatures."""
        data = GasketCreate(curvatures=["3/2", "5/3", "7/4"], max_depth=3)

        assert data.curvatures == ["3/2", "5/3", "7/4"]

    def test_valid_negative_curvature(self):
        """Test valid request with negative curvature."""
        data = GasketCreate(curvatures=["-1", "2", "2"], max_depth=5)

        assert data.curvatures == ["-1", "2", "2"]

    def test_default_max_depth(self):
        """Test that max_depth defaults to 5."""
        data = GasketCreate(curvatures=["1", "1", "1"])

        assert data.max_depth == 5

    def test_invalid_two_curvatures(self):
        """Test that 2 curvatures raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "2"], max_depth=5)

        errors = exc_info.value.errors()
        assert any("curvatures" in str(err) for err in errors)

    def test_invalid_five_curvatures(self):
        """Test that 5 curvatures raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "2", "3", "4", "5"], max_depth=5)

        errors = exc_info.value.errors()
        assert any("curvatures" in str(err) for err in errors)

    def test_invalid_curvature_format(self):
        """Test that invalid curvature format raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "invalid", "3"], max_depth=5)

        errors = exc_info.value.errors()
        assert any("Invalid curvature" in str(err) for err in errors)

    def test_zero_curvature_raises_error(self):
        """Test that zero curvature raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "0", "3"], max_depth=5)

        errors = exc_info.value.errors()
        assert any("Zero curvatures" in str(err) for err in errors)

    def test_invalid_max_depth_too_low(self):
        """Test that max_depth < 1 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "1", "1"], max_depth=0)

        errors = exc_info.value.errors()
        assert any("max_depth" in str(err) for err in errors)

    def test_invalid_max_depth_too_high(self):
        """Test that max_depth > 15 raises error."""
        with pytest.raises(ValidationError) as exc_info:
            GasketCreate(curvatures=["1", "1", "1"], max_depth=16)

        errors = exc_info.value.errors()
        assert any("max_depth" in str(err) for err in errors)


class TestCircleResponse:
    """Tests for CircleResponse schema."""

    def test_valid_circle(self):
        """Test valid circle response."""
        data = CircleResponse(
            id=1,
            curvature="3/2",
            center={"x": "1/4", "y": "-1/3"},
            radius="2/3",
            generation=2,
            parent_ids=[1, 2, 3],
            tangent_ids=[2, 3, 4],
        )

        assert data.id == 1
        assert data.curvature == "3/2"
        assert data.center == {"x": "1/4", "y": "-1/3"}
        assert data.radius == "2/3"
        assert data.generation == 2
        assert data.parent_ids == [1, 2, 3]
        assert data.tangent_ids == [2, 3, 4]

    def test_default_empty_lists(self):
        """Test that parent_ids and tangent_ids default to empty lists."""
        data = CircleResponse(
            id=1,
            curvature="1/1",
            center={"x": "0/1", "y": "0/1"},
            radius="1/1",
            generation=0,
        )

        assert data.parent_ids == []
        assert data.tangent_ids == []


class TestGasketResponse:
    """Tests for GasketResponse schema."""

    def test_valid_gasket(self):
        """Test valid gasket response."""
        data = GasketResponse(
            id=1,
            hash="abc123",
            initial_curvatures=["1", "1", "1"],
            num_circles=50,
            max_depth_cached=5,
            created_at="2025-10-31T12:00:00Z",
            last_accessed_at="2025-10-31T12:30:00Z",
            access_count=3,
            circles=[
                CircleResponse(
                    id=1,
                    curvature="1/1",
                    center={"x": "0/1", "y": "0/1"},
                    radius="1/1",
                    generation=0,
                )
            ],
        )

        assert data.id == 1
        assert data.hash == "abc123"
        assert data.num_circles == 50
        assert len(data.circles) == 1

    def test_optional_last_accessed_at(self):
        """Test that last_accessed_at can be None."""
        data = GasketResponse(
            id=1,
            hash="abc123",
            initial_curvatures=["1", "1", "1"],
            num_circles=50,
            max_depth_cached=5,
            created_at="2025-10-31T12:00:00Z",
            last_accessed_at=None,
            access_count=1,
            circles=[],
        )

        assert data.last_accessed_at is None
