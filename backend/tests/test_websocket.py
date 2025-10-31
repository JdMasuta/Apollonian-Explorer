"""
Tests for WebSocket gasket generation endpoint.

Reference: IMPLEMENTATION_PLAN.md Phase 2 Day 5 Task 1
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fractions import Fraction

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from core.circle_data import CircleData


class TestWebSocketGasketGenerate:
    """Tests for WebSocket /ws/gasket/generate endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)

    def test_websocket_connection_accepted(self):
        """Test that WebSocket connection is accepted."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Connection should be established
            assert websocket is not None

    def test_websocket_valid_generation_request(self):
        """Test successful gasket generation with valid parameters."""
        with patch('api.endpoints.websocket.generate_apollonian_gasket') as mock_gen:
            # Create mock circle data
            mock_circles = [
                CircleData(
                    curvature=Fraction(1),
                    center=(Fraction(0), Fraction(0)),
                    generation=0,
                    parent_ids=[]
                ),
                CircleData(
                    curvature=Fraction(1),
                    center=(Fraction(2), Fraction(0)),
                    generation=0,
                    parent_ids=[]
                ),
                CircleData(
                    curvature=Fraction(1),
                    center=(Fraction(1), Fraction(1)),
                    generation=0,
                    parent_ids=[]
                ),
            ]
            mock_gen.return_value = iter(mock_circles)

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                # Send valid request
                websocket.send_json({
                    "action": "start",
                    "curvatures": ["1", "1", "1"],
                    "max_depth": 2
                })

                # Receive messages
                messages = []
                try:
                    while True:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                except:
                    pass

                # Should have at least progress and complete messages
                assert len(messages) >= 1

                # Last message should be complete
                complete_msg = messages[-1]
                assert complete_msg["type"] == "complete"
                assert complete_msg["total_circles"] == 3
                assert complete_msg["gasket_id"] is None  # TODO: Will be implemented later

    def test_websocket_invalid_json(self):
        """Test error handling for invalid JSON."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send invalid JSON
            websocket.send_text("not valid json {{{")

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "Invalid JSON" in msg["message"]

    def test_websocket_missing_action(self):
        """Test error handling for missing 'action' field."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send message without action
            websocket.send_json({
                "curvatures": ["1", "1", "1"],
                "max_depth": 2
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "action" in msg["message"].lower()

    def test_websocket_invalid_action(self):
        """Test error handling for invalid action."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send invalid action
            websocket.send_json({
                "action": "invalid_action",
                "curvatures": ["1", "1", "1"],
                "max_depth": 2
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "Unknown action" in msg["message"]

    def test_websocket_missing_curvatures(self):
        """Test error handling for missing curvatures."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send without curvatures
            websocket.send_json({
                "action": "start",
                "max_depth": 2
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "curvatures" in msg["message"].lower()

    def test_websocket_missing_max_depth(self):
        """Test error handling for missing max_depth."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send without max_depth
            websocket.send_json({
                "action": "start",
                "curvatures": ["1", "1", "1"]
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "max_depth" in msg["message"].lower()

    def test_websocket_invalid_curvatures_count(self):
        """Test validation error for wrong number of curvatures."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send with only 2 curvatures (need 3-4)
            websocket.send_json({
                "action": "start",
                "curvatures": ["1", "1"],
                "max_depth": 2
            })

            # Should receive error message from Pydantic validation
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "Validation error" in msg["message"] or "curvatures" in msg["message"].lower()

    def test_websocket_invalid_curvature_format(self):
        """Test validation error for invalid curvature format."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send with invalid curvature string
            websocket.send_json({
                "action": "start",
                "curvatures": ["1", "invalid", "1"],
                "max_depth": 2
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "invalid" in msg["message"].lower() or "validation" in msg["message"].lower()

    def test_websocket_zero_curvature(self):
        """Test validation error for zero curvature (not yet supported)."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send with zero curvature
            websocket.send_json({
                "action": "start",
                "curvatures": ["0", "1", "1"],
                "max_depth": 2
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "zero" in msg["message"].lower() or "validation" in msg["message"].lower()

    def test_websocket_max_depth_out_of_range(self):
        """Test validation error for max_depth out of range."""
        with self.client.websocket_connect("/ws/gasket/generate") as websocket:
            # Send with max_depth too large
            websocket.send_json({
                "action": "start",
                "curvatures": ["1", "1", "1"],
                "max_depth": 50  # Exceeds limit of 15
            })

            # Should receive error message
            msg = websocket.receive_json()
            assert msg["type"] == "error"
            assert "validation" in msg["message"].lower() or "max_depth" in msg["message"].lower()

    def test_websocket_batch_streaming(self):
        """Test that circles are streamed in batches."""
        with patch('api.endpoints.websocket.generate_apollonian_gasket') as mock_gen:
            # Create 25 mock circles (should result in 3 messages: 10, 10, 5)
            mock_circles = []
            for i in range(25):
                mock_circles.append(
                    CircleData(
                        curvature=Fraction(1),
                        center=(Fraction(i), Fraction(0)),
                        generation=i // 10,
                        parent_ids=[]
                    )
                )
            mock_gen.return_value = iter(mock_circles)

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json({
                    "action": "start",
                    "curvatures": ["1", "1", "1"],
                    "max_depth": 3
                })

                # Collect progress messages
                progress_messages = []
                complete_message = None

                try:
                    while True:
                        msg = websocket.receive_json()
                        if msg["type"] == "progress":
                            progress_messages.append(msg)
                        elif msg["type"] == "complete":
                            complete_message = msg
                            break
                except:
                    pass

                # Should have 3 progress messages (batches of 10, 10, 5)
                assert len(progress_messages) == 3

                # First two batches should have 10 circles each
                assert progress_messages[0]["circles_count"] == 10
                assert len(progress_messages[0]["circles"]) == 10
                assert progress_messages[1]["circles_count"] == 10
                assert len(progress_messages[1]["circles"]) == 10

                # Last batch should have 5 circles
                assert progress_messages[2]["circles_count"] == 5
                assert len(progress_messages[2]["circles"]) == 5

                # Complete message should report total
                assert complete_message is not None
                assert complete_message["total_circles"] == 25

    def test_websocket_generation_error(self):
        """Test error handling during generation."""
        with patch('api.endpoints.websocket.generate_apollonian_gasket') as mock_gen:
            # Make generator raise an exception
            def raise_error():
                raise ValueError("Test generation error")
                yield  # unreachable

            mock_gen.return_value = raise_error()

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json({
                    "action": "start",
                    "curvatures": ["1", "1", "1"],
                    "max_depth": 2
                })

                # Should receive error message
                msg = websocket.receive_json()
                assert msg["type"] == "error"
                assert "generation error" in msg["message"].lower() or "test generation error" in msg["message"].lower()

    def test_websocket_progress_message_format(self):
        """Test that progress messages have correct format."""
        with patch('api.endpoints.websocket.generate_apollonian_gasket') as mock_gen:
            mock_circles = [
                CircleData(
                    curvature=Fraction(1),
                    center=(Fraction(0), Fraction(0)),
                    generation=0,
                    parent_ids=[]
                )
            ]
            mock_gen.return_value = iter(mock_circles)

            with self.client.websocket_connect("/ws/gasket/generate") as websocket:
                websocket.send_json({
                    "action": "start",
                    "curvatures": ["1", "1", "1"],
                    "max_depth": 1
                })

                # Get first message (should be progress or complete)
                msg = websocket.receive_json()

                # Check message structure
                if msg["type"] == "progress":
                    assert "generation" in msg
                    assert "circles_count" in msg
                    assert "circles" in msg
                    assert isinstance(msg["circles"], list)
                    assert isinstance(msg["generation"], int)
                    assert isinstance(msg["circles_count"], int)
                elif msg["type"] == "complete":
                    # Small gasket might complete immediately
                    assert "total_circles" in msg
                    assert "gasket_id" in msg
