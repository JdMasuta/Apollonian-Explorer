# Debug Log

**Purpose**: This document is a searchable database of all errors encountered and their solutions. It prevents solving the same problem twice and provides quick reference for debugging.

---

## How to Use This File (For Claude)

### CRITICAL: Search Before Debugging

**BEFORE attempting to fix ANY error**, you MUST:
1. Copy key phrases from the error message
2. Search this file using the methods below
3. If a similar error exists, try that solution first
4. Only proceed with new debugging if no match found

### Quick Search Guide

#### Method 1: Search by Error Message Keywords
```bash
# Search for specific error text
grep -i "import error" DEBUG_LOG.md

# Search for error codes
grep "ERR-" DEBUG_LOG.md | grep "import"

# Case-insensitive search with context
grep -i -A 10 "module not found" DEBUG_LOG.md
```

#### Method 2: Search by File/Module
```bash
# Find all errors in a specific file
grep "descartes.py" DEBUG_LOG.md

# Find all backend errors
grep "### Backend" -A 50 DEBUG_LOG.md

# Find all database errors
grep "### Database" -A 50 DEBUG_LOG.md
```

#### Method 3: Search by Error Type
```bash
# Find all import errors
grep "Import Error" DEBUG_LOG.md

# Find all type errors
grep "TypeError" DEBUG_LOG.md

# Find all test failures
grep "Test Failure" DEBUG_LOG.md
```

#### Method 4: Search by Date (Recent Errors)
```bash
# Find errors from today
grep "2025-10-29" DEBUG_LOG.md

# Find errors from October 2025
grep "2025-10-" DEBUG_LOG.md
```

### When to Update

**ALWAYS** update this file after resolving ANY error, including:
- Import/dependency errors
- Test failures
- Runtime errors
- Compilation/build errors
- Type errors
- Logic bugs
- Performance issues
- Configuration problems

### Required Format

```markdown
#### [ERR-XXX] YYYY-MM-DD - Brief Error Title
**Error Message**:
```
Full error message or stack trace
```
**Context**: Where/when the error occurred (file, function, test)
**Root Cause**: What actually caused the error (be specific)
**Solution**: Exact steps taken to fix it
**Prevention**: How to avoid this error in the future
**Related**: Links to similar errors (ERR-XXX)
**Files Changed**: List of files modified to fix the error
```

### Error ID Numbering

- Start at ERR-001
- Increment by 1 for each new error
- IDs are never reused
- Use same ID if adding updates to an existing error

### Example Entry

```markdown
#### [ERR-003] 2025-10-29 - Module 'fractions' Import Fails in Numba JIT
**Error Message**:
```
TypeError: Cannot determine Numba type of <class 'fractions.Fraction'>
  File "backend/core/descartes.py", line 15, in descartes_curvature
```
**Context**: Attempting to JIT compile descartes_curvature() function with Numba
**Root Cause**: Numba does not support Python's fractions.Fraction type. It only supports primitive numeric types (int, float, complex).
**Solution**:
1. Removed @jit decorator from descartes_curvature()
2. Added conversion helper: fraction_to_float() for rendering only
3. Kept exact Fraction arithmetic for core calculations
4. Will revisit optimization in Phase 7
**Prevention**:
- Check Numba supported types before using @jit: https://numba.pydata.org/numba-doc/latest/reference/pysupported.html
- Use Numba only for numerical (float/int) operations
- Keep Fraction calculations in pure Python
**Related**: None yet
**Files Changed**:
- `backend/core/descartes.py` - Removed @jit decorator
- `backend/utils/rational.py` - Added fraction_to_float() helper
```

---

## Log Entries

### Backend Errors

#### [ERR-001] 2025-10-29 - Example: SQLAlchemy Session Not Closed
**Error Message**:
```
ResourceWarning: unclosed <sqlite3.Connection object at 0x7f8b1c>
```
**Context**: Running tests for gasket API endpoints
**Root Cause**: Database session not properly closed after exception in endpoint handler
**Solution**:
1. Added try-finally block to ensure session.close()
2. Updated dependency injection in api/deps.py to use context manager
3. Code:
   ```python
   @contextmanager
   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()
   ```
**Prevention**:
- Always use context managers for database sessions
- Use FastAPI's Depends() with context manager functions
- Add pytest fixture that checks for unclosed resources
**Related**: None
**Files Changed**:
- `backend/api/deps.py` - Updated get_db() to use context manager

