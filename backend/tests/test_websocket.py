"""
Tests for the WebSocket gasket generation endpoint (protocol + streaming).

Reference: REVAMP_BLUEPRINT.md Milestone 2. The cross-stack message-shape
contract lives in tests/test_ws_contract.py; this file covers validation,
batching, and error paths with a mocked generator seam
(api.endpoints.websocket.generate_records).
"""

from fractions import Fraction
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.engine.inversive import InversiveCircle
from core.engine.walk import GeneratedCircle
from main import app


def make_record(curvature=1, x=0, y=0, generation=0, seed_index=0, word=""):
    """Build a GeneratedCircle like the walk would emit."""
    circle = InversiveCircle.from_curvature_center(curvature, x, y)
    return GeneratedCircle(
        circle=circle,
        generation=generation,
        word=word if generation > 0 else "",
        seed_index=seed_index,
        curvature_f=float(curvature),
        x_f=float(x),
        y_f=float(y),
        r_f=1.0 / abs(float(curvature)),
    )


class TestWebSocketGasketGenerate:
    """Tests for WebSocket /ws/gasket/generate endpoint."""

    def setup_method(self):
        from db.base import Base, engine

        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def collect(self, websocket):
        """Drain messages until complete/error."""
        messages = []
        while True:
            msg = websocket.receive_json()
            messages.append(msg)
            if msg["type"] in ("complete", "error"):
                return messages

    def test_websocket_connection_accepted(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            assert websocket is not None

    def test_websocket_valid_generation_request(self):
        with patch("api.endpoints.websocket.generate_records") as mock_gen:
            mock_gen.return_value = iter(
                [make_record(1, i, 0, 0, i) for i in range(3)]
            )

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json(
                    {"action": "start", "curvatures": ["1", "1", "1"], "max_depth": 2}
                )
                messages = self.collect(websocket)

        assert messages[-1]["type"] == "complete"
        assert messages[-1]["total_circles"] == 3
        # Runs persist on completion (Milestone 4)
        assert isinstance(messages[-1]["gasket_id"], int)

    def test_websocket_invalid_json(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_text("not valid json {{{")
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "Invalid JSON" in msg["message"]

    def test_websocket_missing_action(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json({"curvatures": ["1", "1", "1"], "max_depth": 2})
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "action" in msg["message"].lower()

    def test_websocket_unknown_action(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {"action": "stop", "curvatures": ["1", "1", "1"], "max_depth": 2}
            )
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "Unknown action" in msg["message"]

    def test_websocket_missing_curvatures(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json({"action": "start", "max_depth": 2})
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "curvatures" in msg["message"].lower()

    def test_websocket_missing_max_depth(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json({"action": "start", "curvatures": ["1", "1", "1"]})
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "max_depth" in msg["message"].lower()

    def test_websocket_invalid_curvatures_count(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {"action": "start", "curvatures": ["1", "1"], "max_depth": 2}
            )
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert (
                "Validation error" in msg["message"]
                or "curvatures" in msg["message"].lower()
            )

    def test_websocket_invalid_curvature_format(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {"action": "start", "curvatures": ["1", "invalid", "1"], "max_depth": 2}
            )
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert (
                "invalid" in msg["message"].lower()
                or "validation" in msg["message"].lower()
            )

    def test_websocket_max_depth_too_large(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {"action": "start", "curvatures": ["1", "1", "1"], "max_depth": 100}
            )
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert (
                "validation" in msg["message"].lower()
                or "max_depth" in msg["message"].lower()
            )

    def test_websocket_invalid_min_radius(self):
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            websocket.send_json(
                {
                    "action": "start",
                    "curvatures": ["1", "1", "1"],
                    "max_depth": 2,
                    "min_radius": -1,
                }
            )
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "validation" in msg["message"].lower()

    def test_websocket_batch_streaming(self):
        """Circles stream in BATCH_SIZE batches: 1100 -> 500, 500, 100."""
        with patch("api.endpoints.websocket.generate_records") as mock_gen:
            mock_gen.return_value = iter(
                [make_record(1, i, 0, i // 500, 0, word="0" * max(1, i // 500)) for i in range(1100)]
            )

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json(
                    {"action": "start", "curvatures": ["1", "1", "1"], "max_depth": 3}
                )
                messages = self.collect(websocket)

        progress = [m for m in messages if m["type"] == "progress"]
        assert [m["circles_count"] for m in progress] == [500, 500, 100]
        for m in progress:
            assert m["circles_count"] == len(m["circles"])
        assert messages[-1]["type"] == "complete"
        assert messages[-1]["total_circles"] == 1100

    def test_websocket_min_radius_forwarded(self):
        """The optional min_radius parameter reaches the generator seam."""
        with patch("api.endpoints.websocket.generate_records") as mock_gen:
            mock_gen.return_value = iter([make_record(1, 0, 0, 0, 0)])

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json(
                    {
                        "action": "start",
                        "curvatures": ["1", "1", "1"],
                        "max_depth": 4,
                        "min_radius": 0.05,
                    }
                )
                self.collect(websocket)

        mock_gen.assert_called_once_with(["1", "1", "1"], 4, 0.05)

    def test_websocket_generation_error(self):
        with patch("api.endpoints.websocket.generate_records") as mock_gen:

            def raise_error():
                raise ValueError("Test generation error")
                yield  # unreachable; makes this a generator

            mock_gen.return_value = raise_error()

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json(
                    {"action": "start", "curvatures": ["1", "1", "1"], "max_depth": 2}
                )
                msg = websocket.receive_json()
                assert msg["type"] == "error"
                assert "generation error" in msg["message"].lower()

    def test_websocket_progress_message_format(self):
        with patch("api.endpoints.websocket.generate_records") as mock_gen:
            mock_gen.return_value = iter([make_record(2, Fraction(1, 2), 0, 1, 1, word="1")])

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json(
                    {"action": "start", "curvatures": ["-1", "2", "2"], "max_depth": 1}
                )
                messages = self.collect(websocket)

        progress = [m for m in messages if m["type"] == "progress"]
        assert len(progress) == 1
        msg = progress[0]
        assert set(msg.keys()) == {"type", "generation", "circles_count", "circles"}
        assert isinstance(msg["generation"], int)
        assert isinstance(msg["circles_count"], int)
        circle = msg["circles"][0]
        assert circle["curvature"] == "2/1"
        assert circle["center"] == {"x": "1/2", "y": "0/1"}
        assert circle["word"] == "1"
