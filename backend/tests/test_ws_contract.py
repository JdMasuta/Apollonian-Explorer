"""
Cross-stack contract tests for the gasket-generation WebSocket protocol.

These tests drive the REAL endpoint (no mocks) and validate every message
against the shapes the frontend depends on — the TypeScript interfaces in
frontend/src/services/websocketService.ts:

    ProgressMessage { type: 'progress', generation: int,
                      circles_count: int, circles: CircleData[] }
    CompleteMessage { type: 'complete', gasket_id: int | null,
                      total_circles: int }
    ErrorMessage    { type: 'error', message: str }

    CircleData { id?: int, curvature: str, center: {x: str, y: str},
                 radius: str, generation: int,
                 parent_ids: int[], tangent_ids: int[] }

If a backend change breaks any assertion here, the frontend rendering layer
breaks with it — update both sides together (and the frontend types).

The frontend half of the same protocol is covered by
frontend/src/services/websocketService.test.ts.
"""

import re

import pytest
from fastapi.testclient import TestClient

from db.base import Base, engine
from main import app


@pytest.fixture(scope="module", autouse=True)
def clean_db():
    """WS runs persist now: isolate this module's writes."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# Frontend parseValue() accepts "num/denom" fraction strings (or a plain
# decimal). The backend serializes every numeric field as "num/denom".
FRACTION_RE = re.compile(r"^-?\d+/-?\d+$")


def collect_messages(curvatures, max_depth):
    """Run a full generation over the real WebSocket and return all messages."""
    client = TestClient(app)
    messages = []
    with client.websocket_connect("/ws/gasket/generate") as websocket:
        websocket.send_json(
            {"action": "start", "curvatures": curvatures, "max_depth": max_depth}
        )
        while True:
            message = websocket.receive_json()
            messages.append(message)
            if message["type"] in ("complete", "error"):
                break
    return messages


def assert_circle_shape(circle):
    """CircleData as the frontend consumes it (websocketService.ts)."""
    assert set(circle.keys()) >= {
        "curvature",
        "center",
        "radius",
        "generation",
        "parent_ids",
        "tangent_ids",
    }
    assert isinstance(circle["curvature"], str)
    assert FRACTION_RE.match(circle["curvature"]), circle["curvature"]
    assert set(circle["center"].keys()) == {"x", "y"}
    for axis in ("x", "y"):
        value = circle["center"][axis]
        assert isinstance(value, str)
        assert FRACTION_RE.match(value), value
    assert isinstance(circle["radius"], str)
    assert FRACTION_RE.match(circle["radius"]), circle["radius"]
    assert isinstance(circle["generation"], int)
    assert isinstance(circle["parent_ids"], list)
    assert isinstance(circle["tangent_ids"], list)
    # Denominators must be non-zero so frontend parseValue() never divides by 0
    for value in (circle["curvature"], circle["radius"],
                  circle["center"]["x"], circle["center"]["y"]):
        _, denom = value.split("/")
        assert int(denom) != 0, value


class TestProtocolContract:
    """Message shapes for a successful generation run."""

    @pytest.fixture(scope="class")
    def messages(self):
        return collect_messages(["-1", "2", "2"], max_depth=2)

    def test_run_ends_with_complete(self, messages):
        assert messages[-1]["type"] == "complete"

    def test_progress_message_shape(self, messages):
        progress = [m for m in messages if m["type"] == "progress"]
        assert progress, "expected at least one progress message"
        for message in progress:
            assert set(message.keys()) == {
                "type",
                "generation",
                "circles_count",
                "circles",
            }
            assert isinstance(message["generation"], int)
            assert isinstance(message["circles_count"], int)
            assert message["circles_count"] == len(message["circles"])
            for circle in message["circles"]:
                assert_circle_shape(circle)

    def test_complete_message_shape(self, messages):
        complete = messages[-1]
        assert set(complete.keys()) == {"type", "gasket_id", "total_circles"}
        # Runs persist on completion (Milestone 4): the id is real.
        assert isinstance(complete["gasket_id"], int)
        assert isinstance(complete["total_circles"], int)

    def test_run_is_persisted_and_reusable(self, messages):
        gasket_id = messages[-1]["gasket_id"]
        client = TestClient(app)
        response = client.get(f"/api/gaskets/{gasket_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["initial_curvatures"] == ["-1", "2", "2"]
        assert body["num_circles"] >= messages[-1]["total_circles"]

    def test_total_circles_matches_stream(self, messages):
        streamed = sum(m["circles_count"] for m in messages if m["type"] == "progress")
        assert messages[-1]["total_circles"] == streamed

    def test_circle_values_are_renderable(self, messages):
        """The frontend computes radius = |1/curvature| and float centers;
        every streamed circle must produce finite values."""
        for message in messages:
            if message["type"] != "progress":
                continue
            for circle in message["circles"]:
                num, denom = (int(p) for p in circle["curvature"].split("/"))
                assert num != 0, "zero curvature cannot be rendered as a circle"
                x_num, x_denom = (int(p) for p in circle["center"]["x"].split("/"))
                y_num, y_denom = (int(p) for p in circle["center"]["y"].split("/"))
                assert x_denom != 0 and y_denom != 0


class TestProtocolContractQuadruple:
    """4-curvature seeds stream through the same contract."""

    def test_quadruple_run(self):
        messages = collect_messages(["-1", "2", "2", "3"], max_depth=1)
        assert messages[-1]["type"] == "complete"
        assert messages[-1]["total_circles"] == 8  # 4 seed + 4 reflections


class TestProtocolContractIrrational:
    """Irrational seeds (rational bends, irrational centers) keep the contract.

    Regression: per-component exactness in record_to_api_circle — (1,1,1)
    previously crashed serialization with 'argument should be a string or a
    Rational instance'.
    """

    def test_irrational_seed_run(self):
        messages = collect_messages(["1", "1", "1"], max_depth=2)
        assert messages[-1]["type"] == "complete"
        assert messages[-1]["total_circles"] == 20
        for message in messages:
            if message["type"] == "progress":
                for circle in message["circles"]:
                    assert_circle_shape(circle)

    def test_min_radius_bounds_the_stream(self):
        """The additive min_radius parameter prunes the stream server-side."""
        full = collect_messages(["-1", "2", "2"], max_depth=5)
        pruned_messages = []
        client = TestClient(app)
        with client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {
                    "action": "start",
                    "curvatures": ["-1", "2", "2"],
                    "max_depth": 5,
                    "min_radius": 0.05,
                }
            )
            while True:
                message = websocket.receive_json()
                pruned_messages.append(message)
                if message["type"] in ("complete", "error"):
                    break
        assert pruned_messages[-1]["type"] == "complete"
        assert 0 < pruned_messages[-1]["total_circles"] < full[-1]["total_circles"]


class TestProtocolErrors:
    """Error messages keep the ErrorMessage shape the frontend routes on."""

    def test_invalid_curvature_error_shape(self):
        messages = collect_messages(["not-a-number", "1", "1"], max_depth=2)
        assert len(messages) == 1
        error = messages[0]
        assert set(error.keys()) == {"type", "message"}
        assert error["type"] == "error"
        assert isinstance(error["message"], str) and error["message"]

    def test_unrealizable_triple_error_shape(self):
        # Negative Descartes discriminant: no real completion exists.
        messages = collect_messages(["-1", "1", "1/10"], max_depth=2)
        error = messages[-1]
        assert error["type"] == "error"
        assert isinstance(error["message"], str) and error["message"]
