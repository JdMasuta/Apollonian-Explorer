# Apollonian Explorer — Technical Revamp Blueprint

**Status**: Proposal / architectural blueprint
**Scope**: Fork, revamp, and elevate the Apollonian Explorer into a research-grade tool for
mathematical scientists studying Apollonian gaskets and integral circle packings.

---

## PHASE 1 — Codebase Discovery & Structural Assessment

### 1.1 Tech Stack & Architecture

**Monorepo layout**

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3 / FastAPI / Uvicorn | `backend/` — REST (`/api/gaskets`) + WebSocket (`/ws/gasket/generate`) |
| Math core | Pure Python: `fractions.Fraction` + SymPy "hybrid exact arithmetic" | `backend/core/` (~2,600 LOC) |
| Persistence | SQLAlchemy 2 + SQLite | Dual storage: INTEGER num/denom pairs **and** tagged TEXT exact columns |
| Frontend | React 19 + TypeScript 5.9 + Vite 7 | `frontend/` |
| Rendering | **Canvas 2D via Konva / react-konva** (retained-mode scene graph, one node per circle) | `GasketCanvas.tsx` |
| State | Zustand store (`gasketStore.ts`), flat `CircleData[]` | |
| UI | Material-UI v7 | |
| Streaming | Native WebSocket service with batch progress messages | `websocketService.ts` |

**Separation of concerns** is genuinely good at the macro level: all mathematics lives in
`backend/core/` (pure functions, no I/O), with `db/`, `schemas/`, `services/`, `api/` layered
above, and the frontend is purely a consumer. However, the exactness contract **breaks at the
serialization boundary**: circles are serialized as `"num/denom"` strings, and the frontend's
`parseValue()` (`GasketCanvas/utils.ts:31`) immediately collapses them to 64-bit floats. SymPy
irrational values are serialized as lossy approximations (e.g. `sqrt(2)` → `"14142136/10000000"`,
see `circle_data.py:to_dict`). All downstream rendering, bounding boxes, and zoom math are float64.
Zoom is additionally hard-clamped to 0.1×–10× (`GasketCanvas.tsx:148`), so deep exploration is
impossible today regardless of precision.

### 1.2 Current Algorithmic Approach

- **Recursive Descartes Circle Theorem** (curvature + complex-center forms) in
  `core/descartes.py`, driven by a **BFS over circle triplets** in `core/gasket_generator.py`.
- **Hybrid exact arithmetic** (`core/exact_math.py`, 885 LOC): every operation dispatches through
  `smart_add/smart_multiply/smart_sqrt`, escalating `int → Fraction → sympy.Expr`, with frequent
  `sympy.simplify()` calls. This achieves exactness but at enormous per-operation cost — `simplify`
  is one of the slowest operations in SymPy and it sits in the innermost loop.
- **Initial placement** solves tangency constraints symbolically via `sympy.solve`
  (`_solve_third_circle_position_exact`), then **verifies tangency in floating point with a 1e-10
  tolerance** (`verify_tangency`) — an exact pipeline guarded by inexact checks.
- **Deduplication** is the structural weak point. The BFS enqueues 3 child triplets per new circle;
  every circle is reachable along many paths, so the algorithm relies on (a) an MD5 hash of
  stringified exact values and (b) `is_duplicate()`, a linear scan of *all* circles with float
  tolerance. Total complexity is **O(n²)** in circle count, with Fraction/SymPy arithmetic inside
  the scan. The BFS also wraps its body in `except Exception: continue`, silently swallowing math
  errors.
- **Depth limits**: practically ~depth 5–6 on the backend; the project's own HISTORY.md notes the
  frontend is limited to **depth 1–2** before rendering degrades.
- A newer, **unwired** module `core/diophantine_generator.py` implements seed generation for
  integral packings from the Diophantine parametrization B² + μ² = kn — a valuable seed of the
  right idea (integral packings as first-class objects) that the revamp should absorb.
- There is **no Apollonian group / Möbius / matrix-action machinery** today.

### 1.3 Code Quality & Standards

**Strengths**: exemplary documentation culture (CLAUDE.md, HISTORY.md, DEBUG_LOG.md, ISSUES.md,
spec docs); 257 backend test functions across 9 files; typed Python signatures; TypeScript +
ESLint + Vitest on the frontend; clean FastAPI layering.

**Technical debt & bottlenecks**:

1. **Packaging**: `sys.path.insert` hacks inside library modules (`descartes.py`, `websocket.py`,
   `db/models/circle.py`) instead of a proper installable package.
