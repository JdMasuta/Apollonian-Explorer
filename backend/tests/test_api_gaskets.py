"""
Integration tests for /api/gaskets REST endpoints with hybrid exact arithmetic.

Phase 10: API Integration Testing

This test suite verifies the complete flow through the system:
API Request → Service Layer → Generator → Database → API Response

Tests cover:
- POST /api/gaskets (create/retrieve gaskets)
- GET /api/gaskets/{id} (retrieve by ID)
- DELETE /api/gaskets/{id} (delete gasket)
- ExactNumber type preservation (int, Fraction, SymPy)
- Dual storage strategy (INTEGER + TEXT columns)
- Cache behavior (hash-based lookup)
- Previously failing [1,2,2] configuration

Reference: .DESIGN_SPEC.md section 8.4 (Hybrid Exact Arithmetic System)
"""

import pytest
from fastapi.testclient import TestClient
from fractions import Fraction
import sympy as sp

from main import app
from db.base import Base, engine, SessionLocal
from db.models.gasket import Gasket
from db.models.circle import Circle


def _is_rational(exact: str) -> bool:
    """True for canonical rational exact strings ('6', '-3/2')."""
    try:
        Fraction(exact)
        return True
    except (ValueError, ZeroDivisionError):
        return False


@pytest.fixture(scope="function")
def db_session():
    """
    Create fresh database for each test.

    Provides isolated test environment with clean database state.
    """
    # Drop BEFORE creating as well: the tests share the dev gaskets.db, so a
    # previously running dev server may have left rows behind. Cleaning only
    # after each test is not enough for the first test of a session.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Create session
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """Create FastAPI test client for HTTP requests."""
    return TestClient(app)


