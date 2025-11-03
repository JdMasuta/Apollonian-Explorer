Here are the entries for the two concerns identified in the previous verification step, formatted for your `ISSUES.md` document.

---

## 🛠️ Issue Tracker

This document tracks identified bugs, potential performance bottlenecks, and required investigations.

---

### Issue #1: Extraneous Database Query for Gasket Retrieval Post-Update

**Status:** Needs Investigation
**Priority:** Medium (Potential Performance Bottleneck)

**Description**

During a successful API interaction involving the `gaskets` resource (specifically triggered by a `POST /api/gaskets`), the system executes two distinct, sequential database transactions. The second transaction appears to be a redundant read operation immediately following a successful write (update) operation.

This suggests that the application may be retrieving data that is already available in the ORM's session or memory, leading to **unnecessary database round trips** and potential performance impact, especially under high load.

**Affected Logs / Behavior**

The issue is visible in the log snippet below, focusing on the actions taken around 14:22:48:

- **Transaction 1 (Update & Commit):**
  - `14:22:48,966 INFO sqlalchemy.engine.Engine SELECT ... FROM gaskets WHERE gaskets.hash = ?` (Read)
  - `14:22:48,973 INFO sqlalchemy.engine.Engine SELECT ... FROM circles WHERE circles.gasket_id IN (?)` (Read)
  - `14:22:48,983 INFO sqlalchemy.engine.Engine UPDATE gaskets SET last_accessed_at=?, access_count=? WHERE gaskets.id = ?` (**Write**)
  - `14:22:48,984 INFO sqlalchemy.engine.Engine COMMIT` (Saves data)
- **Transaction 2 (Immediate Re-fetch):**
  - `14:22:48,996 INFO sqlalchemy.engine.Engine BEGIN` (implicit)
  - `14:22:48,997 INFO sqlalchemy.engine.Engine SELECT ... FROM gaskets WHERE gaskets.id = ?` (**Redundant Read**)
  - `14:22:48,999 INFO sqlalchemy.engine.Engine SELECT ... FROM circles WHERE ? = circles.gasket_id` (**Redundant Read**)
  - `14:22:49,016 INFO sqlalchemy.engine.Engine ROLLBACK` (Ends transaction)

**Investigation Required**

- **Determine Necessity:** Is the second `SELECT` sequence (Transaction 2) genuinely required for serialization, logging, or to refresh the ORM object?
- **Code Review:** Review the code path for `POST /api/gaskets` to see if the object created/updated in the first transaction can be reused for the final API response object, eliminating the need for the second database query.
- **ORM Optimization:** If using an ORM (like SQLAlchemy), check if settings can be adjusted to prevent an automatic re-fetch after a committed update.

---

### Issue #2: Flawed Initial Circle Placement in Gasket Generator

**Status:** Needs Fix
**Priority:** High (Core Mathematical Correctness)

**Description**

The Apollonian Gasket generation script relies on the initial three circles being **perfectly mutually tangent**. The function `_initialize_three_circles` (in `gasket_generator.py`) uses a simplified geometric approach (Law of Cosines) that involves **floating-point conversion** (`float()`) and approximation (`math.acos`, `Fraction.limit_denominator`).

This use of approximation for initial placement directly contradicts the module's goal of using **exact rational arithmetic** and causes the three starting circles to be only _approximately_ tangent. If the base circles are not perfectly tangent, all subsequent recursive calculations using the Descartes Theorem will be based on an incorrect premise, potentially leading to errors, misplaced circles, and numerical drift in the gasket structure.

**Affected Components**

- `gasket_generator.py`: `_initialize_three_circles` function.

**Required Action**

- **Refactor `_initialize_three_circles`** to compute the center of the third circle using **exact rational geometry** (e.g., solving the quadratic tangency constraints symbolically using the radii $r_1, r_2, r_3$) to ensure all three starting circles are perfectly tangent. This ensures the output centers remain `Fraction` objects derived purely from rational inputs.

---

### Issue #3: Incomplete Deduplication in Gasket Generation BFS

**Status:** Needs Fix
**Priority:** High (Core Algorithm Correctness)

**Description**

The recursive Breadth-First Search (BFS) algorithm in `generate_apollonian_gasket` correctly uses a triplet of tangent circles $(C_1, C_2, C_3)$ to compute two new circles via `descartes_solve`.

The Descartes Theorem mandates that one of the two solutions is the expected **new tangent circle**, and the other is one of the **three original parent circles** (the "opposite" circle $C_C$ that completed the quartet with $C_1, C_2, C_3$ in a previous step).