2. **Dead/contradictory code**: unreachable code after `raise` in `_initialize_three_circles`
   (`gasket_generator.py:329-343`); ad-hoc `test_phase*.py` scripts at `backend/` root outside the
   test suite.
3. **Documentation drift in math claims**: e.g. `descartes.py:79` claims
   `descartes_curvature(-1, 2, 2) → (6, 2/3)`; the correct result is the double root `(3, 3)`
   (the discriminant −2+4−2 = 0). CLAUDE.md's sample test asserts `(-1,2,2) → (6, 14/15)`, also
   incorrect. For a rigor-oriented project, the spec documents must be re-derived and re-verified.
4. **Dual DB representation** (num/denom INTEGER columns + tagged TEXT exact columns) doubles
   write paths and invites divergence.
5. **Float tolerances inside the exact pipeline** (`is_duplicate`, `verify_tangency`) — exactness
   is paid for but not exploited.
6. **No CI**, no mypy enforcement, no formatter config committed; frontend uses `any` for Konva
   event types and `@ts-ignore` in tests; only one frontend test file (WebSocket service).
7. **Renderer ceiling**: one Konva node per circle means DOM-like scene-graph overhead per circle;
   unsuitable beyond a few thousand circles. A depth-8 gasket from (−1,2,2,3) has ~10⁴ circles;
   research use needs 10⁵–10⁷.

---

## PHASE 2 — Advanced Mathematical & Feature Specification

### 2.0 The keystone change: inversive coordinates + Apollonian group walk

Nearly every Phase 2 requirement falls out of one representational change, so it is specified
first. Replace per-circle `(curvature, center)` + Descartes-with-square-roots by
**augmented curvature–center ("inversive") coordinates** (Lagarias–Mallows–Wilks, *Beyond the
Descartes Circle Theorem*):

```
v(C) = (b̄, b, b·x, b·y)
```

where `b` is the curvature, `(x, y)` the center, and `b̄ = b(x²+y²) − 1/b` the **co-curvature**
(curvature of the image of C under inversion in the unit circle). Lines are the `b = 0` case and
are represented natively. Each circle satisfies the quadratic constraint
`Q(v) = b̄·b − (bx)² − (by)² = −1`, which becomes an **exact integer/rational invariant checkable
in unit tests with equality, not tolerance**.

The generation step becomes the **Apollonian group action**. Given a tangent quartet
`(v₁, v₂, v₃, v₄)`, the reflection that replaces circle *j* with the "other" solution is linear:

```
Sⱼ:  vⱼ ← 2(vₐ + v_b + v_c) − vⱼ        (a, b, c = the other three indices)
```

Consequences:

- **No square roots after seeding.** Generation is 4 vector additions per circle — pure integer
  arithmetic for integral packings (all four coordinates of every circle in a primitive integral
  packing are integers), pure rational arithmetic otherwise.
- **No deduplication needed.** The Apollonian group is the free product ℤ/2 ∗ ℤ/2 ∗ ℤ/2 ∗ ℤ/2;
  reduced words (never repeat the generator you just applied) are in bijection with circles. The
  generator becomes a **spanning-tree walk: every circle produced exactly once, O(1) per circle**,
  versus today's O(n²) hash-plus-tolerance scan.
- **Exact tangency for free**: the inversive inner product of two tangent circles is a fixed
  integer value; tangency verification becomes an exact algebraic identity.
- **Seeds with irrational coordinates stay closed**: reflections are ℤ-linear, so every circle
  lies in the ℤ-module spanned by the four seed vectors. A circle can even be stored as an
  integer 4-vector of coefficients over the seed basis, confining all irrationality to 4 constants.

### 2.1 Arbitrary & Exact Arithmetic Precision

**Backend**
- Python `int` is already arbitrary-precision; with the group-walk representation, integral
  packings need **only big integers** — no Fraction, no SymPy in the hot loop. Optional `gmpy2`
  (`mpz`/`mpq`) backend for 5–20× speedups at depth ≫ 10 (bends grow exponentially with word
  length; depth-30 bends overflow i64 but are trivial for bigints).
- SymPy is **demoted to the seeding layer only**: completing a curvature triple to a quartet
  (one square root), solving custom seed placements, and pretty-printing exact values. Retire
  `smart_*` dispatch from generation entirely.

**Frontend**
- Wire format: exact decimal strings or `num/denom` strings, plus a float64 fast field.
- Client keeps a **rational/BigInt camera**: viewport center stored as exact rationals
  (`BigInt` numerator/denominator). For rendering, compute `(position − camera_center)` **in exact
  arithmetic**, then convert the small residual to f64. This is the standard deep-zoom technique:
  f64 has ~15–16 significant digits of *relative* precision, so camera-relative coordinates remain
  exact-to-the-pixel at 10⁻¹⁵, 10⁻³⁰, or any scale — the exactness lives in the rebasing, not the GPU.

