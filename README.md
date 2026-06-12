# Apollonian Explorer

A research-grade tool for generating, exploring, and analyzing Apollonian
gaskets and related circle packings — built on an **exact arithmetic engine**
with deep-zoom rendering and number-theoretic analytics.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node](https://img.shields.io/badge/node-22+-green.svg)

## What it does

- **Exact generation engine** (`backend/core/engine/`): circles live in
  augmented curvature–center (inversive) coordinates (Lagarias–Mallows–Wilks);
  generation is the Apollonian group action — ℤ-linear reflections, no square
  roots after seeding, no floating-point tolerances anywhere. Every circle is
  enumerated exactly once via reduced words (the words ARE the identities),
  ~200k circles/sec for integral packings.
- **Seeds**: named presets, Descartes quadruples (validated exactly),
  curvature triples (completed via the Descartes relation), and the
  Apollonian strip (0, 0, 1, 1) with true lines.
- **Deep zoom**: a BigInt-rational exact camera (no zoom clamp; pixel-exact
  at 10⁻¹² and beyond), WebGL2 instanced SDF rendering (~10⁵ circles at
  60 fps), and viewport-driven refinement that resumes the generation walk at
  a circle's group word — output-sensitive at any magnification. Cusp
  (tangency-point) zooms use the exact parabolic closed form
  C_n = C_0 + nV + n²(A+B): O(1) per chain element.
- **Group actions**: exact Möbius inversions (Lorentz reflections on
  inversive vectors), the dual Apollonian group, orbit coloring.
- **Research analytics**: bend histograms, the counting function N(T), and a
  growth-exponent fit against the Hausdorff dimension δ ≈ 1.305688
  (Kontorovich–Oh / McMullen); coloring by residue mod m, parity, prime
  bends, generation, or group orbit.
- **Exports**: streaming CSV / JSON / SQLite with exact coordinate strings,
  float mirrors, residues mod 24, prime-bend tags, and reproducibility
  metadata (engine version + generation budgets).

## Quickstart

```bash
# Backend (FastAPI, port 8000)
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload --port 8000

# Frontend (Vite + React, port 5173, proxies /api and /ws to :8000)
cd frontend && npm install && npm run dev

# Or both at once from the repo root (uses backend/venv if present)
npm install && npm run dev
```

Open http://localhost:5173, enter 3–4 curvatures (e.g. `-1, 2, 2` or the
strip `0, 0, 1, 1`), Generate, and zoom — detail refines on demand.

## API surface

| Endpoint | Purpose |
|---|---|
| `WS /ws/gasket/generate` | Stream a generation run (`{action, curvatures, max_depth, min_radius?}`); persists on completion |
| `POST /api/gaskets` | Create/expand the cached packing (resolution-aware, incremental) |
| `GET /api/gaskets/{id}/circles` | Viewport queries (bbox + min radius on indexed float mirrors) |
| `POST /api/gaskets/{id}/deepen` | Local refinement: resume the walk at a circle's group word |
| `POST /api/gaskets/{id}/cusp-chain` | Parabolic chain at a tangency point (exact closed form) |
| `POST /api/gaskets/{id}/transform` | Möbius inversion of the packing in one of its circles |
| `GET /api/gaskets/{id}/analytics` | Histogram, N(T), dimension-exponent fit |
| `GET /api/gaskets/{id}/export?format=csv\|json\|sqlite` | Research data dumps |

## Development

- Backend: `cd backend && pytest tests/ -q` (~370 exact-equality tests, no
  tolerances), `ruff check .`, `mypy` (strict on the engine),
  `python benchmark.py` (perf gate).
- Frontend: `cd frontend && npx vitest run && npx eslint . && npm run build`.
- End-to-end: `python scripts/e2e_smoke.py` against a running backend.
- CI runs all of the above (`.github/workflows/ci.yml`).

## Documentation map

- `REVAMP_BLUEPRINT.md` — architecture and milestone roadmap (authoritative)
- `HISTORY.md` — implementation log (what, when, why)
- `DEBUG_LOG.md` / `ISSUES.md` — error database and issue tracker
- `backend/core/engine/*.py` — the mathematics, documented in module docstrings
- `.DESIGN_SPEC.md`, `API_USAGE_GUIDE.md` — historical (pre-revamp) documents

## Mathematical background

An Apollonian gasket arises from three mutually tangent circles by endlessly
inscribing tangent circles into the gaps. Bends (curvatures) of integral
packings are governed by the Descartes relation
2(k₁²+k₂²+k₃²+k₄²) = (k₁+k₂+k₃+k₄)²; the packing's residual set has Hausdorff
dimension ≈ 1.305688, and bends mod 24 obey local–global residue classes —
all of which this tool lets you compute, color, and export exactly.
