"""
WebSocket endpoint for real-time gasket generation streaming.

Reference: IMPLEMENTATION_PLAN.md Phase 2 Day 5 Task 1
Reference: DESIGN_SPEC.md section 5.3 (WebSocket API)

This module implements the WebSocket endpoint for streaming Apollonian gasket
generation in real-time. Clients connect, send initial parameters, and receive
circles in batches as they are generated.
"""

import asyncio
import json
from typing import List
from fractions import Fraction

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

# Use relative import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.gasket_generator import generate_apollonian_gasket
from schemas import GasketCreate

router = APIRouter()


@router.websocket("/ws/gasket/generate")
async def websocket_gasket_generate(websocket: WebSocket):
    """
    WebSocket endpoint for real-time gasket generation streaming.

    Protocol:
    1. Client connects to /ws/gasket/generate
    2. Client sends: {"action": "start", "curvatures": ["1", "1", "1"], "max_depth": 5}
    3. Server streams progress messages with batches of circles
    4. Server sends completion message when done

    Message Types:
    - Progress: {"type": "progress", "generation": N, "circles_count": M, "circles": [...]}
    - Complete: {"type": "complete", "gasket_id": null, "total_circles": N}
    - Error: {"type": "error", "message": "..."}

    Args:
        websocket: FastAPI WebSocket connection

    Reference:
        IMPLEMENTATION_PLAN.md lines 836-923 (Day 5 Task 1)
    """
    await websocket.accept()

    try:
        # Step 1: Receive initial request message
        data = await websocket.receive_text()

        try:
            message = json.loads(data)
        except json.JSONDecodeError as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid JSON: {str(e)}"
            })
            await websocket.close()
            return

        # Step 2: Validate message structure
        if not isinstance(message, dict):
            await websocket.send_json({
                "type": "error",
                "message": "Message must be a JSON object"
            })
            await websocket.close()
            return

        action = message.get("action")
        if action != "start":
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown action: '{action}'. Expected 'start'."
            })
            await websocket.close()
            return

        # Step 3: Extract and validate parameters
        curvatures = message.get("curvatures")
        max_depth = message.get("max_depth")

        if curvatures is None:
            await websocket.send_json({
                "type": "error",
                "message": "Missing required field: 'curvatures'"
            })
            await websocket.close()
            return

        if max_depth is None:
            await websocket.send_json({
                "type": "error",
                "message": "Missing required field: 'max_depth'"
            })
            await websocket.close()
            return

        # Step 4: Validate using Pydantic schema (reuse existing validation)
        try:
            validated = GasketCreate(curvatures=curvatures, max_depth=max_depth)
        except ValidationError as e:
            # Extract error messages from Pydantic validation
            error_messages = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                error_messages.append(f"{field}: {error['msg']}")

            await websocket.send_json({
                "type": "error",
                "message": "Validation error: " + "; ".join(error_messages)
            })
            await websocket.close()
            return

        # Step 5: Parse curvatures as Fractions
        try:
            curvature_fractions = [Fraction(c) for c in validated.curvatures]
        except (ValueError, ZeroDivisionError) as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Invalid curvature format: {str(e)}"
            })
            await websocket.close()
            return

        # Step 6: Generate gasket with streaming
        total_circles = 0
        batch = []
        batch_size = 10

        try:
            # Use streaming generator
            for circle_data in generate_apollonian_gasket(
                curvature_fractions,
                validated.max_depth,
                stream=True
            ):
                batch.append(circle_data.to_dict())
                total_circles += 1

                # Send batch when it reaches batch_size
                if len(batch) >= batch_size:
                    await websocket.send_json({
                        "type": "progress",
                        "generation": circle_data.generation,
                        "circles_count": len(batch),
                        "circles": batch
                    })

                    batch = []  # Clear batch

                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.01)

            # Send remaining circles in final batch
            if batch:
                await websocket.send_json({
                    "type": "progress",
                    "generation": batch[-1]["generation"],
                    "circles_count": len(batch),
                    "circles": batch
                })

            # Step 7: Send completion message
            # TODO: Save gasket to database and return gasket_id
            # For now, gasket_id is null - will implement in later phase
            await websocket.send_json({
                "type": "complete",
                "gasket_id": None,
                "total_circles": total_circles
            })

        except Exception as e:
            # Handle errors during generation
            await websocket.send_json({
                "type": "error",
                "message": f"Generation error: {str(e)}"
            })
            await websocket.close()
            return

    except WebSocketDisconnect:
        # Client disconnected - gracefully handle
        # No need to send message as connection is already closed
        pass

    except Exception as e:
        # Unexpected error - try to send error message if connection still open
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
        except:
            # Connection already closed, nothing we can do
            pass

    finally:
        # Ensure connection is closed
        try:
            await websocket.close()
        except:
            # Already closed
            pass
