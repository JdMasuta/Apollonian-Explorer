# Apollonian Gasket Visualization Tool - Implementation Plan

## Executive Summary

This document provides a step-by-step implementation guide for building an interactive Apollonian gasket visualization tool. The project uses a modern web stack (FastAPI + React) with emphasis on mathematical correctness, performance optimization through caching, and rich user interactions.

**Estimated Timeline**: 21 days (3 weeks)
**Team Size**: 1-2 developers
**Complexity**: High (mathematical algorithms + real-time visualization)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
3. [Critical Path Items](#critical-path-items)
4. [Risk Assessment](#risk-assessment)
5. [Testing Checklist](#testing-checklist)
6. [Deployment Checklist](#deployment-checklist)

---

## Prerequisites

### Development Environment
- Python 3.11+ with pip/poetry
- Node.js 18+ with npm/yarn
- SQLite3 (included with Python)
- Git
- Code editor (VS Code recommended)

### Knowledge Requirements
- **Essential**: Python, React, REST APIs
- **Important**: FastAPI, SQLAlchemy, Zustand, Canvas APIs
- **Helpful**: Computational geometry, number theory, Descartes Circle Theorem

### Initial Setup (30 minutes)
```bash
# Create project directory
mkdir ap-gask && cd ap-gask

# Initialize git
git init

# Create monorepo structure
mkdir -p backend/{api/endpoints,core,db/models,schemas,services,utils,tests}
mkdir -p frontend/{src/{components,stores,services,hooks,utils,styles},tests}
mkdir -p scripts

# Create root package.json for workspaces
cat > package.json << 'JSON'
{
  "name": "ap-gask-monorepo",
  "private": true,
  "workspaces": ["frontend", "backend"],
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
    "dev:backend": "cd backend && uvicorn main:app --reload --port 8000",
    "dev:frontend": "cd frontend && npm run dev",
    "build": "cd frontend && npm run build",
    "deploy": "./scripts/deploy.sh"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
JSON

# Initialize backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install fastapi uvicorn sqlalchemy pydantic numpy numba pytest

# Initialize frontend
cd ../frontend
npm init -y
npm install react react-dom react-konva konva @mui/material @emotion/react @emotion/styled zustand axios
npm install -D vite @vitejs/plugin-react vitest
```

---

## Phase-by-Phase Implementation

### Phase 0: Project Foundation (Day 1)

#### Goals
- Set up monorepo structure
- Configure tooling and linters
- Create deployment scripts
- Establish development workflow

#### Tasks

**1. Backend Setup (2 hours)**
```bash
cd backend

# Create main.py
cat > main.py << 'PYTHON'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.router import api_router

app = FastAPI(title="Apollonian Gasket API", version="1.0.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")

# Mount static files (frontend build)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
PYTHON

# Create config.py
cat > config.py << 'PYTHON'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./apollonian_gasket.db"
    DEBUG: bool = True
    MAX_RECURSION_DEPTH: int = 12
    CACHE_SIZE_LIMIT_MB: int = 500
    
    class Config:
        env_file = ".env"

settings = Settings()
PYTHON

# Create .env
cat > .env << 'ENV'
DATABASE_URL=sqlite:///./apollonian_gasket.db
DEBUG=true
ENV

# Create requirements.txt
cat > requirements.txt << 'TXT'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.4.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
websockets>=12.0
numpy>=1.24.0
numba>=0.58.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
TXT
```

**2. Frontend Setup (2 hours)**
```bash
cd ../frontend

# Create vite.config.js
cat > vite.config.js << 'JS'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
JS

# Create src/main.jsx
mkdir -p src
cat > src/main.jsx << 'JSX'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import './styles/global.css'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
JSX

# Create src/App.jsx
cat > src/App.jsx << 'JSX'
import React from 'react'
import { Container, Typography, Box } from '@mui/material'

function App() {
  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Apollonian Gasket Visualizer
        </Typography>
        <Typography variant="body1">
          Setup complete. Ready to build!
        </Typography>
      </Box>
    </Container>
  )
}

export default App
JSX

# Create index.html
cat > index.html << 'HTML'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Apollonian Gasket Visualizer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
HTML
```

**3. Deployment Scripts (1 hour)**
```bash
cd ../scripts

# Create setup.sh
cat > setup.sh << 'BASH'
#!/bin/bash
set -e

echo "Setting up Apollonian Gasket Visualizer..."

# Backend setup
echo "Setting up backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend setup
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo "Setup complete! Run 'npm run dev' to start development."
BASH
chmod +x setup.sh

# Create deploy.sh (see DESIGN_SPEC.md for full version)
cat > deploy.sh << 'BASH'
#!/bin/bash
set -e

echo "Deploying Apollonian Gasket Visualizer..."

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Build frontend
cd frontend
npm install
npm run build
cd ..

# Copy frontend to backend static
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

# Initialize database
cd backend
python -c "from db.base import Base, engine; Base.metadata.create_all(bind=engine)"
cd ..

# Start server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
BASH
chmod +x deploy.sh
```

**4. Testing (1 hour)**
```bash
# Test backend
cd backend
uvicorn main:app --reload &
sleep 2
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
kill %1

# Test frontend
cd ../frontend
npm run dev &
sleep 3
curl http://localhost:5173
# Should return HTML
kill %1

# Test monorepo dev command
cd ..
npm run dev &
sleep 5
# Both servers should be running
kill %1
```

**Deliverables**:
- ✅ Working monorepo structure
- ✅ Backend serves health check
- ✅ Frontend renders basic UI
- ✅ `npm run dev` starts both servers
- ✅ Deployment script created

---

### Phase 1: Core Mathematics (Days 2-4)

#### Goals
- Implement Descartes Circle Theorem with exact arithmetic
- Create gasket generation algorithm
- Set up database models
- Build basic API endpoints

#### Critical Algorithm: Descartes Circle Theorem

**Mathematical Foundation**:
Given three mutually tangent circles with curvatures k₁, k₂, k₃, the curvature k₄ of the fourth circle tangent to all three is:

```
k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)
```

For positions (using complex numbers):
```
k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)
```

**Implementation** (`backend/core/descartes.py`):

```python
from fractions import Fraction
from typing import Tuple, List
import math

# Type aliases for clarity
Curvature = Fraction
ComplexFraction = Tuple[Fraction, Fraction]  # (real, imag)
Circle = Tuple[Curvature, ComplexFraction]  # (curvature, center)


def complex_multiply(a: ComplexFraction, b: ComplexFraction) -> ComplexFraction:
    """Multiply two complex numbers represented as Fraction tuples."""
    real_a, imag_a = a
    real_b, imag_b = b
    return (
        real_a * real_b - imag_a * imag_b,
        real_a * imag_b + imag_a * real_b
    )


def complex_sqrt(z: ComplexFraction) -> ComplexFraction:
    """
    Compute square root of complex number.
    WARNING: This requires float conversion and loses exactness.
    For production, consider using sympy for symbolic computation.
    """
    real, imag = z
    r_float = float(real)
    i_float = float(imag)
    
    magnitude = math.sqrt(r_float**2 + i_float**2)
    sqrt_magnitude = math.sqrt(magnitude)
    angle = math.atan2(i_float, r_float) / 2
    
    result_real = sqrt_magnitude * math.cos(angle)
    result_imag = sqrt_magnitude * math.sin(angle)
    
    # Convert back to Fraction (approximate)
    return (
        Fraction(result_real).limit_denominator(1000000),
        Fraction(result_imag).limit_denominator(1000000)
    )


def descartes_curvature(k1: Curvature, k2: Curvature, k3: Curvature, 
                        sign: int = 1) -> Tuple[Curvature, Curvature]:
    """
    Calculate the two possible curvatures of circles tangent to three given circles.
    
    Args:
        k1, k2, k3: Curvatures of three mutually tangent circles
        sign: +1 or -1 to select which solution
    
    Returns:
        Two curvature solutions (positive and negative branch)
    """
    sum_curv = k1 + k2 + k3
    product_sum = k1*k2 + k2*k3 + k3*k1
    
    # k₄ = k₁ + k₂ + k₃ ± 2√(k₁k₂ + k₂k₃ + k₃k₁)
    sqrt_term = Fraction(int(math.sqrt(float(product_sum)) * 1000000), 1000000)
    sqrt_term = sqrt_term.limit_denominator(1000000)
    
    k4_plus = sum_curv + 2 * sqrt_term
    k4_minus = sum_curv - 2 * sqrt_term
    
    return k4_plus, k4_minus


def descartes_center(c1: Circle, c2: Circle, c3: Circle, 
                     k4: Curvature) -> ComplexFraction:
    """
    Calculate center of fourth circle given three tangent circles and its curvature.
    
    Args:
        c1, c2, c3: Tuples of (curvature, center) for three tangent circles
        k4: Curvature of the fourth circle
    
    Returns:
        Center of fourth circle as complex Fraction tuple
    """
    k1, z1 = c1
    k2, z2 = c2
    k3, z3 = c3
    
    # k₄z₄ = k₁z₁ + k₂z₂ + k₃z₃ ± 2√(k₁k₂z₁z₂ + k₂k₃z₂z₃ + k₃k₁z₃z₁)
    term1 = (k1 * z1[0], k1 * z1[1])
    term2 = (k2 * z2[0], k2 * z2[1])
    term3 = (k3 * z3[0], k3 * z3[1])
    
    sum_terms = (
        term1[0] + term2[0] + term3[0],
        term1[1] + term2[1] + term3[1]
    )
    
    # Compute sqrt term (this is approximate)
    prod1 = complex_multiply((k1, Fraction(0)), complex_multiply((k2, Fraction(0)), complex_multiply(z1, z2)))
    prod2 = complex_multiply((k2, Fraction(0)), complex_multiply((k3, Fraction(0)), complex_multiply(z2, z3)))
    prod3 = complex_multiply((k3, Fraction(0)), complex_multiply((k1, Fraction(0)), complex_multiply(z3, z1)))
    
    sum_prod = (
        prod1[0] + prod2[0] + prod3[0],
        prod1[1] + prod2[1] + prod3[1]
    )
    
    sqrt_prod = complex_sqrt(sum_prod)
    sqrt_term = (sqrt_prod[0] * 2, sqrt_prod[1] * 2)
    
    # z₄ = (sum_terms + sqrt_term) / k₄
    numerator = (
        sum_terms[0] + sqrt_term[0],
        sum_terms[1] + sqrt_term[1]
    )
    
    z4 = (numerator[0] / k4, numerator[1] / k4)
    
    return z4


def descartes_solve(c1: Circle, c2: Circle, c3: Circle, 
                    sign: int = 1) -> Tuple[Circle, Circle]:
    """
    Find two circles tangent to three given mutually tangent circles.
    
    Args:
        c1, c2, c3: Three mutually tangent circles
        sign: Which branch of the solution to use
    
    Returns:
        Two new tangent circles (inner and outer)
    """
    k1, _ = c1
    k2, _ = c2
    k3, _ = c3
    
    k4_plus, k4_minus = descartes_curvature(k1, k2, k3, sign)
    
    z4_plus = descartes_center(c1, c2, c3, k4_plus)
    z4_minus = descartes_center(c1, c2, c3, k4_minus)
    
    return (k4_plus, z4_plus), (k4_minus, z4_minus)


# Test cases
if __name__ == "__main__":
    # Test with three mutually tangent circles of curvature 1
    k1, k2, k3 = Fraction(1), Fraction(1), Fraction(1)
    
    # These circles should be arranged in a specific configuration
    # For simplicity, using a standard configuration
    c1 = (k1, (Fraction(0), Fraction(0)))
    c2 = (k2, (Fraction(2), Fraction(0)))
    c3 = (k3, (Fraction(1), Fraction(int(math.sqrt(3) * 1000), 1000)))
    
    (k4_plus, z4_plus), (k4_minus, z4_minus) = descartes_solve(c1, c2, c3)
    
    print(f"New circles:")
    print(f"  Circle 1: curvature={k4_plus}, center={z4_plus}")
    print(f"  Circle 2: curvature={k4_minus}, center={z4_minus}")
```

**Task Breakdown**:

**Day 2: Descartes Implementation (6 hours)**
1. Create `backend/core/descartes.py` with above code
2. Add helper functions for Fraction math
3. Write unit tests for known configurations
4. Document mathematical assumptions and limitations

**Day 3: Gasket Generator (6 hours)**

Create `backend/core/gasket_generator.py`:

```python
from typing import List, Generator, Set, Tuple
from fractions import Fraction
from collections import deque
import hashlib
import json

from .descartes import Circle, descartes_solve, Curvature, ComplexFraction


class CircleData:
    """Data class for a circle in the gasket."""
    def __init__(self, curvature: Curvature, center: ComplexFraction, 
                 generation: int, parent_ids: List[int]):
        self.curvature = curvature
        self.center = center
        self.generation = generation
        self.parent_ids = parent_ids
        self.id = None  # Set when added to database
        self.tangent_ids = []
    
    def to_dict(self):
        return {
            'curvature': f"{self.curvature.numerator}/{self.curvature.denominator}",
            'center_x': f"{self.center[0].numerator}/{self.center[0].denominator}",
            'center_y': f"{self.center[1].numerator}/{self.center[1].denominator}",
            'radius': f"{(1/self.curvature).numerator}/{(1/self.curvature).denominator}",
            'generation': self.generation,
            'parent_ids': self.parent_ids
        }
    
    def hash_key(self) -> str:
        """Generate unique hash for circle (for deduplication)."""
        key = f"{self.curvature}_{self.center[0]}_{self.center[1]}"
        return hashlib.md5(key.encode()).hexdigest()


def initialize_standard_gasket(curvatures: List[Curvature]) -> List[CircleData]:
    """
    Initialize a standard Apollonian gasket with 3 or 4 initial circles.
    
    For three curvatures, creates a standard packing.
    For four curvatures, uses them as-is.
    """
    if len(curvatures) == 3:
        # Standard configuration: three mutually tangent circles
        k1, k2, k3 = curvatures
        
        # Place circles in standard positions
        # Circle 1: center at origin
        c1 = CircleData(k1, (Fraction(0), Fraction(0)), 0, [])
        
        # Circle 2: tangent to right
        r1 = 1 / k1
        r2 = 1 / k2
        c2 = CircleData(k2, (r1 + r2, Fraction(0)), 0, [])
        
        # Circle 3: above (using geometry)
        # Simplified: actual position requires solving tangency constraints
        # For MVP, use approximate placement
        c3 = CircleData(k3, (Fraction(1), Fraction(1)), 0, [])
        
        return [c1, c2, c3]
    
    elif len(curvatures) == 4:
        # Use provided configuration
        # Requires user to specify positions (future enhancement)
        raise NotImplementedError("Four-circle initialization requires position specification")
    
    else:
        raise ValueError("Need 3 or 4 initial curvatures")


def generate_apollonian_gasket(
    initial_curvatures: List[Fraction],
    max_depth: int,
    stream: bool = False
) -> Generator[CircleData, None, None]:
    """
    Generate Apollonian gasket using breadth-first search.
    
    Args:
        initial_curvatures: List of 3-4 curvatures for initial circles
        max_depth: Maximum recursion depth
        stream: If True, yield circles as they're computed (for WebSocket)
    
    Yields:
        CircleData objects as they're generated
    """
    # Initialize
    circles = initialize_standard_gasket(initial_curvatures)
    circle_hashes: Set[str] = {c.hash_key() for c in circles}
    
    # Yield initial circles
    if stream:
        for circle in circles:
            yield circle
    
    # BFS queue: (circle1, circle2, circle3, depth)
    queue = deque()
    
    # Add initial triplets
    if len(circles) >= 3:
        queue.append((circles[0], circles[1], circles[2], 0))
    
    while queue:
        c1, c2, c3, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        # Convert to format expected by descartes_solve
        circle1 = (c1.curvature, c1.center)
        circle2 = (c2.curvature, c2.center)
        circle3 = (c3.curvature, c3.center)
        
        try:
            # Compute two new circles
            (k_new1, z_new1), (k_new2, z_new2) = descartes_solve(
                circle1, circle2, circle3
            )
            
            # Create CircleData objects
            new_circles = []
            for k, z in [(k_new1, z_new1), (k_new2, z_new2)]:
                new_circle = CircleData(
                    curvature=k,
                    center=z,
                    generation=depth + 1,
                    parent_ids=[c1.id, c2.id, c3.id] if c1.id else []
                )
                
                # Check for duplicates
                hash_key = new_circle.hash_key()
                if hash_key not in circle_hashes:
                    circle_hashes.add(hash_key)
                    circles.append(new_circle)
                    new_circles.append(new_circle)
                    
                    if stream:
                        yield new_circle
            
            # Add new triplets to queue
            for new_circle in new_circles:
                queue.append((c1, c2, new_circle, depth + 1))
                queue.append((c2, c3, new_circle, depth + 1))
                queue.append((c3, c1, new_circle, depth + 1))
        
        except Exception as e:
            # Skip invalid configurations
            print(f"Skipping triplet due to error: {e}")
            continue
    
    if not stream:
        for circle in circles:
            yield circle


# Test
if __name__ == "__main__":
    curvatures = [Fraction(1), Fraction(1), Fraction(1)]
    circles = list(generate_apollonian_gasket(curvatures, max_depth=3))
    print(f"Generated {len(circles)} circles at depth 3")
    for i, circle in enumerate(circles[:10]):
        print(f"  Circle {i}: curvature={circle.curvature}, gen={circle.generation}")
```

**Day 4: Database Models & API (6 hours)**

Create `backend/db/models/gasket.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from db.base import Base


class Gasket(Base):
    __tablename__ = "gaskets"
    
    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(64), unique=True, nullable=False, index=True)
    initial_curvatures = Column(Text, nullable=False)  # JSON array
    num_circles = Column(Integer)
    max_depth_cached = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at = Column(DateTime(timezone=True), onupdate=func.now())
    access_count = Column(Integer, default=1)


class Circle(Base):
    __tablename__ = "circles"
    
    id = Column(Integer, primary_key=True, index=True)
    gasket_id = Column(Integer, ForeignKey("gaskets.id", ondelete="CASCADE"), nullable=False)
    generation = Column(Integer, nullable=False)
    curvature_num = Column(Integer, nullable=False)
    curvature_denom = Column(Integer, nullable=False)
    center_x_num = Column(Integer, nullable=False)
    center_x_denom = Column(Integer, nullable=False)
    center_y_num = Column(Integer, nullable=False)
    center_y_denom = Column(Integer, nullable=False)
    radius_num = Column(Integer, nullable=False)
    radius_denom = Column(Integer, nullable=False)
    parent_ids = Column(Text)  # JSON array
    tangent_ids = Column(Text)  # JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Create `backend/api/endpoints/gaskets.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.deps import get_db
from schemas.gasket import GasketCreate, GasketResponse, CircleResponse
from services.gasket_service import GasketService

router = APIRouter()


@router.post("/gaskets", response_model=GasketResponse)
def create_gasket(
    gasket_data: GasketCreate,
    db: Session = Depends(get_db)
):
    """
    Create or retrieve an Apollonian gasket.
    If a gasket with the same initial curvatures exists, returns cached version.
    """
    service = GasketService(db)
    gasket = service.create_or_get_gasket(
        curvatures=gasket_data.curvatures,
        max_depth=gasket_data.max_depth
    )
    return gasket


@router.get("/gaskets/{gasket_id}", response_model=GasketResponse)
def get_gasket(gasket_id: int, db: Session = Depends(get_db)):
    """Retrieve a gasket by ID."""
    service = GasketService(db)
    gasket = service.get_gasket(gasket_id)
    if not gasket:
        raise HTTPException(status_code=404, detail="Gasket not found")
    return gasket


@router.get("/gaskets/{gasket_id}/circles", response_model=List[CircleResponse])
def get_circles(
    gasket_id: int,
    generation: int = None,
    min_curvature: float = None,
    max_curvature: float = None,
    db: Session = Depends(get_db)
):
    """Get circles for a gasket with optional filters."""
    service = GasketService(db)
    circles = service.get_circles(
        gasket_id=gasket_id,
        generation=generation,
        min_curvature=min_curvature,
        max_curvature=max_curvature
    )
    return circles
```

**Deliverables**:
- ✅ Working Descartes theorem implementation with tests
- ✅ Gasket generator producing valid circles
- ✅ Database models for Gasket and Circle
- ✅ REST API endpoints for gasket creation and retrieval
- ✅ Integration tests for end-to-end flow

---

### Phase 2: Real-Time Streaming (Days 5-6)

#### Goals
- Implement WebSocket endpoint
- Stream circles during generation
- Update frontend in real-time
- Handle connection management

#### Backend WebSocket (Day 5, 4 hours)

Create `backend/api/endpoints/websocket.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from fractions import Fraction
import json
import asyncio

from core.gasket_generator import generate_apollonian_gasket
from db.session import SessionLocal

router = APIRouter()


@router.websocket("/ws/gasket/generate")
async def websocket_gasket_generation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time gasket generation.
    
    Client sends: {"action": "start", "curvatures": [...], "max_depth": N}
    Server streams: {"type": "progress", "generation": N, "circles": [...]}
    Server finalizes: {"type": "complete", "gasket_id": ID, "total_circles": N}
    """
    await websocket.accept()
    
    try:
        # Receive initial request
        data = await websocket.receive_json()
        
        if data.get("action") != "start":
            await websocket.send_json({"type": "error", "message": "Invalid action"})
            return
        
        curvatures_str = data.get("curvatures", [])
        max_depth = data.get("max_depth", 5)
        
        # Parse curvatures
        curvatures = [Fraction(c) for c in curvatures_str]
        
        # Generate gasket with streaming
        circle_count = 0
        batch = []
        batch_size = 10  # Send circles in batches
        
        for circle_data in generate_apollonian_gasket(curvatures, max_depth, stream=True):
            circle_count += 1
            batch.append(circle_data.to_dict())
            
            if len(batch) >= batch_size:
                await websocket.send_json({
                    "type": "progress",
                    "generation": circle_data.generation,
                    "circles_count": circle_count,
                    "circles": batch
                })
                batch = []
                await asyncio.sleep(0.01)  # Prevent overwhelming client
        
        # Send remaining circles
        if batch:
            await websocket.send_json({
                "type": "progress",
                "circles": batch
            })
        
        # TODO: Save to database and get gasket_id
        
        # Send completion
        await websocket.send_json({
            "type": "complete",
            "gasket_id": None,  # Will be set after DB save
            "total_circles": circle_count
        })
    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
```

#### Frontend WebSocket Service (Day 5, 3 hours)

Create `frontend/src/services/websocketService.js`:

```javascript
class WebSocketService {
  constructor() {
    this.ws = null
    this.callbacks = {
      onProgress: null,
      onComplete: null,
      onError: null
    }
  }

  connect(url = 'ws://localhost:8000/ws/gasket/generate') {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        resolve()
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        reject(error)
      }
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket closed')
      }
    })
  }

  handleMessage(data) {
    switch (data.type) {
      case 'progress':
        if (this.callbacks.onProgress) {
          this.callbacks.onProgress(data)
        }
        break
      
      case 'complete':
        if (this.callbacks.onComplete) {
          this.callbacks.onComplete(data)
        }
        break
      
      case 'error':
        if (this.callbacks.onError) {
          this.callbacks.onError(data.message)
        }
        break
    }
  }

  generateGasket(curvatures, maxDepth, callbacks) {
    this.callbacks = callbacks
    
    return this.connect().then(() => {
      this.ws.send(JSON.stringify({
        action: 'start',
        curvatures: curvatures,
        max_depth: maxDepth
      }))
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default new WebSocketService()
```

#### Frontend Hook (Day 6, 2 hours)

Create `frontend/src/hooks/useGasketGeneration.js`:

```javascript
import { useState, useCallback } from 'react'
import websocketService from '../services/websocketService'
import useGasketStore from '../stores/gasketStore'

export function useGasketGeneration() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  
  const { setCircles, setGasketId } = useGasketStore()

  const generateGasket = useCallback(async (curvatures, maxDepth) => {
    setIsGenerating(true)
    setError(null)
    setProgress(0)
    setCircles([])  // Clear existing circles

    try {
      await websocketService.generateGasket(curvatures, maxDepth, {
        onProgress: (data) => {
          // Add new circles to store
          const newCircles = data.circles || []
          useGasketStore.getState().addCircles(newCircles)
          
          // Update progress
          const progressPercent = (data.circles_count / estimatedTotal(maxDepth)) * 100
          setProgress(Math.min(progressPercent, 99))
        },
        
        onComplete: (data) => {
          setGasketId(data.gasket_id)
          setProgress(100)
          setIsGenerating(false)
          websocketService.disconnect()
        },
        
        onError: (message) => {
          setError(message)
          setIsGenerating(false)
          websocketService.disconnect()
        }
      })
    } catch (err) {
      setError(err.message)
      setIsGenerating(false)
    }
  }, [setCircles, setGasketId])

  return {
    generateGasket,
    isGenerating,
    progress,
    error
  }
}

// Rough estimate of circle count for progress bar
function estimatedTotal(depth) {
  // Approximate: circles grow exponentially
  return Math.pow(3, depth + 1)
}
```

#### Integration Testing (Day 6, 2 hours)

Test scenarios:
1. Generate depth-5 gasket, verify circles stream in
2. Generate depth-10 gasket, monitor performance
3. Test WebSocket disconnect/reconnect
4. Verify circle data correctness

**Deliverables**:
- ✅ WebSocket endpoint streaming circles
- ✅ Frontend receiving and rendering circles in real-time
- ✅ Progress indicator showing generation status
- ✅ Error handling for connection issues

---

### Phase 3: Interactive Canvas (Days 7-8)

#### Goals
- Implement pan and zoom
- Circle click selection
- Smooth 60fps rendering
- Canvas controls overlay

#### Canvas Component (Day 7, 6 hours)

Create `frontend/src/components/GasketCanvas/GasketCanvas.jsx`:

```javascript
import React, { useRef, useEffect, useState } from 'react'
import { Stage, Layer, Circle } from 'react-konva'
import { Box, IconButton, Paper } from '@mui/material'
import { ZoomIn, ZoomOut, CenterFocusStrong } from '@mui/icons-material'
import useGasketStore from '../../stores/gasketStore'
import useCanvasStore from '../../stores/canvasStore'
import useSelectionStore from '../../stores/selectionStore'

export default function GasketCanvas() {
  const stageRef = useRef(null)
  const { circles } = useGasketStore()
  const { transform, setTransform, resetView } = useCanvasStore()
  const { selectedCircleId, selectCircle } = useSelectionStore()
  
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  // Handle window resize
  useEffect(() => {
    const updateDimensions = () => {
      const container = document.getElementById('canvas-container')
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: container.clientHeight
        })
      }
    }
    
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  // Fit circles in viewport
  useEffect(() => {
    if (circles.length > 0) {
      fitCircles()
    }
  }, [circles])

  const fitCircles = () => {
    if (circles.length === 0) return

    // Find bounding box
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    
    circles.forEach(circle => {
      const [x, y] = parseCenter(circle.center_x, circle.center_y)
      const r = parseRadius(circle.radius)
      
      minX = Math.min(minX, x - r)
      minY = Math.min(minY, y - r)
      maxX = Math.max(maxX, x + r)
      maxY = Math.max(maxY, y + r)
    })

    const width = maxX - minX
    const height = maxY - minY
    const padding = 1.1  // 10% padding
    
    const scaleX = dimensions.width / (width * padding)
    const scaleY = dimensions.height / (height * padding)
    const scale = Math.min(scaleX, scaleY)
    
    const centerX = (minX + maxX) / 2
    const centerY = (minY + maxY) / 2
    
    setTransform(
      dimensions.width / 2 - centerX * scale,
      dimensions.height / 2 - centerY * scale,
      scale
    )
  }

  const handleWheel = (e) => {
    e.evt.preventDefault()
    
    const stage = stageRef.current
    const oldScale = transform.scale
    const pointer = stage.getPointerPosition()

    // Zoom factor
    const scaleBy = 1.1
    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy

    // Zoom towards mouse position
    const mousePointTo = {
      x: (pointer.x - transform.x) / oldScale,
      y: (pointer.y - transform.y) / oldScale,
    }

    const newPos = {
      x: pointer.x - mousePointTo.x * newScale,
      y: pointer.y - mousePointTo.y * newScale,
    }

    setTransform(newPos.x, newPos.y, newScale)
  }

  const handleDragEnd = (e) => {
    setTransform(e.target.x(), e.target.y(), transform.scale)
  }

  const handleCircleClick = (circleId) => {
    selectCircle(circleId)
  }

  const handleZoomIn = () => {
    const newScale = transform.scale * 1.2
    setTransform(transform.x, transform.y, newScale)
  }

  const handleZoomOut = () => {
    const newScale = transform.scale / 1.2
    setTransform(transform.x, transform.y, newScale)
  }

  return (
    <Box id="canvas-container" sx={{ position: 'relative', width: '100%', height: '100%' }}>
      <Stage
        ref={stageRef}
        width={dimensions.width}
        height={dimensions.height}
        draggable
        x={transform.x}
        y={transform.y}
        scaleX={transform.scale}
        scaleY={transform.scale}
        onWheel={handleWheel}
        onDragEnd={handleDragEnd}
      >
        <Layer>
          {circles.map((circle) => {
            const [x, y] = parseCenter(circle.center_x, circle.center_y)
            const radius = parseRadius(circle.radius)
            const isSelected = circle.id === selectedCircleId
            
            return (
              <Circle
                key={circle.id}
                x={x}
                y={y}
                radius={radius}
                fill="white"
                stroke={isSelected ? '#FFD700' : '#000000'}
                strokeWidth={isSelected ? 3 / transform.scale : 1 / transform.scale}
                onClick={() => handleCircleClick(circle.id)}
                onTap={() => handleCircleClick(circle.id)}
              />
            )
          })}
        </Layer>
      </Stage>

      {/* Controls Overlay */}
      <Paper
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          p: 1
        }}
      >
        <IconButton size="small" onClick={handleZoomIn}>
          <ZoomIn />
        </IconButton>
        <IconButton size="small" onClick={handleZoomOut}>
          <ZoomOut />
        </IconButton>
        <IconButton size="small" onClick={resetView}>
          <CenterFocusStrong />
        </IconButton>
      </Paper>
    </Box>
  )
}

// Helper functions to parse fraction strings
function parseCenter(centerX, centerY) {
  return [parseFraction(centerX), parseFraction(centerY)]
}

function parseRadius(radiusStr) {
  return parseFraction(radiusStr)
}

function parseFraction(fracStr) {
  const [num, denom] = fracStr.split('/').map(Number)
  return num / denom
}
```

#### Canvas Store (Day 7, 2 hours)

Create `frontend/src/stores/canvasStore.js`:

```javascript
import { create } from 'zustand'

const useCanvasStore = create((set) => ({
  transform: {
    x: 0,
    y: 0,
    scale: 1
  },
  
  viewport: {
    width: 800,
    height: 600
  },

  setTransform: (x, y, scale) => set((state) => ({
    transform: { x, y, scale }
  })),

  resetView: () => set((state) => ({
    transform: { x: 0, y: 0, scale: 1 }
  })),

  panBy: (dx, dy) => set((state) => ({
    transform: {
      ...state.transform,
      x: state.transform.x + dx,
      y: state.transform.y + dy
    }
  })),

  zoomAt: (x, y, scaleDelta) => set((state) => {
    const oldScale = state.transform.scale
    const newScale = oldScale * scaleDelta
    
    const mousePointTo = {
      x: (x - state.transform.x) / oldScale,
      y: (y - state.transform.y) / oldScale,
    }

    return {
      transform: {
        x: x - mousePointTo.x * newScale,
        y: y - mousePointTo.y * newScale,
        scale: newScale
      }
    }
  }),

  setViewport: (width, height) => set((state) => ({
    viewport: { width, height }
  }))
}))

export default useCanvasStore
```

#### Performance Testing (Day 8, 2 hours)

Test with increasing circle counts:
- 100 circles: Should be instant
- 1,000 circles: Should maintain 60fps
- 10,000 circles: May need optimization (virtualization)

**Deliverables**:
- ✅ Smooth pan and zoom at 60fps
- ✅ Click to select circles
- ✅ Zoom controls working
- ✅ Auto-fit on load
- ✅ Responsive canvas sizing

---

## Critical Path Items

These are must-have features that block other work:

1. **Descartes Theorem Implementation** (Phase 1, Day 2)
   - Blocks: All gasket generation
   - Risk: High - mathematical complexity
   - Mitigation: Use proven reference implementations, extensive testing

2. **Database Schema** (Phase 1, Day 4)
   - Blocks: All persistence, caching
   - Risk: Medium - schema changes expensive later
   - Mitigation: Thorough design review, migration strategy

3. **WebSocket Streaming** (Phase 2, Days 5-6)
   - Blocks: Real-time UX
   - Risk: Medium - connection stability
   - Mitigation: Reconnection logic, fallback to REST

4. **Canvas Rendering** (Phase 3, Days 7-8)
   - Blocks: All visualization features
   - Risk: Low - well-established libraries
   - Mitigation: Use react-konva, optimize rendering

---

## Risk Assessment

### High-Risk Items

**1. Mathematical Correctness**
- **Risk**: Descartes theorem implementation produces incorrect circles
- **Impact**: Entire application unusable
- **Mitigation**:
  - Use exact rational arithmetic (Fraction)
  - Test against known configurations
  - Visual validation (circles should be tangent)
  - Cross-reference with academic papers

**2. Performance at Scale**
- **Risk**: Deep gaskets (depth 10+) cause UI freezing
- **Impact**: Poor user experience, unusable for research
- **Mitigation**:
  - Implement streaming (WebSocket)
  - Add progress indicators
  - Use Web Workers for computation (future)
  - Implement canvas virtualization (render only visible circles)

**3. Caching Complexity**
- **Risk**: Cache invalidation bugs, incorrect lookups
- **Impact**: Wrong gaskets returned, data corruption
- **Mitigation**:
  - Robust hashing (canonical form)
  - Comprehensive testing
  - Cache versioning
  - Manual cache clear option

### Medium-Risk Items

**1. WebSocket Stability**
- **Risk**: Connection drops during long computations
- **Impact**: Lost progress, poor UX
- **Mitigation**:
  - Implement reconnection with exponential backoff
  - Fallback to REST API
  - Resume capability (save partial results)

**2. Browser Memory Limits**
- **Risk**: Very deep gaskets (10,000+ circles) exhaust memory
- **Impact**: Browser crash, data loss
- **Mitigation**:
  - Warn users for depth > 10
  - Implement pagination for circle lists
  - Canvas virtualization (future)

---

## Testing Checklist

### Unit Tests (Backend)
- [ ] Descartes curvature calculation
- [ ] Descartes center calculation
- [ ] Complex number arithmetic with Fractions
- [ ] Gasket generation (known configurations)
- [ ] Sequence detection algorithms (all 5 types)
- [ ] Hash generation (gasket, sequence)
- [ ] Database models (CRUD operations)
- [ ] API schemas (validation)

### Integration Tests (Backend)
- [ ] Full gasket generation flow (API → Service → Core → DB)
- [ ] WebSocket message handling
- [ ] Cache hit/miss scenarios
- [ ] Export generation (SVG, JSON, CSV)
- [ ] Concurrent requests

### Component Tests (Frontend)
- [ ] Gasket store state updates
- [ ] Sequence store operations
- [ ] Canvas store transformations
- [ ] WebSocket service connection handling
- [ ] Circle selection sync (canvas ↔ list ↔ details)

### End-to-End Tests
- [ ] Generate gasket from UI
- [ ] Detect sequence and highlight
- [ ] Export SVG with highlighted sequences
- [ ] Export data (JSON, CSV)
- [ ] Pan, zoom, and select circles
- [ ] Navigate parent/tangent relationships

### Performance Tests
- [ ] Gasket generation time (depths 5, 7, 10)
- [ ] Canvas rendering FPS (100, 1k, 10k circles)
- [ ] WebSocket latency
- [ ] Database query performance
- [ ] Cache hit ratio after N gaskets

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code review complete
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Database migrations ready

### Deployment Steps
1. [ ] Clone repository
2. [ ] Run `./scripts/setup.sh`
3. [ ] Run `./scripts/deploy.sh`
4. [ ] Verify backend health: `curl http://localhost:8000/health`
5. [ ] Open browser: `http://localhost:8000`
6. [ ] Test basic flow: generate gasket, detect sequence, export

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Test all features manually
- [ ] Verify database created correctly
- [ ] Check file permissions
- [ ] Test on clean machine (if possible)

---

## Appendix: Useful Commands

### Development
```bash
# Start development servers
npm run dev

# Backend only
cd backend && uvicorn main:app --reload

# Frontend only
cd frontend && npm run dev

# Run tests
cd backend && pytest
cd frontend && npm test
```

### Database
```bash
# Initialize database
cd backend && python -c "from db.base import Base, engine; Base.metadata.create_all(bind=engine)"

# Drop all tables (careful!)
cd backend && python -c "from db.base import Base, engine; Base.metadata.drop_all(bind=engine)"

# SQLite CLI
sqlite3 backend/apollonian_gasket.db
```

### Debugging
```bash
# Backend logs
cd backend && uvicorn main:app --log-level debug

# Frontend build
cd frontend && npm run build

# Test WebSocket
websocat ws://localhost:8000/ws/gasket/generate
```

---

## Success Criteria

The project is complete when:
1. ✅ User can generate gaskets with custom curvatures
2. ✅ All 5 sequence types detect correctly
3. ✅ Interactive canvas with pan/zoom/select
4. ✅ Highlighting works with color schemes
5. ✅ Export (SVG, JSON, CSV) produces valid files
6. ✅ Caching reduces generation time for repeat gaskets
7. ✅ Single-command deployment works
8. ✅ All tests pass
9. ✅ Documentation complete

---

## Next Steps After MVP

1. **Performance Optimization**
   - GPU acceleration (CuPy)
   - Web Workers
   - Canvas virtualization
   - WASM port

2. **Feature Enhancements**
   - 3D sphere packing
   - Animation
   - Custom sequences
   - Multi-user support

3. **Production Deployment**
   - PostgreSQL migration
   - Docker containerization
   - Cloud hosting
   - CI/CD pipeline

4. **Research Features**
   - Algebraic property analysis
   - Pattern discovery
   - Fractal dimension
   - Automated conjectures