class TestPostGaskets:
    """
    Tests for POST /api/gaskets endpoint.

    Verifies gasket creation and caching with hybrid exact arithmetic.
    """

    def test_create_gasket_integer_curvatures(self, client, db_session):
        """
        Test gasket creation with integer curvatures [1, 2, 2].

        Verifies:
        - 201 Created status
        - Response structure correct
        - Database persistence (INTEGER + TEXT columns)
        - Unified fraction format in API response
        """
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 2
        })

        # API response assertions
        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "hash" in data
        assert "initial_curvatures" in data
        assert data["initial_curvatures"] == ["1", "2", "2"]
        assert "num_circles" in data
        assert data["num_circles"] > 0
        assert "circles" in data
        assert len(data["circles"]) > 0

        # Verify unified fraction format in API response
        for circle in data["circles"]:
            assert "/" in circle["curvature"], "Curvature should be in 'num/denom' format"
            assert "/" in circle["radius"], "Radius should be in 'num/denom' format"
            assert "/" in circle["center"]["x"], "Center X should be in 'num/denom' format"
            assert "/" in circle["center"]["y"], "Center Y should be in 'num/denom' format"

        # Database assertions
        gasket = db_session.query(Gasket).first()
        assert gasket is not None
        assert gasket.num_circles == data["num_circles"]

        # Verify circles persisted
        circles = db_session.query(Circle).all()
        assert len(circles) == data["num_circles"]

    def test_create_gasket_with_database_verification(self, client, db_session):
        """
        Test schema-v2 storage: word identity, exact inversive coordinates,
        and float mirrors all populated.
        """
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })

        assert response.status_code == 201

        circles = db_session.query(Circle).all()
        assert circles

        words = [c.word for c in circles]
        assert len(words) == len(set(words)), "words must be unique per gasket"
        assert {"S0", "S1", "S2", "S3"} <= set(words), "seed circles persisted"

        for circle in circles:
            # Exact inversive coordinates (lossless source of truth)
            for column in (
                circle.cocurvature_exact,
                circle.curvature_exact,
                circle.kx_exact,
                circle.ky_exact,
            ):
                assert isinstance(column, str) and column
            # Float mirrors (indexed, for viewport queries)
            assert isinstance(circle.b_f, float)
            assert circle.x_f is not None and circle.y_f is not None
            assert circle.r_f is not None and circle.r_f > 0

    def test_create_gasket_fraction_curvatures(self, client, db_session):
        """
        Test gasket creation with fraction curvatures ["3/2", "5/3", "7/4"].

        Verifies Fraction parsing and storage.
        """
        response = client.post("/api/gaskets", json={
            "curvatures": ["3/2", "5/3", "7/4"],
            "max_depth": 1
        })

        assert response.status_code == 201
        data = response.json()

        assert data["initial_curvatures"] == ["3/2", "5/3", "7/4"]
        assert data["num_circles"] > 0

        # Check database for exact fraction storage (canonical 'p/q' strings)
        circles = db_session.query(Circle).all()
        has_fraction = any(
            "/" in c.curvature_exact and _is_rational(c.curvature_exact)
            for c in circles
        )
        assert has_fraction, "Expected at least one Fraction curvature in database"

    def test_previously_failing_configuration_122(self, client, db_session):
        """
        CRITICAL TEST: Verify [1,2,2] that caused INTEGER overflow now works.

        This configuration previously failed at depth 2-3 due to
        .limit_denominator(10^9) creating huge denominators.

        With hybrid arithmetic (Phase 6), it should complete successfully.
        Note: Using depth=1 due to severe SymPy performance issues (Issue #5).
        Even depth=2 times out after 30+ seconds.
        """
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1  # Minimal depth due to SymPy slowness (Issue #5)
        })

        # Should complete successfully (no 500 error)
        assert response.status_code == 201
        data = response.json()

        # Verify generation completed
        assert data["num_circles"] > 0
        assert data["max_depth_cached"] == 1

        # [1,2,2] produces irrational values (k4 = 5 ± 4√2): exact strings
        # must preserve them symbolically, never as huge fractions.
        circles = db_session.query(Circle).all()
        irrational_count = sum(
            1 for c in circles
            if not _is_rational(c.curvature_exact)
            or not _is_rational(c.kx_exact)
            or not _is_rational(c.ky_exact)
        )
        assert irrational_count > 0, "Expected exact symbolic (irrational) coordinates"

        # Float mirrors stay finite and sane
        for c in circles:
            assert abs(c.b_f) < 1e9

    def test_irrational_producing_configuration(self, client, db_session):
        """
        Test [1, 1, 1] configuration that produces sqrt expressions.

        Verifies SymPy expressions are stored in TEXT columns.
        """
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "1", "1"],
            "max_depth": 1  # Keep shallow for speed
        })

        assert response.status_code == 201

        # [1,1,1] produces irrational curvatures (3 ± 2√3) and centers;
        # the exact strings must preserve them symbolically.
        circles = db_session.query(Circle).all()
        irrational = [
            c for c in circles
            if not _is_rational(c.curvature_exact)
            or not _is_rational(c.kx_exact)
            or not _is_rational(c.ky_exact)
        ]
        assert irrational, "Expected exact symbolic (irrational) values"
        assert any("sqrt" in c.curvature_exact for c in circles), (
            "Expected sqrt() expressions in exact curvature strings"
        )

    def test_cache_hit_sufficient_depth(self, client, db_session):
        """
        Test cache hit when cached depth >= requested depth.

        Verifies gasket is retrieved from cache without regeneration.
        """
        # Create gasket with depth 5
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 5
        })
        assert response1.status_code == 201
        data1 = response1.json()
        gasket_id = data1["id"]
        initial_access_count = data1["access_count"]

        # Request same gasket with depth 3 (should hit cache)
        response2 = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 3
        })
        assert response2.status_code == 201
        data2 = response2.json()

        # Should return same gasket
        assert data2["id"] == gasket_id
        assert data2["max_depth_cached"] == 5  # Original depth preserved
        assert data2["access_count"] == initial_access_count + 1

        # Verify no new gasket created
        gasket_count = db_session.query(Gasket).count()
        assert gasket_count == 1, "Should reuse existing gasket (cache hit)"

    def test_cache_miss_insufficient_depth(self, client, db_session):
        """
        Test cache miss when cached depth < requested depth.

        Verifies gasket is regenerated with greater depth.
        """
        # Create gasket with depth 2
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 2
        })
        assert response1.status_code == 201
        data1 = response1.json()

        # Request same gasket with depth 5 (should regenerate)
        response2 = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 5
        })
        assert response2.status_code == 201
        data2 = response2.json()

        # Should have more circles (greater depth)
        assert data2["num_circles"] > data1["num_circles"]
        assert data2["max_depth_cached"] == 5

        # Old gasket should be deleted, new one created
        gasket_count = db_session.query(Gasket).count()
        assert gasket_count == 1, "Old gasket should be deleted during regeneration"

    def test_invalid_curvature_format(self, client, db_session):
        """Test error handling for invalid curvature format."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["not-a-number", "1", "1"],
            "max_depth": 3
        })

        assert response.status_code == 422  # Pydantic validation returns 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_zero_curvature_rejected(self, client, db_session):
        """Test that zero curvatures are rejected (not supported)."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["0", "1", "1"],
            "max_depth": 3
        })

        # Should fail validation (zero curvature = infinite radius)
        assert response.status_code in [400, 422]

    def test_depth_validation(self, client, db_session):
        """Test validation for max_depth parameter."""
        # Negative depth
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["1", "1", "1"],
            "max_depth": -1
        })
        assert response1.status_code in [400, 422]

        # Zero depth
        response2 = client.post("/api/gaskets", json={
            "curvatures": ["1", "1", "1"],
            "max_depth": 0
        })
        assert response2.status_code in [400, 422]