---

#### [ERR-002] 2025-10-29 - Example: Curvature String Parsing Fails
**Error Message**:
```
ValueError: invalid literal for Fraction: '1/0'
  File "backend/schemas/gasket.py", line 12, in validate_curvatures
```
**Context**: POST /api/gaskets with curvatures=["1", "1", "1/0"]
**Root Cause**: User provided "1/0" which creates ZeroDivisionError when parsing to Fraction
**Solution**:
1. Added explicit ZeroDivisionError catch in validator
2. Return 400 Bad Request with clear message: "Curvature cannot have zero denominator"
3. Added test case for this edge case
**Prevention**:
- Always catch ZeroDivisionError when parsing fractions
- Add validation tests for boundary cases
- Document valid curvature ranges in API docs
**Related**: None
**Files Changed**:
- `backend/schemas/gasket.py` - Updated validator to catch ZeroDivisionError
- `backend/tests/test_api/test_gaskets.py` - Added test_invalid_curvature_zero_denominator()

---

### Frontend Errors

#### [ERR-003] 2025-10-29 - Example: React Hook Dependency Warning
**Error Message**:
```
React Hook useEffect has a missing dependency: 'fetchGasket'.
Either include it or remove the dependency array.
```
**Context**: GasketCanvas component, useEffect for loading gasket data
**Root Cause**: fetchGasket function reference changes on every render, causing useEffect to run repeatedly
**Solution**:
1. Wrapped fetchGasket in useCallback hook
2. Code:
   ```javascript
   const fetchGasket = useCallback(async () => {
     const data = await gasketService.getById(gasketId);
     setCircles(data.circles);
   }, [gasketId]);
   ```
**Prevention**:
- Use useCallback for functions used in useEffect dependencies
- Use ESLint react-hooks/exhaustive-deps rule
- Consider using custom hooks for data fetching
**Related**: None
**Files Changed**:
- `frontend/src/components/GasketCanvas/GasketCanvas.jsx` - Added useCallback

---

### Database Errors

#### [ERR-015] 2026-06-13 - "database is locked" 500s during viewport deepening
**Error Message**:
```
(browser) [deepen] viewport refinement failed: Error: ensure-resolution failed: 500
(network) POST /api/gaskets -> 500 Internal Server Error (repeated, ~6-27ms each)
(backend) sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked
          -> caught at api/endpoints/gaskets.py -> {"error_code": "GENERATION_ERROR"}
```
**Context**: Zooming a freshly generated gasket. Each viewport settle fires the
`ensure-resolution` POST `/api/gaskets` (App.tsx), which runs
`create_or_get_gasket` (incremental `_expand` + access-tracking commit). This
races the post-generation WebSocket persist: the `_produce` worker thread calls
`persist_walk_records`, which opens its OWN `SessionLocal()` and does one large
`commit()` of the whole packing.
**Root Cause**: Two connections write the same SQLite file with **zero
concurrency configuration**. The engine set only `check_same_thread=False`
(`db/base.py`) — no `journal_mode=WAL`, no `busy_timeout`. Default SQLite uses a
rollback journal with `busy_timeout=0`, so the moment a second writer wants the
write lock it fails **immediately** with `database is locked` instead of
waiting. The worker's bulk commit holds the lock long enough that concurrent
ensure-resolution POSTs reliably collide. (FastAPI runs sync endpoints in a
threadpool, so overlapping HTTP writes can collide too; the worker just widens
the window.) Reproduced at the `sqlite3` level: default config → instant
`database is locked`; `WAL` + `busy_timeout=5000` → the competing writer waits
~433ms and succeeds.
**Solution**:
1. Per-connection PRAGMAs via `event.listens_for(engine, "connect")` in
   `db/base.py`: `journal_mode=WAL` (readers no longer block the single
   writer), `busy_timeout=5000` (a competing writer waits for the lock instead
   of erroring), `synchronous=NORMAL` (safe, faster WAL companion). SQLite-only.
2. Bounded retry backstop (`db/concurrency.py`): `commit_with_retry` (rolls
   back, re-stages via a callback, retries) and `run_with_retry` (retries a
   self-contained unit). Applied to every write path in `gasket_service.py`;
   `persist_walk_records` retries on a fresh session and stays best-effort.