### 2.2 Flexible Initial Conditions & Seed Configurations

Introduce a `Seed` abstraction (`backend/core/engine/seeds.py`) with constructors:

1. **Classic**: named presets — (−1, 2, 2, 3), (0, 0, 1, 1) strip, (−1, 1, 1) etc., with
   canonical exact placements.
2. **Integer quadruples**: user supplies (k₁..k₄); validate the Descartes equation
   `2Σkᵢ² = (Σkᵢ)²` exactly; auto-solve centers by canonical construction in inversive
   coordinates (root quadruple placed in normal form: bounding circle centered at origin,
   largest interior circle on the x-axis). Absorb `diophantine_generator.py`: the
   B² + μ² = kn parametrization becomes an **integral-packing browser** that enumerates
   primitive root quadruples for the user to pick from.
3. **Curvature triples**: complete to a quartet via Descartes (the one place a square root is
   taken), then proceed integrally/rationally.
4. **Strips & belts (unbounded packings)**: `b = 0` lines are first-class in inversive
   coordinates; the Apollonian strip (0, 0, 1, 1) and half-plane packings work with the *same*
   generator and renderer (renderer draws `b = 0` instances as lines).
5. **Direct geometric input**: three user-drawn mutually tangent circles (exactness obtained by
   snapping to rational centers/radii satisfying tangency, solved at seed time).

### 2.3 Advanced Visualizations & Group Actions

**Coloring metrics** — a `ColorMetric` interface: `metric(circle) → t ∈ [0,1]` + palette,
computed backend-side and shipped as a per-circle scalar attribute:
- generation depth / group word length;
- log-curvature;
- **residue classes**: bends of an integral packing mod 24 hit a fixed set of residues — color by
  `b mod m` for user-chosen m (visualizes the local-global phenomenon);
- parity, prime bends, prime-power bends (`sympy.factorint`, cached);
- orbit coloring: which generator Sᵢ produced the circle (the four "limbs" of the group), or
  color by first letter of the group word.

**Hyperbolic geometry & inversions**
- Möbius/inversion transforms act on inversive coordinates as **O(3,1) Lorentz matrices** —
  implement a `Transform` type (4×4 rational matrix) with: inversion in any circle of the packing,
  the four **dual Apollonian group** generators (reflections in the dual circles through tangency
  points), and the S₃/S₄ symmetries permuting the root quartet.
- UI tools: click a circle → animate inversion of the whole packing through it (animate in float,
  land on exact); toggle dual-circle overlay; "orbit highlighting" — select a circle and highlight
  its orbit under a chosen subgroup; optional Poincaré-disk side view of the packing as a
  hyperbolic tiling boundary.

**Infinite vector zooming** — three cooperating mechanisms:
1. **WebGL instanced renderer**: circles as instanced quads with a signed-distance-function
   fragment shader → perfectly anti-aliased discs/rings at any magnification, ~10⁶ instances at
   60 fps. (Konva is retained only for UI overlays, or dropped.)
2. **Camera-relative exact coordinates** (see 2.1): GPU only ever sees small numbers.
3. **Viewport-driven lazy generation**: replace fixed `max_depth` with an *output-sensitive*
   contract — the walk prunes any subtree whose circle lies outside the view rectangle or whose
   radius < ε·pixel. Zooming in streams deeper circles for the visible region only. This is the
   single most important architectural change for "infinite" zoom: depth becomes a function of
   the camera, not a global parameter.

### 2.4 Data Analytics & Research Export

**Statistics panel** (backend-computed, cached per packing):
- Curvature distribution histogram (linear & log binning), live-updating during generation.
- **Counting function N(T)** = #{circles: b ≤ T}, with log-log plot and fitted slope. By
  Kontorovich–Oh, N(T) ~ c·T^δ with δ ≈ **1.305688** (the packing's Hausdorff dimension,
  McMullen) — the fitted exponent is displayed against the reference value with residuals.
- Secondary estimators: radius-sum moments Σrˢ vs s (dimension as the exponent where the sum
  transitions), box-counting on the rendered set as a cross-check.
- Integral-packing diagnostics: residues mod 24 observed vs admissible, prime-bend counts vs
  the prime number theorem analogue for packings.

**Export pipelines** (`/api/gaskets/{id}/export?format=csv|json|sqlite|parquet`):
- Columns: `id, generation, word (group word string), parent_id, k_exact, k_float, x_exact,
  x_float, y_exact, y_float, r_float, cocurvature, residue_24, is_prime_bend, tangent_ids`.
