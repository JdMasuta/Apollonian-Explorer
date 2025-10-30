# Claude Implementation Guide for Apollonian Gasket Project

**Purpose**: This document provides instructions for Claude (AI assistant) during the implementation phase of the Apollonian Gasket Visualization Tool. It ensures consistent, high-quality code generation with minimal hallucination and maximum user collaboration.

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Required Reading](#required-reading)
3. [Implementation Workflow](#implementation-workflow)
4. [Anti-Hallucination Techniques](#anti-hallucination-techniques)
5. [Testing Requirements](#testing-requirements)
6. [Decision-Making Protocol](#decision-making-protocol)
7. [Code Quality Standards](#code-quality-standards)
8. [Phase-by-Phase Instructions](#phase-by-phase-instructions)
9. [Documentation Maintenance](#documentation-maintenance)

---

## Core Principles

### 1. Small, Incremental Changes
- **NEVER** implement more than ONE component/file/feature at a time
- Complete each unit of work before moving to the next
- Always ask "Is this too much to do in one step?" If yes, break it down further

### 2. User Collaboration First
- **ALWAYS** ask user for approval on high-level design decisions
- Present options with trade-offs, not just recommendations
- Confirm understanding before writing code

### 3. Evidence-Based Implementation
- **ONLY** implement features specified in project documents
- **NEVER** add features "that might be useful" without asking
- Reference specific document sections when making decisions

### 4. Test-Driven Approach
- Write or update tests for EVERY new component
- Run tests IMMEDIATELY after implementation
- Fix failing tests before proceeding

---

## Required Reading

Before starting ANY implementation task, you MUST be familiar with these documents:

### Essential Documents (Read First)
1. **`DESIGN_SPEC.md`** - Complete technical specification
2. **`API_USAGE_GUIDE.md`** - API contracts and data formats
3. **`IMPLEMENTATION_PLAN.md`** - Phased development roadmap

### Supporting Documents (Reference as Needed)
4. **`README.md`** - Project overview
5. **`ROADMAP.md`** - Timeline and milestones
6. **`CHECKLIST.md`** - Verification criteria

### Maintenance Documents (Update Regularly)
7. **`HISTORY.md`** - Implementation history log (update after EVERY task)
8. **`DEBUG_LOG.md`** - Error solutions database (update after EVERY error fix)

### When to Reference Each Document

| Document | Use When... |
|----------|-------------|
| `DESIGN_SPEC.md` | Understanding system architecture, database schema, algorithms |
| `API_USAGE_GUIDE.md` | Implementing API endpoints, data serialization, error handling |
| `IMPLEMENTATION_PLAN.md` | Planning what to work on next, understanding dependencies |
| `CHECKLIST.md` | Verifying completion of a phase or feature |
| `HISTORY.md` | Reviewing what was done, tracking progress, understanding past decisions |
| `DEBUG_LOG.md` | **BEFORE debugging any error** - search for similar issues and solutions |

---

## Implementation Workflow

### Standard Workflow for Each Task

```
1. READ relevant documentation sections
   ↓
2. ASK user to confirm task scope and approach
   ↓
3. PLAN implementation (outline steps in response)
   ↓
4. IMPLEMENT one small piece at a time
   ↓
5. WRITE/UPDATE tests
   ↓
6. RUN tests and verify
   ↓
7. COMMIT with descriptive message
   ↓
8. UPDATE HISTORY.md with what was done
   ↓
9. ASK user before moving to next task
```

### Error Handling Workflow

```
When ANY error occurs:

1. SEARCH DEBUG_LOG.md for similar errors (using grep)
   ↓
2. If found: Try the documented solution
   ↓
3. If not found OR solution doesn't work: Debug the error
   ↓
4. FIX the error
   ↓
5. UPDATE DEBUG_LOG.md with error and solution
   ↓
6. Continue with standard workflow
```

### Example: Implementing Descartes Circle Theorem

**GOOD Workflow**:
```
Claude: "I'll implement the Descartes Circle Theorem according to
section 8.1 of DESIGN_SPEC.md. The function will:
1. Accept three Fraction curvatures as input
2. Return two Fraction curvatures (+ and - solutions)
3. Use the formula: k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)

Should I proceed with this approach?"

User: "Yes"

Claude: [Implements descartes_curvature() function]

Claude: "Function implemented. Now I'll write unit tests for:
- Known configuration (-1, 2, 2, 3) → (6, 14/15)
- Edge case: three identical curvatures
- Zero curvature handling

Should I proceed with these tests?"

User: "Yes"

Claude: [Writes tests, runs them, verifies they pass]

Claude: "Tests passing. Ready to commit. Commit message:
'feat(core): implement Descartes Circle Theorem for curvatures'

Shall I commit and move to the next function (center calculation)?"
```

**BAD Workflow** (DO NOT DO THIS):
```
Claude: "I'll implement the entire gasket generation system now."
[Implements 5 files, 800 lines of code, no tests, no user checkpoints]
Claude: "Done! Here's the complete system."
```

---

## Anti-Hallucination Techniques

### Technique 1: Cite Your Sources

**ALWAYS** reference the specific document and section when implementing.

**Example**:
```python
def descartes_curvature(k1: Fraction, k2: Fraction, k3: Fraction) -> Tuple[Fraction, Fraction]:
    """
    Calculate the curvature of the fourth circle tangent to three circles.

    Implements Descartes Circle Theorem as specified in:
    DESIGN_SPEC.md section 8.1

    Formula: k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)

    Args:
        k1, k2, k3: Curvatures of three mutually tangent circles

    Returns:
        Tuple of (k4_plus, k4_minus) solutions
    """
```

### Technique 2: Verify Against Specifications

Before writing code, state:
1. What document section you're implementing
2. What the expected behavior is
3. Any assumptions you're making

**Example**:
```
"According to DESIGN_SPEC.md section 4.2, the circles table stores
curvature as two integer columns (curvature_num, curvature_denom).
I'll create the Circle model with these fields using SQLAlchemy.

Assumption: We'll use a @hybrid_property to provide a convenient
'curvature' attribute that returns a Fraction object.

Is this approach correct?"
```

### Technique 3: Admit Uncertainty

**NEVER** guess or make up APIs, libraries, or functionality.

**Instead of**:
```python
# Guessing that Numba has a @fraction_jit decorator
@fraction_jit
def fast_calculation(x):
    ...
```

**Do this**:
```
"I need to implement JIT compilation for the Descartes theorem function.
DESIGN_SPEC.md mentions using Numba, but I'm unsure if Numba supports
fractions.Fraction directly. Should I:

A) Use Numba with float conversion (loses exact arithmetic)
B) Keep Fraction-based calculation without JIT for now
C) Research Numba + Fraction compatibility first

What's your preference?"
```

### Technique 4: Use Type Hints and Validation

Add type hints and runtime validation to catch errors early.

**Example**:
```python
from typing import List
from fractions import Fraction
from pydantic import BaseModel, validator

class GasketCreate(BaseModel):
    curvatures: List[str]
    max_depth: int

    @validator('curvatures')
    def validate_curvatures(cls, v):
        if len(v) not in [3, 4]:
            raise ValueError("Must provide 3 or 4 curvatures")

        # Try to parse each as Fraction
        try:
            parsed = [Fraction(c) for c in v]
        except (ValueError, ZeroDivisionError) as e:
            raise ValueError(f"Invalid curvature format: {e}")

        # Check for zero curvatures (infinite radius circles require special handling)
        if any(f == 0 for f in parsed):
            raise ValueError("Zero curvatures not yet supported")

        return v
```

### Technique 5: Reference Existing Code Patterns

When implementing similar functionality, reference existing patterns.

**Example**:
```
"I'm implementing the sequence detection endpoint. I'll follow the same
pattern as the gasket creation endpoint (api/endpoints/gaskets.py:15-45):
1. Pydantic schema for request validation
2. Dependency injection for DB session
3. Try/except with specific error types
4. Return standardized response format

Is this consistent with the project style?"
```

---

## Testing Requirements

### Test Every Component

For **EVERY** piece of code you write, you MUST write tests.

### Testing Checklist

- [ ] **Unit tests** for pure functions and algorithms
- [ ] **Integration tests** for API endpoints
- [ ] **Edge case tests** for boundary conditions
- [ ] **Error case tests** for exception handling

### Test File Naming Convention

```
backend/tests/
├── test_descartes.py          # Unit tests for core/descartes.py
├── test_gasket_generator.py   # Unit tests for core/gasket_generator.py
├── test_sequence_detector.py  # Unit tests for core/sequence_detector.py
└── test_api/
    ├── test_gaskets.py        # Integration tests for api/endpoints/gaskets.py
    └── test_sequences.py      # Integration tests for api/endpoints/sequences.py

frontend/tests/
├── stores/
│   ├── gasketStore.test.js    # Tests for stores/gasketStore.js
│   └── sequenceStore.test.js  # Tests for stores/sequenceStore.js
└── components/
    ├── GasketCanvas.test.jsx  # Tests for components/GasketCanvas/
    └── SequencePanel.test.jsx # Tests for components/SequencePanel/
```

### Test Template: Backend Unit Test

```python
# backend/tests/test_descartes.py
import pytest
from fractions import Fraction
from core.descartes import descartes_curvature

class TestDescartesCircleTheorem:
    """Tests for Descartes Circle Theorem implementation.

    Reference: DESIGN_SPEC.md section 8.1
    """

    def test_known_configuration(self):
        """Test with known Apollonian gasket configuration.

        Starting curvatures: -1, 2, 2, 3
        Expected results: 6 and 14/15
        """
        k1 = Fraction(-1)
        k2 = Fraction(2)
        k3 = Fraction(2)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        assert k4_plus == Fraction(6)
        assert k4_minus == Fraction(14, 15)

    def test_identical_curvatures(self):
        """Test with three identical curvatures (1, 1, 1)."""
        k1 = k2 = k3 = Fraction(1)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Expected: k4 = 3 ± 2√3 = 3 ± 3.464... ≈ 6.464 or -0.464
        # Since we use exact rational arithmetic, verify approximate values
        assert abs(float(k4_plus) - 6.464) < 0.01
        assert abs(float(k4_minus) + 0.464) < 0.01

    def test_negative_curvature(self):
        """Test with enclosing circle (negative curvature)."""
        k1 = Fraction(-1)  # Enclosing circle
        k2 = Fraction(1)
        k3 = Fraction(1)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Both solutions should be positive (internal circles)
        assert k4_plus > 0
        assert k4_minus > 0

    def test_large_curvatures(self):
        """Test numerical stability with large curvatures."""
        k1 = Fraction(1000)
        k2 = Fraction(1001)
        k3 = Fraction(1002)

        k4_plus, k4_minus = descartes_curvature(k1, k2, k3)

        # Should not raise overflow or precision errors
        assert isinstance(k4_plus, Fraction)
        assert isinstance(k4_minus, Fraction)
```

### Test Template: Backend Integration Test

```python
# backend/tests/test_api/test_gaskets.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
class TestGasketEndpoints:
    """Integration tests for gasket API endpoints.

    Reference: API_USAGE_GUIDE.md section "REST API Endpoints"
    """

    async def test_create_gasket_success(self):
        """Test successful gasket creation with valid curvatures."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/gaskets", json={
                "curvatures": ["1", "1", "1"],
                "max_depth": 5
            })

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "hash" in data
        assert data["initial_curvatures"] == ["1", "1", "1"]
        assert data["max_depth_cached"] == 5
        assert "circles" in data
        assert len(data["circles"]) > 0

    async def test_create_gasket_invalid_curvatures(self):
        """Test error handling for invalid curvature format."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/gaskets", json={
                "curvatures": ["invalid", "1", "1"],
                "max_depth": 5
            })

        assert response.status_code == 400
        data = response.json()

        assert "error_code" in data
        assert data["error_code"] == "INVALID_CURVATURES"

    async def test_get_gasket_not_found(self):
        """Test 404 response for non-existent gasket."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/gaskets/99999")

        assert response.status_code == 404
        data = response.json()

        assert data["error_code"] == "GASKET_NOT_FOUND"
```

### Test Template: Frontend Store Test

```javascript
// frontend/tests/stores/gasketStore.test.js
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useGasketStore from '../../src/stores/gasketStore';

describe('gasketStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useGasketStore());
    act(() => {
      result.current.clearGasket();
    });
  });

  it('should initialize with null gasket', () => {
    const { result } = renderHook(() => useGasketStore());

    expect(result.current.currentGasket).toBeNull();
    expect(result.current.circles).toEqual([]);
    expect(result.current.isGenerating).toBe(false);
  });

  it('should add circles to store', () => {
    const { result } = renderHook(() => useGasketStore());

    const newCircles = [
      { id: 1, curvature: '1', center: { x: '0', y: '0' }, radius: '1' },
      { id: 2, curvature: '1', center: { x: '2', y: '0' }, radius: '1' }
    ];

    act(() => {
      result.current.addCircles(newCircles);
    });

    expect(result.current.circles).toHaveLength(2);
    expect(result.current.circles[0].id).toBe(1);
  });

  it('should update progress during generation', () => {
    const { result } = renderHook(() => useGasketStore());

    act(() => {
      result.current.updateProgress(5, 10);
    });

    expect(result.current.progress).toBe(50);
  });
});
```

### Running Tests

**Backend**:
```bash
# Run all tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_descartes.py -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=html
```

**Frontend**:
```bash
# Run all tests
npm test

# Run specific test file
npm test gasketStore.test.js

# Run with coverage
npm test -- --coverage
```

### When to Write Tests

| Scenario | When to Test |
|----------|--------------|
| **New function/method** | Write test BEFORE or IMMEDIATELY AFTER implementation |
| **New API endpoint** | Write integration test AFTER endpoint works manually |
| **Bug fix** | Write test that FAILS, then fix code, then test PASSES |
| **Refactoring** | Run existing tests BEFORE and AFTER to ensure no regression |

---

## Decision-Making Protocol

### Always Ask About These Decisions

You MUST ask the user before:

1. **Adding new dependencies** (libraries, packages)
   ```
   "I need to parse SVG paths. Should I:
   A) Add 'svgpathtools' library (125KB)
   B) Implement manual parsing (more code, no dependency)
   C) Use built-in xml.etree

   What's your preference?"
   ```

2. **Changing data structures or schemas**
   ```
   "I'm implementing the circles table. The spec shows separate num/denom
   fields for rationals. However, I could also store as TEXT in format
   'num/denom'. TEXT format would be:
   + Easier to read in database queries
   + Simpler ORM mapping
   - Slightly slower for numerical comparisons

   Should I stick with the spec's two-integer approach?"
   ```

3. **Deviating from specifications**
   ```
   "DESIGN_SPEC.md section 9.1 specifies SHA-256 for gasket hashing.
   However, MD5 would be faster and sufficient for our use case (non-security).

   Should I:
   A) Use SHA-256 as specified (slower, overkill)
   B) Switch to MD5 (faster, ask user to update spec)
   C) Use a faster hash like xxHash

   What do you prefer?"
   ```

4. **Implementation approach for complex features**
   ```
   "I'm implementing the WebSocket streaming for gasket generation.
   Two approaches:

   A) Synchronous generation with periodic yields
      + Simple, easy to understand
      - Blocks FastAPI worker during generation

   B) Background task with queue
      + Non-blocking, better scalability
      - More complex, requires task management

   For single-user deployment, which approach should I use?"
   ```

5. **Optimization strategies**
   ```
   "The generation algorithm is slower than expected for depth 10.
   Profiling shows 80% time in square root calculations.

   Options:
   A) Cache sqrt results in a lookup table
   B) Use Numba JIT (but need to handle Fraction objects)
   C) Pre-compute common configurations

   Which optimization should I prioritize?"
   ```

### Questions You Can Decide Independently

These LOW-LEVEL decisions are okay to make without asking:

- Variable names (as long as they're descriptive)
- Code organization within a single file
- Helper function extraction for readability
- Comment wording
- Log message formatting
- Error message wording (as long as it's clear)

---

## Code Quality Standards

### Python Backend Standards

**Style**:
- Follow PEP 8
- Use Black formatter (line length: 100)
- Use isort for imports
- Type hints on all function signatures

**Example**:
```python
from fractions import Fraction
from typing import List, Tuple

def descartes_curvature(
    k1: Fraction, k2: Fraction, k3: Fraction
) -> Tuple[Fraction, Fraction]:
    """
    Calculate fourth circle curvature using Descartes Circle Theorem.

    Args:
        k1, k2, k3: Curvatures of three mutually tangent circles

    Returns:
        Tuple of (k4_plus, k4_minus) curvature solutions

    Raises:
        ValueError: If curvatures form invalid configuration
    """
    # Implementation...
```

**Docstrings**:
- Use Google-style docstrings
- Include Args, Returns, Raises sections
- Reference specification documents where applicable

**Error Handling**:
```python
# GOOD: Specific exceptions with context
try:
    curvature = Fraction(value)
except (ValueError, ZeroDivisionError) as e:
    raise ValueError(f"Invalid curvature '{value}': {e}")

# BAD: Generic exceptions
try:
    curvature = Fraction(value)
except Exception:
    raise Exception("Error")
```

### JavaScript/React Frontend Standards

**Style**:
- Follow Airbnb JavaScript Style Guide
- Use ESLint + Prettier
- Functional components with hooks (no class components)

**Example**:
```javascript
import React from 'react';
import PropTypes from 'prop-types';
import { Box, Typography } from '@mui/material';

/**
 * Displays details for a selected circle.
 *
 * @param {Object} props
 * @param {Object} props.circle - Circle object with curvature, center, radius
 * @param {Function} props.onParentClick - Callback when parent link clicked
 */
const CircleDetails = ({ circle, onParentClick }) => {
  if (!circle) {
    return (
      <Box p={2}>
        <Typography color="text.secondary">
          Select a circle to view details
        </Typography>
      </Box>
    );
  }

  return (
    <Box p={2}>
      <Typography variant="h6">Circle {circle.id}</Typography>
      <Typography>Curvature: {circle.curvature}</Typography>
      {/* More details... */}
    </Box>
  );
};

CircleDetails.propTypes = {
  circle: PropTypes.shape({
    id: PropTypes.number.isRequired,
    curvature: PropTypes.string.isRequired,
    center: PropTypes.shape({
      x: PropTypes.string.isRequired,
      y: PropTypes.string.isRequired
    }).isRequired,
    radius: PropTypes.string.isRequired
  }),
  onParentClick: PropTypes.func.isRequired
};

CircleDetails.defaultProps = {
  circle: null
};

export default CircleDetails;
```

**Component Structure**:
```
1. Imports (React, libraries, local)
2. Component definition
3. PropTypes
4. Default props (if needed)
5. Export
```

**Hooks**:
- Use custom hooks for reusable logic
- Keep components focused on rendering
- Extract complex state logic to Zustand stores

---

## Phase-by-Phase Instructions

Follow these phase-specific instructions from `IMPLEMENTATION_PLAN.md`.

### Phase 0: Project Setup

**Before starting**:
```
1. Confirm with user: "Ready to set up the monorepo structure?"
2. Show directory tree you'll create
3. Ask about any modifications to structure
```

**Checklist**:
- [ ] Create directory structure (backend/, frontend/, scripts/)
- [ ] Initialize Python project (pyproject.toml or requirements.txt)
- [ ] Initialize React project (npm, Vite)
- [ ] Set up .gitignore
- [ ] Create setup.sh script
- [ ] Test: Can run `npm run dev` to start both frontend and backend

**Testing Phase 0**:
```bash
# Should start both servers
npm run dev

# Backend should respond
curl http://localhost:8000/health

# Frontend should load
open http://localhost:5173
```

### Phase 1: Core Gasket Generation

**Order of implementation**:
```
1. descartes.py (curvature calculation only)
   → Write tests → Run tests

2. descartes.py (center calculation with complex numbers)
   → Write tests → Run tests

3. circle_math.py (helper utilities)
   → Write tests → Run tests

4. gasket_generator.py (basic recursive generation)
   → Write tests → Run tests

5. Database models (Gasket, Circle)
   → Test with pytest fixtures

6. API endpoint POST /api/gaskets
   → Integration test

7. API endpoint GET /api/gaskets/{id}
   → Integration test
```

**For EACH step, ask**:
```
"I've completed [X]. Tests are passing.
Should I commit this and move to [Y]?"
```

### Phase 2-9: Continue Pattern

For each phase:
1. Read phase description in `IMPLEMENTATION_PLAN.md`
2. Break into small tasks (5-7 tasks per phase)
3. For each task:
   - Ask user to confirm task
   - Implement
   - Test
   - Ask before committing
   - Ask before next task

---

## Handling Common Scenarios

### Scenario 1: User Requests Feature Not in Spec

```
User: "Can you add dark mode to the UI?"

Claude: "Dark mode isn't currently in the specification documents.
I can add it, but it would be outside the current scope.

Would you like me to:
A) Add dark mode now (will take ~1-2 hours)
B) Add it to a 'Future Enhancements' list for later
C) Skip it entirely

If A, should I update DESIGN_SPEC.md to document the feature first?"
```

### Scenario 2: Test Fails

```
Claude: "The test for descartes_curvature() with identical curvatures
is failing. Expected approximate value 6.464, got 6.928.

This might be because:
1. My test expectation is wrong (possible calculation error)
2. The implementation has a bug
3. Floating-point precision issue in the test

Let me verify the math manually...

[Shows calculation]

The implementation is correct. I'll update the test expectation.
Should I proceed?"
```

### Scenario 3: Unclear Specification

```
Claude: "I'm implementing the sequence detection caching (section 9.1).
The spec says 'hash of (gasket_hash + sequence_type + parameters)'.

For the 'parameters' part, if parameters = {"modulus": 24, "residue": 5},
should I:
A) Hash the JSON string: '{"modulus":24,"residue":5}'
B) Hash the sorted JSON to ensure consistency
C) Hash individual values concatenated: '24' + '5'

The spec doesn't specify. What's your preference?"
```

### Scenario 4: Performance Issue

```
Claude: "I've implemented the gasket generator. Tests pass, but
depth-10 generation takes 25 seconds (target: < 5s per DESIGN_SPEC.md).

Profiling shows:
- 60% time in Fraction operations
- 25% time in duplicate detection
- 15% time in database inserts

Should I:
A) Optimize now (might delay current phase)
B) Note the issue and optimize in Phase 7 (performance phase)
C) Ask for guidance on acceptable performance for MVP

What's your priority?"
```

---

## Documentation Maintenance

### CRITICAL: Always Update Documentation

Documentation is NOT optional. It's a core part of the implementation process. **ALWAYS** update HISTORY.md after completing any task, and **ALWAYS** update DEBUG_LOG.md after fixing any error.

---

### HISTORY.md: Implementation Log

#### When to Update

Update HISTORY.md **IMMEDIATELY** after:
- Completing any implementation task
- Writing a new function, class, or component
- Adding a feature
- Fixing a bug
- Writing tests
- Refactoring code
- Making any commit

**DO NOT** wait until end of session or batch multiple updates. Update after EACH task.

#### Required Format

```markdown
### [YYYY-MM-DD HH:MM] Phase X: Task Name
**What was done**: Detailed description of the implementation
**Specifics**: Technical details (algorithms used, design patterns, key decisions)
**Files changed**:
- `path/to/file1.py` - Description of changes
- `path/to/file2.js` - Description of changes
**Tests added**:
- `path/to/test_file.py` - What was tested
**Commit**: `<commit-hash>` - "commit message"
**Status**: ✅ Complete / ⚠️ Partial / ❌ Blocked
**Notes**: Any additional context or gotchas
```

#### Example Update

After implementing descartes_curvature():

```markdown
### [2025-10-29 14:30] Phase 1: Descartes Circle Theorem - Curvature Calculation
**What was done**: Implemented core Descartes Circle Theorem for calculating the curvature of a fourth circle tangent to three mutually tangent circles.
**Specifics**:
- Used fractions.Fraction for exact rational arithmetic
- Implemented both + and - solutions using formula: k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)
- Square root calculated using Fraction-compatible math.isqrt() and approximation
- Handles negative curvatures (enclosing circles)
**Files changed**:
- `backend/core/descartes.py` - Created new file with descartes_curvature() function (45 lines)
**Tests added**:
- `backend/tests/test_descartes.py` - Added TestDescartesCircleTheorem class with 4 test methods
  - test_known_configuration: Tests (-1, 2, 2, 3) → (6, 14/15)
  - test_identical_curvatures: Tests (1, 1, 1)
  - test_negative_curvature: Tests enclosing circle behavior
  - test_large_curvatures: Tests numerical stability
**Commit**: `a4f7c29` - "feat(core): implement Descartes Circle Theorem for curvatures"
**Status**: ✅ Complete
**Notes**: All 4 tests passing. Ready for center calculation (complex Descartes). Considered using Numba @jit but incompatible with Fraction type - will revisit in optimization phase.
```

#### Instructions

1. Use current timestamp in format `[YYYY-MM-DD HH:MM]`
2. Include phase number and descriptive task name
3. Be specific in "What was done" - should be understandable without reading code
4. List ALL files modified, created, or deleted with brief description
5. List ALL test files and what they test
6. Include actual commit hash after committing
7. Use status indicators: ✅ Complete, ⚠️ Partial, ❌ Blocked
8. Add notes for context, gotchas, or future considerations

---

### DEBUG_LOG.md: Error Solutions Database

#### CRITICAL: Search BEFORE Debugging

**BEFORE attempting to fix ANY error:**

1. Copy key error message phrases
2. Search DEBUG_LOG.md using grep (see search methods below)
3. If similar error found, try that solution FIRST
4. Only proceed with new debugging if no match or solution doesn't work

#### Search Methods

```bash
# Method 1: Search by error message keywords
grep -i "import error" DEBUG_LOG.md
grep -i "module not found" DEBUG_LOG.md

# Method 2: Search by file/module name
grep "descartes.py" DEBUG_LOG.md

# Method 3: Search by error type
grep "TypeError" DEBUG_LOG.md
grep "Import Error" DEBUG_LOG.md

# Method 4: Search by category
grep "### Backend Errors" -A 50 DEBUG_LOG.md
grep "### Frontend Errors" -A 50 DEBUG_LOG.md

# Method 5: Case-insensitive with context (shows 10 lines after match)
grep -i -A 10 "fraction" DEBUG_LOG.md
```

#### Example Search Workflow

```
Error encountered: "TypeError: Cannot determine Numba type of <class 'fractions.Fraction'>"

Step 1: Extract keywords: "numba" "fraction"
Step 2: Search DEBUG_LOG.md:
  $ grep -i "numba" DEBUG_LOG.md
  $ grep -i "fraction" DEBUG_LOG.md

Step 3: If match found (e.g., ERR-003), read that entry
Step 4: Try the documented solution
Step 5: If it works, continue. If not, debug normally.
```

#### When to Update

Update DEBUG_LOG.md **IMMEDIATELY** after resolving ANY error:
- Import/dependency errors
- Test failures
- Runtime errors
- Compilation/build errors
- Type errors
- Logic bugs
- Configuration problems
- Any unexpected behavior

#### Required Format

```markdown
#### [ERR-XXX] YYYY-MM-DD - Brief Error Title
**Error Message**:
```
Full error message or relevant stack trace
```
**Context**: Where/when error occurred (file, function, line, test)
**Root Cause**: What actually caused the error (be specific and technical)
**Solution**: Exact steps taken to fix, including code changes
**Prevention**: How to avoid this error in future
**Related**: Links to similar errors (ERR-XXX)
**Files Changed**: List of files modified to fix
```

#### Example Update

After fixing a Numba/Fraction incompatibility:

```markdown
#### [ERR-007] 2025-10-29 - Numba JIT Compilation Fails with Fraction Type
**Error Message**:
```
TypeError: Cannot determine Numba type of <class 'fractions.Fraction'>
  File "backend/core/descartes.py", line 15, in descartes_curvature
    @jit(nopython=True)
```
**Context**: Attempting to apply @jit decorator to descartes_curvature() function that uses fractions.Fraction for exact arithmetic
**Root Cause**: Numba only supports primitive numeric types (int, float, complex). It does not and cannot support Python's fractions.Fraction class because Fraction is a Python object with methods, not a primitive type.
**Solution**:
1. Removed @jit decorator from descartes_curvature()
2. Kept exact Fraction arithmetic for correctness
3. Added note to revisit optimization in Phase 7
4. If optimization needed later, options are:
   - Use Numba on separate float-based helper functions
   - Convert to C extension (via Cython) for performance
   - Accept pure Python performance (sufficient for single-user)
**Prevention**:
- Check Numba documentation for supported types before using @jit
- Only use @jit on functions with int/float/complex operations
- Keep Fraction-based calculations in pure Python
- Consider Cython instead of Numba for non-primitive types
**Related**: None yet
**Files Changed**:
- `backend/core/descartes.py` - Removed @jit decorator (line 15)
```

#### Error ID Numbering

- Start at ERR-001
- Increment by 1 for each new error
- Use format ERR-XXX (with leading zeros: ERR-001, ERR-012, ERR-123)
- Never reuse IDs
- If updating an existing error, use the same ID

#### Categories

Organize errors under these category headers:
- `### Backend Errors`
- `### Frontend Errors`
- `### Database Errors`
- `### Test Errors`
- `### Build/Configuration Errors`
- `### WebSocket Errors`
- `### Performance Issues`

---

### Tips for Effective Documentation

1. **Be immediate**: Update right after completing/fixing, not later
2. **Be specific**: "Changed X to Y because Z" not "Fixed it"
3. **Be searchable**: Use keywords that future searches will find
4. **Be complete**: Include all relevant files and context
5. **Be helpful**: Write for someone encountering this in 6 months
6. **Link related items**: Reference related errors or history entries

---

## Commit Message Standards

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `test`: Adding tests
- `refactor`: Code refactoring
- `docs`: Documentation
- `style`: Formatting, no code change
- `chore`: Maintenance tasks

### Examples

```
feat(core): implement Descartes Circle Theorem

- Add descartes_curvature() for calculating k4 from k1, k2, k3
- Add descartes_center() for calculating circle positions
- Use exact rational arithmetic with fractions.Fraction

Implements DESIGN_SPEC.md section 8.1
```

```
test(core): add unit tests for Descartes theorem

- Test known configuration (-1, 2, 2, 3)
- Test identical curvatures (1, 1, 1)
- Test negative curvatures (enclosing circle)
- Test numerical stability with large values

All tests passing.
```

```
fix(api): handle zero curvature validation

Previously allowed zero curvatures, which represent infinite-radius
circles not yet supported. Now returns 400 Bad Request with clear
error message.

Fixes issue discovered during integration testing.
```

---

## Summary: Key Rules

1. ✅ **DO**: Read docs before implementing
2. ✅ **DO**: Ask user for approval on design decisions
3. ✅ **DO**: Implement one small piece at a time
4. ✅ **DO**: Write tests for every component
5. ✅ **DO**: Run tests immediately after implementation
6. ✅ **DO**: Commit after each complete unit of work
7. ✅ **DO**: Reference specific document sections
8. ✅ **DO**: Admit when you're unsure

9. ❌ **DON'T**: Implement multiple features at once
10. ❌ **DON'T**: Skip writing tests
11. ❌ **DON'T**: Guess at APIs or make up functionality
12. ❌ **DON'T**: Add features not in the specification
13. ❌ **DON'T**: Commit untested code
14. ❌ **DON'T**: Make breaking changes without asking

---

## Final Checklist Before Each Implementation

Before writing any code, ask yourself:

- [ ] Have I read the relevant section of the specification?
- [ ] Do I understand what needs to be implemented?
- [ ] Have I asked the user to confirm the approach?
- [ ] Is this task small enough (< 200 lines of code)?
- [ ] Do I know what tests I'll write?
- [ ] Am I uncertain about anything? (If yes, ask user)

---

**Remember**: It's better to ask too many questions than to implement the wrong thing. The user prefers collaboration over speed.

**Good luck! 🚀**
