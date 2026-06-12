"""
Tests for Milestone 2 research endpoints: viewport queries, analytics, export.

Reference: REVAMP_BLUEPRINT.md Phase 2.4 / Milestone 2.
"""

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from db.base import Base, engine
from main import app


@pytest.fixture(scope="function")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def gasket_id(client):
    """A cached classic gasket at depth 4 (164 circles)."""
    response = client.post(
        "/api/gaskets", json={"curvatures": ["-1", "2", "2"], "max_depth": 4}
    )
    assert response.status_code == 201
    return response.json()["id"]


class TestViewportQuery:
    def test_full_viewport_returns_all(self, client, gasket_id):
        response = client.get(f"/api/gaskets/{gasket_id}/circles")
        assert response.status_code == 200
        data = response.json()
        assert data["gasket_id"] == gasket_id
        assert data["count"] == 164  # 4 + 4 + 12 + 36 + 108

    def test_bbox_filters(self, client, gasket_id):
        """Right half-plane viewport excludes circles entirely on the left."""
        response = client.get(
            f"/api/gaskets/{gasket_id}/circles",
            params={"min_x": 0.0, "max_x": 1.0, "min_y": -1.0, "max_y": 1.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert 0 < data["count"] < 164
        for circle in data["circles"]:
            num, denom = (int(p) for p in circle["center"]["x"].split("/"))
            r_num, r_denom = (int(p) for p in circle["radius"].split("/"))
            x = num / denom
            r = abs(r_num / r_denom)
            assert x + r >= 0.0, "circle must intersect the viewport"

    def test_min_radius_filters(self, client, gasket_id):
        response = client.get(
            f"/api/gaskets/{gasket_id}/circles", params={"min_radius": 0.1}
        )
        assert response.status_code == 200
        data = response.json()
        assert 0 < data["count"] < 164
        for circle in data["circles"]:
            r_num, r_denom = (int(p) for p in circle["radius"].split("/"))
            assert abs(r_num / r_denom) >= 0.1

    def test_limit(self, client, gasket_id):
        response = client.get(
            f"/api/gaskets/{gasket_id}/circles", params={"limit": 10}
        )
        assert response.json()["count"] == 10

    def test_missing_gasket_404(self, client):
        response = client.get("/api/gaskets/99999/circles")
        assert response.status_code == 404

    def test_circles_carry_words(self, client, gasket_id):
        response = client.get(
            f"/api/gaskets/{gasket_id}/circles", params={"limit": 8}
        )
        words = [c["word"] for c in response.json()["circles"]]
        assert "S0" in words


class TestResolutionAwareCaching:
    def test_post_with_min_radius_prunes(self, client):
        full = client.post(
            "/api/gaskets", json={"curvatures": ["-1", "2", "2"], "max_depth": 4}
        ).json()
        client.delete(f"/api/gaskets/{full['id']}")

        pruned = client.post(
            "/api/gaskets",
            json={"curvatures": ["-1", "2", "2"], "max_depth": 4, "min_radius": 0.05},
        ).json()
        assert 0 < pruned["num_circles"] < full["num_circles"]

    def test_finer_request_regenerates(self, client):
        coarse = client.post(
            "/api/gaskets",
            json={"curvatures": ["-1", "2", "2"], "max_depth": 3, "min_radius": 0.2},
        ).json()
        finer = client.post(
            "/api/gaskets",
            json={"curvatures": ["-1", "2", "2"], "max_depth": 3, "min_radius": 0.01},
        ).json()
        assert finer["num_circles"] > coarse["num_circles"]

    def test_coarser_request_served_from_cache(self, client):
        fine = client.post(
            "/api/gaskets", json={"curvatures": ["-1", "2", "2"], "max_depth": 3}
        ).json()
        coarse = client.post(
            "/api/gaskets",
            json={"curvatures": ["-1", "2", "2"], "max_depth": 3, "min_radius": 0.1},
        ).json()
        # Same cached gasket (no regeneration), filtered down in the response
        assert coarse["id"] == fine["id"]
        assert coarse["num_circles"] <= fine["num_circles"]

    def test_expansion_is_incremental(self, client):
        """A deeper request keeps the same gasket id and existing circle ids
        (rows are added, not regenerated)."""
        shallow = client.post(
            "/api/gaskets", json={"curvatures": ["-1", "2", "2"], "max_depth": 2}
        ).json()
        shallow_ids = {c["id"] for c in shallow["circles"]}

        deeper = client.post(
            "/api/gaskets", json={"curvatures": ["-1", "2", "2"], "max_depth": 4}
        ).json()

        assert deeper["id"] == shallow["id"]
        assert deeper["num_circles"] == 164  # full depth-4 count
        deeper_ids = {c["id"] for c in deeper["circles"]}
        assert shallow_ids <= deeper_ids, "expansion must keep existing rows"

    def test_include_circles_false(self, client):
        """The deepening flow gets metadata without the circle payload."""
        response = client.post(
            "/api/gaskets",
            json={
                "curvatures": ["-1", "2", "2"],
                "max_depth": 4,
                "include_circles": False,
            },
        ).json()
        assert response["circles"] == []
        assert response["num_circles"] == 164  # total cached, not payload size

    def test_deep_depth_with_resolution(self, client):
        """max_depth up to 64 works when bounded by min_radius."""
        response = client.post(
            "/api/gaskets",
            json={
                "curvatures": ["-1", "2", "2"],
                "max_depth": 40,
                "min_radius": 0.01,
                "include_circles": False,
            },
        )
        assert response.status_code == 201
        assert response.json()["num_circles"] > 164


class TestDeepen:
    """Local refinement around a cached circle (deep-zoom support)."""

    def test_deepen_returns_and_persists_local_detail(self, client, gasket_id):
        before = client.get(f"/api/gaskets/{gasket_id}/circles").json()["count"]

        response = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "0", "min_radius": 0.001},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["count"] > 0
        assert data["added"] > 0
        assert data["truncated"] is False
        for circle in data["circles"]:
            assert circle["word"].startswith("0")
            r_num, r_denom = (int(p) for p in circle["radius"].split("/"))
            assert abs(r_num / r_denom) >= 0.001

        after = client.get(f"/api/gaskets/{gasket_id}/circles").json()["count"]
        assert after == before + data["added"]

    def test_deepen_is_idempotent_on_cache(self, client, gasket_id):
        first = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "1", "min_radius": 0.005},
        ).json()
        second = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "1", "min_radius": 0.005},
        ).json()
        assert first["added"] > 0
        assert second["added"] == 0  # everything already cached
        assert second["count"] == first["count"]

    def test_deepen_seed_word_walks_from_root(self, client, gasket_id):
        response = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "S0", "min_radius": 0.05},
        )
        assert response.status_code == 200
        assert response.json()["count"] > 0

    def test_deepen_invalid_word_rejected(self, client, gasket_id):
        # Non-reduced word passes the schema regex but fails replay
        response = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "00", "min_radius": 0.01},
        )
        assert response.status_code == 400
        # Bad characters fail schema validation
        response = client.post(
            f"/api/gaskets/{gasket_id}/deepen",
            json={"word": "ab", "min_radius": 0.01},
        )
        assert response.status_code == 422

    def test_deepen_missing_gasket_404(self, client):
        response = client.post(
            "/api/gaskets/99999/deepen", json={"word": "0", "min_radius": 0.01}
        )
        assert response.status_code == 404