- Exact values as canonical strings (integer or `p/q`); streamed (chunked) responses so 10⁷-circle
  dumps don't buffer in RAM; SQLite export ships the schema documented for
  Mathematica/Pandas/Julia consumption; JSON export includes seed metadata + generator provenance
  for reproducibility.

---

## PHASE 3 — Engineering & Performance Architecture Uplift

### 3.1 Type Safety & Maintainability

**Backend**
- Convert `backend/` into an installable package (`pyproject.toml`, `apollonian/` namespace);
  delete all `sys.path` hacks.
- `mypy --strict` on `core/engine/`; ruff (lint + isort) + black, enforced in CI.
- Core interfaces: `InversiveCircle` (frozen dataclass of 4 exact scalars + cached f64 mirror),
  `Quartet`, `Seed`, `Transform` (O(3,1) matrix), `WalkBudget` (depth/curvature/viewport bounds),
  `ColorMetric`, `Exporter` protocols.
- Pydantic v2 models remain the API boundary; exact scalars cross it as strings only.

**Frontend**
- Eliminate `any` (Konva event generics or removal of Konva); ban `@ts-ignore` in favor of typed
  test fixtures.
- **Generate API types from the backend OpenAPI schema** (`openapi-typescript`) so
  `CircleData`/`GasketMetadata` cannot drift from the server.
- Shared `Rational`/`BigRational` utility module (BigInt-based) with its own test suite.

### 3.2 Computational Optimization

**Backend** — the current WebSocket handler runs generation on the event loop:
- Move generation into a **worker process** (`ProcessPoolExecutor` / `multiprocessing.Process`)
  feeding an `asyncio` queue; the WS handler only drains/serializes. Supports cancellation
  (client disconnect kills the job) and parallel sessions.
- The four subtrees under the root quartet are independent → embarrassingly parallel across
  processes for bulk/analytics jobs.
- Optional (flagged) `gmpy2` arithmetic backend; optional Rust/PyO3 kernel later if research
  workloads demand 10⁸ circles — the engine API is designed so the kernel is swappable.

**Frontend**
- **Web Worker math pipeline**: WS messages parsed in a worker; exact→camera-relative conversion
  and instance-buffer packing happen off the main thread; the render thread receives transferable
  `Float32Array` instance buffers only. Main thread = React UI + WebGL draw calls.
- Spatial index (flat quadtree / R-tree over float bounds) in the worker for picking and viewport
  queries.

### 3.3 Testing Strategy

- **Unit (exact, equality-based — no tolerances)**:
  - Descartes quadratic-form invariant: `Q(v) = −1` preserved by every reflection and transform.
  - Reflection involution: `Sⱼ² = id` exactly; quartet tangency Gramian invariant under the group.
  - Tangency: inversive inner product equals its exact expected value.
  - Seed solvers: quadruple validation `2Σkᵢ² = (Σkᵢ)²`; line/strip seeds.
  - Legacy cross-check: new engine vs `descartes.py` on rational fixtures (then retire the latter
    from production paths, keep as test oracle).
- **Property-based (Hypothesis)**: random valid quartets → all invariants hold after random
  reduced words; serialization round-trips exactly; viewport-pruned walk ⊆ unpruned walk.
- **Regression**: classic packings yield verified bend multisets — (−1,2,2,3) →
  {3, 6, 6, 11, 14, 15, 23, …}; (−11,21,24,28); strip (0,0,1,1) → Ford-circle bends (perfect
  squares); counts per generation match the exact recurrence (4·3^(g−1) new circles at
  generation g for the bounded gasket).
- **Integration**: REST + WS protocol tests (httpx/pytest-asyncio), export-format golden files.
- **Frontend**: Vitest for stores/workers/Rational; Playwright smoke (seed → render → zoom →
  select → export); WebGL snapshot tests on a reference scene.
- **CI**: GitHub Actions matrix (backend lint+mypy+pytest, frontend lint+tsc+vitest+build),
  plus a perf job tracking circles/sec on a pinned benchmark.

---

## PHASE 4 — Actionable Revamp Roadmap

### Milestone 0 — Foundations & Hygiene (≈1 week)
*Goal: trustworthy ground to build on.*
- **Create**: `pyproject.toml` (package `apollonian`), `.github/workflows/ci.yml`, ruff/black/mypy configs.
- **Modify**: remove `sys.path` hacks (`core/descartes.py`, `api/endpoints/websocket.py`,
  `db/models/circle.py`); delete dead code in `core/gasket_generator.py:329-343`; correct the
  erroneous worked examples in `descartes.py` docstrings, CLAUDE.md, and spec docs.
