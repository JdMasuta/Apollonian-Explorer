#!/usr/bin/env python3
"""
CI performance gate (REVAMP_BLUEPRINT.md Milestone 6).

Pins the engine's generation throughput; fails (non-zero exit) on a >2x
regression from the recorded baselines (measured ~220k circles/s for the
integral walk; thresholds set at half of a conservative baseline).
"""

import time

from core.engine.seeds import seed_from_preset, seed_from_triple
from core.engine.walk import WalkBudget, walk


def bench(label, seed, budget, minimum_rate):
    start = time.time()
    count = sum(1 for _ in walk(seed, budget))
    elapsed = time.time() - start
    rate = count / elapsed if elapsed > 0 else float("inf")
    status = "OK" if rate >= minimum_rate else "REGRESSION"
    print(f"{label}: {count} circles in {elapsed:.2f}s = {rate:,.0f}/s "
          f"(gate {minimum_rate:,.0f}/s) {status}")
    return rate >= minimum_rate


def main():
    ok = True
    ok &= bench(
        "integral depth-10 walk",
        seed_from_preset("classic"),
        WalkBudget(max_depth=10),
        50_000,
    )
    ok &= bench(
        "irrational budgeted walk (depth 15, min_radius 3e-3)",
        seed_from_triple(1, 1, 1),
        WalkBudget(max_depth=15, min_radius=3e-3),
        1_000,
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