class TestAnalytics:
    def test_analytics_shape_and_values(self, client, gasket_id):
        response = client.get(f"/api/gaskets/{gasket_id}/analytics")
        assert response.status_code == 200
        data = response.json()

        assert data["total_circles"] == 163  # 164 minus the bend -1 bounding circle
        assert sum(data["histogram"]["counts"]) == 163
        assert len(data["histogram"]["bin_edges"]) == len(data["histogram"]["counts"]) + 1

        counting = data["counting_function"]
        assert counting, "expected N(T) points"
        ns = [point["N"] for point in counting]
        assert ns == sorted(ns), "N(T) must be monotone"
        assert ns[-1] == 163

        # The exponent estimate converges to δ ≈ 1.3057 slowly from below
        # (measured: 1.03 @ depth 4, 1.11 @ depth 6, 1.18 @ depth 8); pin the
        # depth-4 window.
        assert data["dimension_reference"] == pytest.approx(1.305688)
        assert data["dimension_estimate"] is not None
        assert 0.9 < data["dimension_estimate"] < 1.31

    def test_missing_gasket_404(self, client):
        assert client.get("/api/gaskets/99999/analytics").status_code == 404


class TestExport:
    def test_csv_export(self, client, gasket_id):
        response = client.get(f"/api/gaskets/{gasket_id}/export?format=csv")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")

        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert len(rows) == 164
        first_seed = next(r for r in rows if r["word"] == "S0")
        assert first_seed["curvature_exact"] == "-1"
        bend_3 = next(r for r in rows if r["curvature_exact"] == "3")
        assert bend_3["residue_24"] == "3"
        assert bend_3["is_prime_bend"] == "True"

    def test_json_export(self, client, gasket_id):
        response = client.get(f"/api/gaskets/{gasket_id}/export?format=json")
        assert response.status_code == 200
        data = json.loads(response.text)
        assert data["gasket_id"] == gasket_id
        # Reproducibility metadata (Milestone 4)
        assert data["engine_version"]
        assert data["max_depth_cached"] == 4
        assert data["initial_curvatures"] == ["-1", "2", "2"]
        assert len(data["circles"]) == 164
        bends = sorted(
            int(c["curvature_exact"]) for c in data["circles"]
        )
        assert bends[:5] == [-1, 2, 2, 3, 3]

    def test_invalid_format_rejected(self, client, gasket_id):
        response = client.get(f"/api/gaskets/{gasket_id}/export?format=xml")
        assert response.status_code == 422

    def test_missing_gasket_404(self, client):
        assert client.get("/api/gaskets/99999/export").status_code == 404