The current implementation only checks for duplicates against the global `circle_hashes` set but **fails to explicitly check and discard the parent circle solution** that is guaranteed to be returned by `descartes_solve`. Relying solely on hashing may not be robust due to potential small numerical approximation errors introduced by the square root operation (`descartes_solve`).

**Affected Components**

- `gasket_generator.py`: `generate_apollonian_gasket` (inside the BFS loop).

**Required Action**

- **Implement Explicit Parent Check:** Before checking the hash, the code must check if the newly calculated circle's (curvature, center) tuple matches that of any of the three parent circles $(C_1, C_2, C_3)$. If it matches, the solution should be explicitly discarded using `continue`. This is necessary for the BFS to correctly propagate the generation forward by identifying only the _true_ new circle.

---

### Issue #4: Frontend WebSocket Service Test Timing Issues

**Status:** Needs Fix (Non-Critical)
**Priority:** Low (Tests, Service Code Works Correctly)

**Description**

The frontend WebSocket service tests (`frontend/src/services/websocketService.test.ts`) have timing issues with vitest fake timers and the MockWebSocket implementation. Currently 11 out of 17 tests fail due to macrotask/microtask timing incompatibility, despite the service code itself working correctly.

**Evidence Service Works:**
- Backend WebSocket tests: 14/14 passing ✓
- Console logs show successful connections in all tests
- Manual browser testing works correctly
- The timing issue is **purely in the test mocking layer**, not the actual service code

**Root Cause**

The MockWebSocket class uses `setTimeout(..., 0)` to simulate async connection (macrotask), but vitest fake timers create a timing incompatibility:

1. Test calls `websocketService.connect()` → creates WebSocket with `setTimeout`
2. Test calls `vi.advanceTimersByTime(0)` → triggers setTimeout callback
3. setTimeout callback sets `readyState = OPEN` and calls `onopen`
4. However, promise microtasks don't resolve until AFTER the test continues
5. Test assertions run before `readyState` updates, causing false failures

**Attempted Solutions (All Failed):**
- `vi.runAllTimersAsync()` - Hung indefinitely (infinite timer loop)
- `vi.advanceTimersByTime(0)` - Synchronous, doesn't wait for microtasks
- `await Promise.resolve()` - Flushes some microtasks but not enough
- Combination of above - Still fails due to macrotask/microtask ordering

**Affected Components**
- `frontend/src/services/websocketService.test.ts` - Test file with 11/17 failures
- MockWebSocket class implementation (uses `setTimeout` for async simulation)

**Recommended Future Fixes** (Choose One)

**Option 1: Refactor MockWebSocket** (Easiest, ~30 minutes)
- Replace `setTimeout(..., 0)` with `queueMicrotask()` in the MockWebSocket constructor
- This aligns the async timing with promise microtasks
- Should make all tests pass with existing fake timer infrastructure
- **Implementation:**
  ```typescript
  constructor(url: string) {
    this.url = url;
    queueMicrotask(() => {  // ← Change from setTimeout
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    });
  }
  ```

**Option 2: Use Proper WebSocket Mocking Library** (Medium effort, 1-2 hours)
- Use `mock-socket` library (https://www.npmjs.com/package/mock-socket)
- Provides production-quality WebSocket mocking
- Eliminates timing issues entirely
- More maintainable long-term
- **Installation:** `npm install --save-dev mock-socket`

**Option 3: Integration Tests Against Real WebSocket** (Most robust, 2-3 hours)
- Spin up actual FastAPI server with WebSocket endpoint in test
- Test against real WebSocket connection (no mocking)
- Most accurate testing but slower test execution
- Requires test server lifecycle management

**Option 4: Accept Current Limitations** (No effort, viable for MVP)
- Service code is proven functional via backend tests
- Manual testing validates end-to-end behavior
- Test infrastructure improvements are documented
- Defer comprehensive test fix to post-MVP

**Recommendation**

For MVP: **Option 4** (accept limitations) - Service is proven working

Post-MVP: **Option 1** (refactor MockWebSocket) - Quick fix with high impact

**Reference**
- Commit: `cd33d6f` - "test(frontend): improve WebSocket tests with fake timers (partial fix)"
- Backend tests passing: `backend/tests/test_websocket.py` (14/14 ✓)
- Vitest fake timers documentation: https://vitest.dev/guide/mocking.html#timers