3. Ignore WAL sidecars (`*.db-wal` / `*.db-shm` / `*.db-journal`).
**Prevention**:
- Any SQLite app with a background writer (worker thread / threadpool) MUST set
  WAL + a non-zero `busy_timeout` at connect time — the defaults fail fast.
- Keep retry **re-stageable**: a rollback discards pending state, so the
  retry callback must rebuild ALL mutations from scratch; keep pure computation
  (the generation walk) outside it so retries never re-run it.
**Related**: ISSUES.md #1 (build response before commit — preserved); ERR-014
(WS worker-thread generation).
**Files Changed**:
- `backend/db/base.py` - connect-time PRAGMA listener (WAL + busy_timeout)
- `backend/db/concurrency.py` - new: `commit_with_retry`, `run_with_retry`
- `backend/services/gasket_service.py` - retry on all write paths
- `backend/tests/test_db_concurrency.py` - new: PRAGMA + helper + integration tests
- `.gitignore` - WAL sidecar files

---

#### [ERR-004] 2025-10-29 - Example: Migration Fails - Column Already Exists
**Error Message**:
```
sqlite3.OperationalError: duplicate column name: curvature_num
```
**Context**: Running Alembic migration to add curvature storage
**Root Cause**: Migration was run twice accidentally, attempted to add column that already exists
**Solution**:
1. Rolled back migration: `alembic downgrade -1`
2. Verified database schema: `sqlite3 gasket.db ".schema circles"`
3. Re-ran migration: `alembic upgrade head`
4. Added migration idempotency check
**Prevention**:
- Always check alembic history before running migrations: `alembic current`
- Use `if not exists` clauses in migrations when possible
- Keep migrations idempotent
- Document migration state in HISTORY.md
**Related**: None
**Files Changed**:
- `backend/alembic/versions/xxx_add_curvature.py` - Added IF NOT EXISTS

---

### Test Errors

#### [ERR-005] 2025-10-29 - Example: Test Fails - Float Comparison
**Error Message**:
```
AssertionError: assert 6.464101615137754 == 6.464
```
**Context**: test_descartes.py, testing identical curvatures (1, 1, 1)
**Root Cause**: Comparing float approximation of exact Fraction result with hardcoded float using ==
**Solution**:
1. Changed assertion to use approximate comparison:
   ```python
   assert abs(float(k4_plus) - 6.464) < 0.001
   ```
2. Added comment explaining why approximation is needed (Fraction → float conversion)
**Prevention**:
- NEVER use == for floating-point comparisons
- Always use abs(a - b) < tolerance
- Consider using pytest.approx() helper
- Document expected precision in test docstring
**Related**: None
**Files Changed**:
- `backend/tests/test_descartes.py` - Updated assertion

---

### Build/Configuration Errors

#### [ERR-006] 2025-10-29 - Example: Vite Build Fails - Out of Memory
**Error Message**:
```
FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory
```
**Context**: Running `npm run build` for production frontend build
**Root Cause**: Default Node.js heap size (1.4GB) insufficient for large React app with MUI
**Solution**:
1. Increased Node heap size in build script:
   ```json
   "build": "NODE_OPTIONS='--max-old-space-size=4096' vite build"
   ```
2. Verified build succeeds with 4GB heap
**Prevention**:
- Set NODE_OPTIONS in package.json build scripts
- Monitor bundle size (use `vite build --analyze`)
- Consider code splitting for very large apps
**Related**: None
**Files Changed**:
- `frontend/package.json` - Updated build script

---

#### [ERR-007] 2026-06-11 - migrations/__init__.py SyntaxError: module name starts with digit
**Error Message**:
```
invalid-syntax: Expected `import`, found float (ruff, migrations/__init__.py:17)
SyntaxError: invalid decimal literal  (on any `import migrations`)
```
**Context**: Found by the first `ruff check` run in Milestone 0. The package
init contained `from migrations.001_add_exact_columns import (...)`.
**Root Cause**: Python module names must be valid identifiers; `001_...`
starts with a digit, so the `from ... import` statement is a syntax error.
Any `import migrations` would have crashed — the package was never imported,
which is why this shipped unnoticed.
**Solution**: Removed the import and `__all__` from `migrations/__init__.py`;
documented that numbered migration modules must be run as scripts or loaded
via `importlib.util.spec_from_file_location`.
**Prevention**: Lint in CI (ruff now runs in `.github/workflows/ci.yml`);
avoid digit-leading module names for importable code.
**Related**: ERR-004 (same migration file, different issue)
**Files Changed**:
- `backend/migrations/__init__.py` - Removed syntactically invalid import