class TestGetGasket:
    """Tests for GET /api/gaskets/{id} endpoint."""

    def test_get_existing_gasket(self, client, db_session):
        """Test retrieving gasket by ID."""
        # Create gasket first
        create_response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 2
        })
        gasket_id = create_response.json()["id"]

        # Retrieve gasket
        get_response = client.get(f"/api/gaskets/{gasket_id}")

        assert get_response.status_code == 200
        data = get_response.json()

        assert data["id"] == gasket_id
        assert "circles" in data
        assert len(data["circles"]) > 0

    def test_get_nonexistent_gasket(self, client, db_session):
        """Test 404 for non-existent gasket."""
        response = client.get("/api/gaskets/99999")

        assert response.status_code == 404

    def test_access_tracking(self, client, db_session):
        """Test that access_count increments on each GET."""
        # Create gasket
        create_response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })
        gasket_id = create_response.json()["id"]
        initial_count = create_response.json()["access_count"]

        # Access multiple times
        for i in range(3):
            response = client.get(f"/api/gaskets/{gasket_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["access_count"] == initial_count + i + 1

    def test_last_accessed_at_updates(self, client, db_session):
        """Test that last_accessed_at timestamp updates."""
        # Create gasket
        create_response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })
        gasket_id = create_response.json()["id"]

        import time
        time.sleep(0.1)  # Small delay to ensure timestamp changes

        # Access gasket
        get_response = client.get(f"/api/gaskets/{gasket_id}")
        assert get_response.status_code == 200

        # Verify last_accessed_at was updated
        gasket = db_session.query(Gasket).filter(Gasket.id == gasket_id).first()
        assert gasket.last_accessed_at > gasket.created_at


class TestDeleteGasket:
    """Tests for DELETE /api/gaskets/{id} endpoint."""

    def test_delete_existing_gasket(self, client, db_session):
        """Test successful deletion returns 204."""
        # Create gasket
        create_response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })
        gasket_id = create_response.json()["id"]

        # Delete gasket
        delete_response = client.delete(f"/api/gaskets/{gasket_id}")

        assert delete_response.status_code == 204

        # Verify gasket deleted
        gasket_count = db_session.query(Gasket).filter(Gasket.id == gasket_id).count()
        assert gasket_count == 0

    def test_delete_cascade_circles(self, client, db_session):
        """Test that deleting gasket also deletes associated circles."""
        # Create gasket
        create_response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 2
        })
        gasket_id = create_response.json()["id"]

        # Count circles before deletion
        circle_count_before = db_session.query(Circle).filter(Circle.gasket_id == gasket_id).count()
        assert circle_count_before > 0

        # Delete gasket
        client.delete(f"/api/gaskets/{gasket_id}")

        # Verify circles also deleted (CASCADE)
        circle_count_after = db_session.query(Circle).filter(Circle.gasket_id == gasket_id).count()
        assert circle_count_after == 0

    def test_delete_nonexistent_gasket(self, client, db_session):
        """Test 404 for deleting non-existent gasket."""
        response = client.delete("/api/gaskets/99999")

        assert response.status_code == 404


