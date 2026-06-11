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

from main import app

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
        assert complete["gasket_id"] is None or isinstance(complete["gasket_id"], int)
        assert isinstance(complete["total_circles"], int)

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
