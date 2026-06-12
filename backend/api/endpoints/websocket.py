"""
WebSocket endpoint for real-time gasket generation streaming.

Reference: REVAMP_BLUEPRINT.md Milestone 2; .DESIGN_SPEC.md section 5.3.

Protocol (v1-compatible, additive):
1. Client connects to /ws/gasket/generate
2. Client sends: {"action": "start", "curvatures": [...], "max_depth": N,
                  "min_radius": optional float}
3. Server streams: {"type": "progress", "generation": g,
                    "circles_count": n, "circles": [...]}
4. Server ends with {"type": "complete", "gasket_id": null, "total_circles": N}
   or {"type": "error", "message": "..."} and closes (one run per connection;
   the frontend reconnects per generate).

Generation runs in a worker thread feeding an asyncio queue, so the event
loop (and every other client) stays responsive during deep walks; a client
disconnect stops the producer via a threading.Event.
"""

import asyncio
import json
import threading
from typing import Iterator, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from core.engine.walk import GeneratedCircle, WalkBudget, walk
from schemas import GasketCreate
from services.gasket_service import build_seed, parse_curvature_string, persist_walk_records
from services.serializers import record_to_api_circle

router = APIRouter()

#: Circles per progress message. Large batches keep message counts low so the
#: client is not flooded (DEBUG_LOG ERR-013); 500 circles ≈ 60 KB JSON.
BATCH_SIZE = 500

#: Producer -> consumer queue depth (backpressure bound).
QUEUE_MAX = 8


def generate_records(
    curvatures: List[str], max_depth: int, min_radius: Optional[float]
) -> Iterator[GeneratedCircle]:
    """Seed and walk a packing from API curvature strings.

    Module-level seam so tests can patch generation. Lines (only possible
    from strip seeds, which the API schema rejects) are skipped defensively.
    """
    parsed = [parse_curvature_string(c) for c in curvatures]
    seed = build_seed(parsed)
    budget = WalkBudget(max_depth=max_depth, min_radius=min_radius)
    for record in walk(seed, budget):
        if record.circle.is_line:
            continue
        yield record


def _produce(
    curvatures: List[str],
    max_depth: int,
    min_radius: Optional[float],
    queue: "asyncio.Queue[dict]",
    loop: asyncio.AbstractEventLoop,
    stop: threading.Event,
) -> None:
    """Worker thread: run the walk, push batched messages onto the queue."""

    def put(message: dict) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(message), loop).result()

    total = 0
    batch: List[dict] = []
    records: List[GeneratedCircle] = []
    last_generation = 0
    try:
        for record in generate_records(curvatures, max_depth, min_radius):
            if stop.is_set():
                return
            batch.append(record_to_api_circle(record))
            records.append(record)
            last_generation = record.generation
            total += 1
            if len(batch) >= BATCH_SIZE:
                put(
                    {
                        "type": "progress",
                        "generation": last_generation,
                        "circles_count": len(batch),
                        "circles": batch,
                    }
                )
                batch = []

        if batch and not stop.is_set():
            put(
                {
                    "type": "progress",
                    "generation": last_generation,
                    "circles_count": len(batch),
                    "circles": batch,
                }
            )
        if not stop.is_set():
            # Persist the run (best-effort) so analytics/export can use it.
            gasket_id = persist_walk_records(curvatures, max_depth, min_radius, records)
            put({"type": "complete", "gasket_id": gasket_id, "total_circles": total})
    except Exception as e:  # surfaced to the client as a protocol error
        if not stop.is_set():
            put({"type": "error", "message": f"Generation error: {str(e)}"})


@router.websocket("/ws/gasket/generate")
async def websocket_gasket_generate(websocket: WebSocket):
    """Stream gasket generation over a WebSocket (see module docstring)."""
    await websocket.accept()

    try:
        # ---- Request validation (shapes unchanged from v1) ----
        data = await websocket.receive_text()

        try:
            message = json.loads(data)
        except json.JSONDecodeError as e:
            await websocket.send_json(
                {"type": "error", "message": f"Invalid JSON: {str(e)}"}
            )
            await websocket.close()
            return

        if not isinstance(message, dict):
            await websocket.send_json(
                {"type": "error", "message": "Message must be a JSON object"}
            )
            await websocket.close()
            return

        action = message.get("action")
        if action != "start":
            await websocket.send_json(
                {"type": "error", "message": f"Unknown action: {action!r}. Expected 'start'."}
            )
            await websocket.close()
            return

        curvatures = message.get("curvatures")
        max_depth = message.get("max_depth")
        if curvatures is None:
            await websocket.send_json(
                {"type": "error", "message": "Missing required field: 'curvatures'"}
            )
            await websocket.close()
            return
        if max_depth is None:
            await websocket.send_json(
                {"type": "error", "message": "Missing required field: 'max_depth'"}
            )
            await websocket.close()
            return

        try:
            validated = GasketCreate(
                curvatures=curvatures,
                max_depth=max_depth,
                min_radius=message.get("min_radius"),
            )
        except ValidationError as e:
            details = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )
            await websocket.send_json(
                {"type": "error", "message": "Validation error: " + details}
            )
            await websocket.close()
            return

        # ---- Generation in a worker thread, streaming from a queue ----
        queue: "asyncio.Queue[dict]" = asyncio.Queue(maxsize=QUEUE_MAX)
        stop = threading.Event()
        loop = asyncio.get_running_loop()
        producer = loop.run_in_executor(
            None,
            _produce,
            validated.curvatures,
            validated.max_depth,
            validated.min_radius,
            queue,
            loop,
            stop,
        )

        try:
            while True:
                message_out = await queue.get()
                await websocket.send_json(message_out)
                if message_out["type"] in ("complete", "error"):
                    break
        except WebSocketDisconnect:
            raise
        finally:
            stop.set()
            # Unblock a producer waiting on a full queue, then let it finish.
            while not queue.empty():
                queue.get_nowait()
            try:
                await producer
            except Exception:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Server error: {str(e)}"}
            )
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