---

#### [ERR-008] 2026-06-11 - AttributeError: 'Zero' object has no attribute 'sqrt'
**Error Message**:
```
AttributeError: 'Zero' object has no attribute 'sqrt'
  File "backend/core/engine/seeds.py", in _rational_sqrt
    num_root = sp.Integer(frac.numerator).sqrt()
```
**Context**: New engine seed placement (`seed_from_quadruple`) computing the
exact square root of a rational y² that happened to be 0 (collinear centers,
e.g. the (-1, 2, 2, 3) quadruple where the third circle lies on the x-axis).
**Root Cause**: `sympy.Integer.sqrt()` is not a stable API across values —
`sp.Integer(0)` is the `Zero` singleton, which doesn't implement `.sqrt`.
**Solution**: Detect perfect squares with `math.isqrt` on numerator and
denominator; fall back to `sp.sqrt(sp.Rational(...))` only for irrational
results.
**Prevention**: Use `math.isqrt` for integer square-root checks; treat SymPy
singleton classes (Zero, One) as lacking the full Integer surface.
**Related**: None
**Files Changed**:
- `backend/core/engine/seeds.py` - `_rational_sqrt` uses `math.isqrt`

---

#### [ERR-009] 2026-06-11 - API requests with irrational seeds take minutes despite fast engine
**Error Message**:
```
(no exception — pytest tests/test_api_gaskets.py ran 10+ minutes;
cProfile: 12.6s for 56 circles, 97% under sympy/simplify/simplify.py:435)
```
**Context**: After switching the service layer to core/engine, API tests with
irrational seeds (e.g. curvatures (1,2,2)) were still extremely slow even
though the engine walk itself took 0.1s.
**Root Cause**: The legacy `CircleData.to_dict`/`to_database_dict` route every
scalar through `exact_math` helpers (`to_numerator_denominator`,
`format_exact`, `smart_divide`, `is_sympy_rational`) that each call
`sympy.simplify()` — ~0.23s per circle, multiplied over hundreds of circles
per request and dozens of tests.
**Solution**: Added `EngineCircleData` in `core/engine_adapter.py` overriding
`radius`/`to_dict`/`to_database_dict` with simplify-free serialization
(engine output is already in normal form; SymPy scalars need a single
`float()` evalf for the lossy INTEGER columns and plain `str()` for the
tagged TEXT columns). (1,2,2) at depth 5: 488 circles incl. serialization in
1.5s; rational seeds 0.01s.
**Prevention**: Never call `sympy.simplify` per-value in serialization paths;
keep normal-form guarantees in the producer. Schema v2 (Milestone 2) removes
this serialization layer entirely.
**Related**: ERR-008; ISSUES.md Issue #5
**Files Changed**:
- `backend/core/engine_adapter.py` - EngineCircleData fast serialization

---

#### [ERR-010] 2026-06-11 - Seed construction hangs on rational triples with irrational completion
**Error Message**:
```
(no exception — seed_from_triple(3/2, 5/3, 7/4) ran > 20s without returning;
pytest test_create_gasket_fraction_curvatures hung the API suite)
```
**Context**: Engine seed placement for curvature triples whose Descartes
completion is irrational (e.g. (3/2, 5/3, 7/4) → k₄ = 59/12 − √1158/6).
**Root Cause**: `sympy.nsimplify` was used as the canonicalizer in
`seeds._norm` / `InversiveCircle.from_curvature_center`. nsimplify performs
*constant recognition* (searching for closed forms), which is effectively
unbounded on nested radical quotients like the tangency-distance expressions
1/(a − b√c) that arise during placement.
**Solution**: Replaced `nsimplify` with `radsimp` (rationalize denominators)
for coordinate normalization and `simplify` where a boolean decision is
needed. The hanging seed now constructs in 0.5s and verifies exactly.
**Prevention**: Never use `nsimplify` for canonicalization — it is a
constant-recognition search, not a simplifier. Use `radsimp`/`cancel`/
`simplify` with known cost profiles; keep all SymPy canonicalization out of
per-circle hot paths (seed-time only).
**Related**: ERR-009
**Files Changed**:
- `backend/core/engine/seeds.py`, `backend/core/engine/inversive.py`,
  `backend/core/engine/metrics.py` - nsimplify → radsimp/simplify

