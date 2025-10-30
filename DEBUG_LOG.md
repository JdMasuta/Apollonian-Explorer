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

### WebSocket Errors

*No errors logged yet*

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