- **Move/Delete**: `backend/test_phase*.py`, `backend/debug_tangency.py` → `backend/tests/` or remove.
- **Fix**: ISSUES.md #1 (redundant post-commit re-fetch in `services/gasket_service.py`).

### Milestone 1 — Core Math Engine Refactor (≈2–3 weeks)
*Goal: exact, dedup-free, O(1)-per-circle generation.*
- **Create** `backend/core/engine/`:
  - `inversive.py` — `InversiveCircle`, quadratic form, inner products, exact tangency.
  - `group.py` — reflections S₁..S₄, dual generators, `Transform` (O(3,1) matrices).
  - `seeds.py` — classic presets, quadruple validation & canonical placement, triple completion,
    strip seeds; **absorbs `diophantine_generator.py`** (root-quadruple enumeration).
  - `walk.py` — reduced-word spanning-tree generator with `WalkBudget` (depth / max bend /
    viewport / count), streaming iterator.
  - `metrics.py` — color metrics, residues, prime-bend tagging.
- **Create tests**: `tests/engine/test_inversive.py`, `test_group.py`, `test_seeds.py`,
  `test_walk.py`, `test_regression_bends.py`, Hypothesis suites.
- **Deprecate**: `core/gasket_generator.py` (replaced by `walk.py`); `core/exact_math.py`
  shrinks to seed-time helpers; `core/descartes.py` kept as test oracle only.
- **Acceptance**: depth-10 (−1,2,2,3) in < 1 s; zero duplicates by construction; all invariants
  exact.

### Milestone 2 — Services, Persistence & Protocol v2 (≈2 weeks)
*Goal: viewport-driven, non-blocking serving.*
- **Modify**: `db/models/circle.py` → schema v2 (single exact representation: 4 coordinate
  TEXT/BLOB columns + f64 mirrors + `word`, drop the dual num/denom-vs-tagged-TEXT split, with
  `migrations/002_inversive_schema.py`); `services/gasket_service.py` → lazy expansion service
  ("ensure circles for viewport V at resolution ε"); `api/endpoints/websocket.py` → worker-process
  generation + cancellation; `api/endpoints/gaskets.py` → viewport query params.
- **Create**: `api/endpoints/export.py` (CSV/JSON/SQLite/Parquet streaming),
  `api/endpoints/analytics.py` (histogram, N(T), δ-fit), spatial index column/strategy.

### Milestone 3 — Rendering & UI Overhaul (≈2–3 weeks)
*Goal: 10⁶ circles, infinite zoom.*
- **Create** `frontend/src/renderer/` (WebGL2 instanced SDF circle renderer, camera-relative),
  `frontend/src/math/rational.ts` (BigInt rationals), `frontend/src/workers/mathWorker.ts`
  (parse/pack/index), `frontend/src/camera/exactCamera.ts` (rational camera + origin rebasing,
  remove the 0.1–10× clamp).
- **Modify**: `GasketCanvas/` becomes a thin shell over the renderer (Konva retained only for
  overlays or removed); `gasketStore.ts` holds metadata/selection only — bulk geometry lives in
  worker-owned buffers; `websocketService.ts` → protocol v2 (binary frames optional).
- **Acceptance**: smooth zoom to ≤10⁻¹⁵ with on-demand deepening; 60 fps at 10⁵ visible circles.

### Milestone 4 — Research Tooling (≈2 weeks)
- **Create**: `frontend/src/components/AnalyticsPanel/` (histogram, N(T) log-log + δ vs 1.305688),
  `ColorMetricPicker`, `ExportDialog`; backend metric/export wiring from M2.
- Reproducibility: every export embeds seed + engine version + budget.

### Milestone 5 — Group-Action Explorer (≈2 weeks)
- **Create**: inversion tool (click-to-invert with animated Möbius interpolation), dual-group
  overlay, orbit highlighting, strip/belt seed UI, S₃/S₄ symmetry controls
  (`frontend/src/components/TransformPanel/`, backend `engine/group.py` already provides the math).

### Milestone 6 — Hardening & Release (≈1 week)
- Playwright e2e, perf benchmarks in CI, README/spec rewrite (replacing stale math examples),
  versioned docs, packaged demo deployment.

**Deprecation summary**: `core/exact_math.py` (885 LOC → ~100 LOC seed helpers),
`core/gasket_generator.py` (replaced), `core/diophantine_generator.py` (absorbed into
`engine/seeds.py`), dual DB columns (collapsed), Konva rendering path (replaced or demoted),
float-tolerance `is_duplicate`/`verify_tangency` (replaced by exact identities).