---

### WebSocket Errors

#### [ERR-011] 2026-06-11 - Frontend never connects: StrictMode mount cycle wedges WebSocketService
**Error Message**:
```
(browser console) WebSocket connection to 'ws://.../ws/gasket/generate'
failed: WebSocket is closed before the connection is established.
(app state) 'Failed to connect to server'; no activity on the backend.
```
**Context**: Loading the frontend page in development. main.tsx wraps the app
in <StrictMode>, which in dev runs every effect as mount → cleanup → mount.
App.tsx connects the WebSocket in a mount effect and disconnects in cleanup.
**Root Cause**: Two service bugs compounding:
1. `disconnect()` closed the socket while it was still CONNECTING (browsers
   then log the "closed before the connection is established" error) but did
   NOT reset the `isConnecting` flag.
2. The second mount's `connect()` saw `isConnecting === true` and rejected
   with 'Connection already in progress' — so the app permanently showed
   disconnected and no request ever reached the backend.
**Solution**: Made `connect()` idempotent — concurrent callers share the
in-flight promise instead of rejecting; `onclose` rejects pending connect
attempts cleanly; `disconnect()` fully resets state so a fresh `connect()`
succeeds. Regression-tested ('survives the React StrictMode
mount/unmount/mount cycle') and verified live through the Vite proxy with an
abort-then-reconnect cycle.
**Prevention**: Any resource acquired in a React mount effect WILL go through
mount/cleanup/mount in dev StrictMode — connection managers must treat
connect/disconnect/connect as a normal sequence, not an error. Cover the
cycle in unit tests.
**Related**: ISSUES.md Issue #4; ERR-012
**Files Changed**:
- `frontend/src/services/websocketService.ts` - idempotent connect, full reset
- `frontend/src/services/websocketService.test.ts` - rewritten suite (19 tests)

---

#### [ERR-012] 2026-06-12 - dev:backend never starts when backend/venv is missing
**Error Message**:
```
sh: 1: .: venv/bin/activate: not found
[0] npm run dev:backend exited with code 127
(then: WebSocket/API errors in the browser, no backend terminal output)
```
**Context**: Running `npm run dev` (or scripts/dev.sh) on a checkout without
`backend/venv` (e.g. dependencies installed system-wide or setup.sh not run).
**Root Cause**: The root package.json hard-required the venv:
`cd backend && . venv/bin/activate && uvicorn ...` — if activation fails the
backend silently never starts, while the frontend comes up normally. The
browser then shows WebSocket errors with *no backend activity*, which looks
like a connection bug rather than a missing process.
**Solution**: dev:backend now activates the venv only if present, falls back
to the system Python environment, and fails loudly with an actionable message
if uvicorn is missing.
**Prevention**: Dev orchestration scripts should degrade gracefully and print
actionable errors; when debugging "no backend activity", first verify the
backend process actually started (curl /health).
**Related**: ERR-011
**Files Changed**:
- `package.json` - resilient dev:backend script

---

#### [ERR-013] 2026-06-12 - "Failed to parse message: Maximum update depth exceeded" under streaming load
**Error Message**:
```
Error: Failed to parse message: Error: Maximum update depth exceeded.
This can happen when a component repeatedly calls setState inside
componentWillUpdate or componentDidUpdate. ...
(stack: setState <- addCircles <- onProgress <- handleMessage <- onmessage)
```
**Context**: Generating a depth-10 gasket; thousands of 10-circle progress
messages flooded the frontend.
**Root Cause**: Two independent bugs:
1. `websocketService.handleMessage` wrapped JSON.parse AND callback dispatch
   in one try/catch, so the React exception thrown inside `onProgress` was
   misreported as a protocol parse failure.
2. Every progress message ran `addCircles` (full array re-clone, O(n²)) plus
   two more store setStates, and every new circles array identity re-fired
   two setState-in-effects in GasketCanvas (`setMaxGeneration`, autoFit →
   `setTransform`). Under message flood, React 19 hit its nested-update
   limit and threw.
**Solution**:
- Separate parse and dispatch error handling; callback exceptions report as
  "Error handling '<type>' message" with the real stack on the console.
- Buffer incoming circles in refs and flush to the store at most once per
  animation frame (App.tsx); progress/generation state updates ride the
  same flush.
- `maxGeneration` computed with useMemo (no state), auto-fit keyed on the
  circle COUNT, Stage onDragEnd added (also clears the Konva warning).
- Server side: batch size 10 → 500 and the 10ms-per-batch sleep removed.
**Prevention**: Never apply per-message store updates from a high-rate
stream — coalesce on animation frames; never setState in an effect keyed on
array identity that changes per message; keep parse and dispatch error
handling separate so error sources stay attributable.
**Related**: ERR-011, ERR-014
**Files Changed**:
- `frontend/src/services/websocketService.ts`, `frontend/src/App.tsx`,
  `frontend/src/components/GasketCanvas/GasketCanvas.tsx`,
  `backend/api/endpoints/websocket.py`

---

#### [ERR-014] 2026-06-12 - Depth-10 irrational generation pegged one CPU core for tens of minutes
**Error Message**:
```
(no exception — POST/WS generation of (1,1,1) at depth 10 saturated one
core "for a very long time"; profile showed float(sympy_expr) evalf calls
~5x per circle x 118,100 circles)
```
**Context**: User generated (1,1,1) at depth 10 from the UI.
**Root Cause**: Three compounding costs: (a) serialization called
`float(expr)` (a SymPy evalf) per scalar per circle; (b) the WS endpoint
slept 10ms per 10-circle batch (≥118s of pure sleep at depth 10); (c)
generation ran synchronously on the event loop, blocking the backend.
**Solution** (Milestone 2):
- The walk now maintains incremental float mirrors (the reflection is the
  same linear op in doubles) — zero evalf per circle.
- `WalkBudget.min_radius` resolution pruning makes deep walks
  output-sensitive; the frontend derives min_radius from the canvas size,
  so depth 10 streams ~6.6k circles in ~5s instead of 118k in tens of
  minutes.
- Generation runs in a worker thread feeding an asyncio queue with
  disconnect cancellation; /health answers in ~26ms mid-stream.
**Prevention**: keep SymPy out of per-circle paths (mirrors at generation
time); budget output by resolution, not depth alone; never run CPU-bound
generation on the event loop.
**Related**: ERR-009, ERR-013
**Files Changed**:
- `backend/core/engine/walk.py`, `backend/api/endpoints/websocket.py`,
  `backend/services/serializers.py`, `frontend/src/App.tsx`

---

### Performance Issues

*No issues logged yet*

---

## Search Index

### Common Error Keywords
- "import" → ERR-001
- "fraction" → ERR-002, ERR-005
- "react hook" → ERR-003
- "migration" → ERR-004
- "float comparison" → ERR-005
- "out of memory" → ERR-006
- "database is locked" / "WAL" / "busy_timeout" / "concurrency" → ERR-015

### By File
- `backend/core/descartes.py` → ERR-002, ERR-005
- `backend/api/deps.py` → ERR-001
- `frontend/src/components/GasketCanvas/` → ERR-003
- `backend/alembic/` → ERR-004

### By Error Type
- **Import Errors**: ERR-001
- **Validation Errors**: ERR-002
- **React Warnings**: ERR-003
- **Database Errors**: ERR-004
- **Test Failures**: ERR-005
- **Build Errors**: ERR-006

---

## Statistics

**Total Errors Logged**: 6 (examples)
**Backend Errors**: 2
**Frontend Errors**: 1
**Database Errors**: 1
**Test Errors**: 1
**Build Errors**: 1
**Last Updated**: 2025-10-29 15:00

---

## Tips for Effective Debugging

1. **Always search first**: 90% of errors have been seen before
2. **Copy exact error text**: More specific = better search results
3. **Search by file name**: If error in `descartes.py`, search for that
4. **Look for patterns**: Similar errors often have similar solutions
5. **Update after solving**: Help your future self (and others)
6. **Be specific**: "Changed X to Y because Z" is better than "Fixed it"
7. **Include code snippets**: Show the actual fix, not just description
8. **Link related errors**: Use ERR-XXX references for similar issues
