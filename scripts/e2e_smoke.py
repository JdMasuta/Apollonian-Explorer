#!/usr/bin/env python3
"""
End-to-end smoke test against a running backend (default localhost:8000).

Reference: REVAMP_BLUEPRINT.md Milestone 6. Drives the full research flow
over the real wire protocols: WebSocket generation (classic + strip),
viewport deepening, parabolic cusp chains, Möbius transform, analytics,
and all three export formats. Exits non-zero on any failure.

Usage: python scripts/e2e_smoke.py [base_host]
(Requires the `websockets` package — already a backend dependency.)
"""

import asyncio
import json
import sqlite3
import sys
import tempfile
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost:8000"
BASE = f"http://{HOST}/api/gaskets"


def jpost(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def jget(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


async def ws_generate(curvatures, depth, min_radius=None):
    import websockets

    msg = {"action": "start", "curvatures": curvatures, "max_depth": depth}
    if min_radius is not None:
        msg["min_radius"] = min_radius
    async with websockets.connect(
        f"ws://{HOST}/ws/gasket/generate", open_timeout=10, max_size=20 * 1024 * 1024
    ) as ws:
        await ws.send(json.dumps(msg))
        total, kinds = 0, {}
        while True:
            m = json.loads(await asyncio.wait_for(ws.recv(), 120))
            if m["type"] == "progress":
                total += m["circles_count"]
                for c in m["circles"]:
                    kinds[c.get("kind", "circle")] = kinds.get(c.get("kind", "circle"), 0) + 1
            else:
                assert m["type"] == "complete", m
                return m, kinds


def main():
    # Health
    health = jget(f"http://{HOST}/health")
    assert health["database"] == "connected", health

    # Classic generation over WS (persists)
    complete, _ = asyncio.run(ws_generate(["-1", "2", "2"], 4, 0.002))
    gid = complete["gasket_id"]
    assert isinstance(gid, int) and complete["total_circles"] > 100

    # Second run hits the cache
    again, _ = asyncio.run(ws_generate(["-1", "2", "2"], 4, 0.002))
    assert again["gasket_id"] == gid

    # Strip packing streams lines
    strip, kinds = asyncio.run(ws_generate(["0", "0", "1", "1"], 5, 0.02))
    assert kinds.get("line") == 2, kinds

    # Viewport deepening (word replay)
    deepened = jpost(f"{BASE}/{gid}/deepen", {"word": "0", "min_radius": 1e-4})
    assert deepened["count"] > 0

    # Parabolic cusp chain
    cusp = jpost(f"{BASE}/{gid}/cusp-chain", {"word_a": "S1", "word_b": "S2", "min_radius": 1e-6})
    assert cusp["verified_words"] and cusp["count"] > 100

    # Möbius transform (2 lines from the bend-2 circles)
    transform = jpost(f"{BASE}/{gid}/transform", {"mirror_word": "S0"})
    assert transform["lines"] == 2

    # Analytics
    analytics = jget(f"{BASE}/{gid}/analytics")
    assert analytics["total_circles"] > 100
    assert analytics["dimension_estimate"] is not None
    assert 0.8 < analytics["dimension_estimate"] < 1.31

    # Exports
    csv_text = urllib.request.urlopen(f"{BASE}/{gid}/export?format=csv", timeout=120).read()
    assert csv_text.startswith(b"id,generation,word")
    payload = jget(f"{BASE}/{gid}/export?format=json")
    assert payload["engine_version"] and payload["circles"]
    blob = urllib.request.urlopen(f"{BASE}/{gid}/export?format=sqlite", timeout=120).read()
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as f:
        f.write(blob)
        f.flush()
        conn = sqlite3.connect(f.name)
        rows = conn.execute("SELECT COUNT(*) FROM circles").fetchone()[0]
        conn.close()
    assert rows > 100, rows

    print("e2e smoke: ALL CHECKS PASSED")
    print(f"  gasket={gid}, circles={analytics['total_circles']}, "
          f"delta={analytics['dimension_estimate']:.4f}, strip lines OK, "
          f"deepen/cusp/transform/exports OK")


if __name__ == "__main__":
    main()