class TestCuspChainEndpoint:
    """Parabolic cusp refinement (ISSUES.md #6 / M5)."""

    def test_cusp_chain_persists_and_returns(self, client, gasket_id):
        before = client.get(f"/api/gaskets/{gasket_id}/circles").json()["count"]
        response = client.post(
            f"/api/gaskets/{gasket_id}/cusp-chain",
            json={"word_a": "S1", "word_b": "S2", "min_radius": 1e-5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["verified_words"] is True
        assert data["count"] > 50
        bends = sorted(
            int(c["curvature"].split("/")[0]) for c in data["circles"]
        )
        assert bends[:4] == [3, 15, 15, 35]  # 4n^2-1, both directions
        after = client.get(f"/api/gaskets/{gasket_id}/circles").json()["count"]
        assert after > before

    def test_cusp_chain_idempotent(self, client, gasket_id):
        first = client.post(
            f"/api/gaskets/{gasket_id}/cusp-chain",
            json={"word_a": "S1", "word_b": "S2", "min_radius": 1e-4},
        ).json()
        second = client.post(
            f"/api/gaskets/{gasket_id}/cusp-chain",
            json={"word_a": "S1", "word_b": "S2", "min_radius": 1e-4},
        ).json()
        assert first["added"] > 0
        assert second["added"] == 0

    def test_non_tangent_rejected(self, client, gasket_id):
        response = client.post(
            f"/api/gaskets/{gasket_id}/cusp-chain",
            json={"word_a": "S3", "word_b": "3", "min_radius": 1e-3},
        )
        assert response.status_code == 400


class TestTransformEndpoint:
    """Möbius inversion of the packing (M5)."""

    def test_invert_in_bounding_circle(self, client, gasket_id):
        response = client.post(
            f"/api/gaskets/{gasket_id}/transform",
            json={"mirror_word": "S0"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mirror_word"] == "S0"
        assert data["count"] == 164
        # The two bend-2 circles pass through the origin -> become lines
        assert data["lines"] == 2
        kinds = {c["kind"] for c in data["circles"]}
        assert kinds == {"circle", "line"}
        assert all(c["word"].startswith("T:") for c in data["circles"])

    def test_unknown_mirror_rejected(self, client, gasket_id):
        response = client.post(
            f"/api/gaskets/{gasket_id}/transform",
            json={"mirror_word": "012301"},
        )
        assert response.status_code == 400


class TestStripPacking:
    """The Apollonian strip (0,0,1,1) end-to-end (M5)."""

    def test_strip_creates_with_lines(self, client):
        response = client.post(
            "/api/gaskets",
            json={"curvatures": ["0", "0", "1", "1"], "max_depth": 3, "min_radius": 0.05},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["num_circles"] > 4
        # REST circle list omits lines; bends are the Ford-like integers
        bends = sorted(set(int(c["curvature"].split("/")[0]) for c in data["circles"]))
        assert bends[0] == 1 and 4 in bends

    def test_other_zero_configs_rejected(self, client):
        response = client.post(
            "/api/gaskets", json={"curvatures": ["0", "1", "1"], "max_depth": 2}
        )
        assert response.status_code == 422