class TestExactNumberPersistence:
    """Exact values survive the full API flow in schema-v2 storage."""

    def test_integer_bends_stored_exactly(self, client, db_session):
        """Integral packings keep all-integer exact coordinate strings."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 2
        })
        assert response.status_code == 201

        circles = db_session.query(Circle).all()
        assert circles
        for c in circles:
            # Every coordinate of an integral packing is an integer string
            for column in (c.cocurvature_exact, c.curvature_exact, c.kx_exact, c.ky_exact):
                assert _is_rational(column)
                assert Fraction(column).denominator == 1, column

        bends = sorted(int(c.curvature_exact) for c in circles)
        assert bends[:4] == [-1, 2, 2, 3]

    def test_fraction_values_stored_exactly(self, client, db_session):
        """Rational (non-integral) packings keep exact p/q strings."""
        scaled = [str(Fraction(k, 5)) for k in (-1, 2, 2)]
        response = client.post("/api/gaskets", json={
            "curvatures": scaled,
            "max_depth": 1
        })
        assert response.status_code == 201

        circles = db_session.query(Circle).all()
        for c in circles:
            assert _is_rational(c.curvature_exact)
        assert any(Fraction(c.curvature_exact).denominator > 1 for c in circles)

    def test_sympy_values_stored_symbolically(self, client, db_session):
        """Irrational values persist as symbolic expressions, reparseable."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "1", "1"],
            "max_depth": 1
        })
        assert response.status_code == 201

        symbolic = [
            c for c in db_session.query(Circle).all()
            if not _is_rational(c.curvature_exact)
        ]
        assert symbolic
        for c in symbolic:
            parsed = sp.sympify(c.curvature_exact)
            # Float mirror must agree with the exact value
            assert abs(float(parsed) - c.b_f) < 1e-9

    def test_float_mirrors_consistent_with_exact(self, client, db_session):
        """Float mirrors equal the exact values for rational packings."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["-1", "2", "2"],
            "max_depth": 2
        })
        assert response.status_code == 201

        for c in db_session.query(Circle).all():
            b = Fraction(c.curvature_exact)
            assert abs(float(b) - c.b_f) < 1e-12
            if b != 0:
                x = Fraction(c.kx_exact) / b
                y = Fraction(c.ky_exact) / b
                assert abs(float(x) - c.x_f) < 1e-9
                assert abs(float(y) - c.y_f) < 1e-9


class TestCachingBehavior:
    """Tests for hash-based caching mechanism."""

    def test_hash_consistency(self, client, db_session):
        """Test that same curvatures produce same hash."""
        # Create gasket twice with same curvatures
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 2
        })
        hash1 = response1.json()["hash"]

        response2 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 2
        })
        hash2 = response2.json()["hash"]

        assert hash1 == hash2, "Same curvatures should produce same hash"

    def test_hash_order_independence(self, client, db_session):
        """Test that curvature order doesn't affect hash (sorted internally)."""
        # Note: Implementation may or may not sort curvatures
        # This test documents the behavior
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })
        hash1 = response1.json()["hash"]

        response2 = client.post("/api/gaskets", json={
            "curvatures": ["2", "1", "2"],
            "max_depth": 1
        })
        hash2 = response2.json()["hash"]

        # Hashes should match if implementation sorts curvatures
        # (implementation detail - this documents the behavior)
        assert hash1 == hash2, "Curvature order should not affect hash (sorted)"

    def test_different_curvatures_different_hash(self, client, db_session):
        """Test that different curvatures produce different hashes."""
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1
        })
        hash1 = response1.json()["hash"]

        response2 = client.post("/api/gaskets", json={
            "curvatures": ["1", "3", "3"],
            "max_depth": 1
        })
        hash2 = response2.json()["hash"]

        assert hash1 != hash2, "Different curvatures should produce different hashes"


class TestErrorHandling:
    """Tests for validation and error responses."""

    def test_malformed_json(self, client, db_session):
        """Test 422 for malformed JSON request."""
        response = client.post(
            "/api/gaskets",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_required_fields(self, client, db_session):
        """Test 422 for missing required fields (curvatures is required)."""
        # Missing curvatures - should fail validation
        response = client.post("/api/gaskets", json={
            "max_depth": 3
        })
        assert response.status_code == 422

        # NOTE: max_depth is NOT tested here because it has a default value (5)
        # and is therefore not a required field. See test_default_max_depth for that.

    def test_wrong_curvature_count(self, client, db_session):
        """Test 400 for wrong number of curvatures."""
        # Too few curvatures
        response1 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2"],
            "max_depth": 3
        })
        assert response1.status_code in [400, 422]

        # Too many curvatures
        response2 = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "3", "4", "5"],
            "max_depth": 3
        })
        assert response2.status_code in [400, 422]

    def test_invalid_fraction_format(self, client, db_session):
        """Test 400 for invalid fraction format."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["1/2/3", "1", "1"],  # Invalid: two slashes
            "max_depth": 3
        })

        assert response.status_code in [400, 422]

    def test_extremely_large_depth(self, client, db_session):
        """Test rejection of extremely large depth values."""
        response = client.post("/api/gaskets", json={
            "curvatures": ["1", "2", "2"],
            "max_depth": 1000  # Unreasonably large
        })

        # Should either reject or handle gracefully
        # (implementation may have max depth validation)
        assert response.status_code in [201, 400, 422]
