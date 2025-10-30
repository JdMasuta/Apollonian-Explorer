# Apollonian Gasket Visualizer

An interactive web application for generating, analyzing, and visualizing Apollonian gaskets with advanced sequence detection capabilities.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)

## Overview

The Apollonian Gasket Visualizer is a mathematical tool that:
- Generates Apollonian gaskets from customizable initial curvatures
- Detects and highlights mathematical sequences within the gasket
- Provides interactive canvas-based visualization with pan/zoom
- Exports high-resolution graphics and data for research
- Caches computations for improved performance over time

### What is an Apollonian Gasket?

An Apollonian gasket is a fractal generated from three mutually tangent circles by repeatedly filling the gaps with new tangent circles. Named after the ancient Greek mathematician Apollonius of Perga, these structures exhibit fascinating mathematical properties including:
- Integer curvatures following predictable sequences
- Connections to number theory and modular arithmetic
- Self-similar fractal structure at all scales
- Rich relationships to continued fractions and Fibonacci numbers

## Features

### Core Functionality
- **Exact Arithmetic**: Uses Python's `fractions.Fraction` for mathematically precise curvatures
- **Real-Time Generation**: WebSocket streaming shows circles as they're computed
- **Interactive Visualization**: Pan, zoom, and click circles on HTML5 canvas
- **Sequence Detection**: 5 built-in sequence types with extensible architecture
- **Intelligent Caching**: Frequently-used gaskets retrieved instantly from database

### Sequence Types
1. **Curvature Sequences**: Classic a(n) = 4a(n-1) - a(n-2) recurrence
2. **Generation-Based**: All circles at a specific depth level
3. **Fibonacci-Related**: Patterns connected to Fibonacci numbers
4. **Residue Classes**: Number-theoretic patterns (mod 24)
5. **Parent-Child Lineage**: Genealogical chains through the gasket

### Visualization Features
- **Color Schemes**: Default, 5 presets, or custom colors
- **Highlighting**: Opaque fills and colored borders for sequences
- **Selective Display**: Toggle visibility of non-sequence circles
- **Multi-View**: Synchronized canvas, list, and detail views
- **High-DPI Support**: Crisp rendering on retina displays

### Export Options
- **SVG**: Scalable vector graphics for publications (configurable depth/size)
- **JSON**: Complete data structure for programmatic analysis
- **CSV**: Spreadsheet-compatible circle properties

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ap-gask

# Run setup script
./scripts/setup.sh

# Start development servers
npm run dev
```

Visit http://localhost:5173 in your browser.

### Generate Your First Gasket

1. Set initial curvatures (default: 1, 1, 1)
2. Choose recursion depth (recommended: 5-7 for first try)
3. Click "Generate" and watch the gasket appear
4. Use mouse wheel to zoom, drag to pan
5. Click any circle to view its properties

See [QUICKSTART.md](QUICKSTART.md) for detailed walkthrough.

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)**: User guide and common workflows
- **[DESIGN_SPEC.md](DESIGN_SPEC.md)**: Complete technical specification
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)**: Phase-by-phase development guide

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy 2.0**: ORM for database operations
- **SQLite3**: Embedded database (PostgreSQL for production)
- **NumPy + Numba**: Numerical computing and JIT compilation
- **WebSockets**: Real-time circle streaming

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Zustand**: Lightweight state management
- **react-konva**: Canvas-based rendering
- **Material-UI**: Component library

### Mathematics
- **Python fractions.Fraction**: Exact rational arithmetic
- **Descartes Circle Theorem**: Core generation algorithm
- **Complex number arithmetic**: Position calculations

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Frontend (React)                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │   Canvas    │  │  Sequence    │  │ Circle  │ │
│  │ (react-konva)│  │   Panel      │  │ Details │ │
│  └─────────────┘  └──────────────┘  └─────────┘ │
│           │              │                │       │
│           └──────────────┴────────────────┘       │
│                          │                        │
│                    Zustand Stores                 │
└──────────────────────────┬──────────────────────┘
                           │
                      REST + WebSocket
                           │
┌──────────────────────────┴──────────────────────┐
│              Backend (FastAPI)                   │
│  ┌──────────────┐  ┌────────────┐  ┌──────────┐ │
│  │    API       │  │  Services  │  │   Core   │ │
│  │  Endpoints   │→ │  Business  │→ │ Algorithms│ │
│  │              │  │   Logic    │  │ Descartes│ │
│  └──────────────┘  └────────────┘  └──────────┘ │
│                          │                        │
│                     SQLAlchemy                    │
│                          │                        │
│                     ┌────┴────┐                   │
│                     │ SQLite3 │                   │
│                     │Database │                   │
│                     └─────────┘                   │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
ap-gask/
├── backend/              # Python FastAPI application
│   ├── api/             # REST and WebSocket endpoints
│   ├── core/            # Mathematical algorithms
│   ├── db/              # Database models and session
│   ├── schemas/         # Pydantic data validation
│   ├── services/        # Business logic layer
│   └── utils/           # Helper functions
│
├── frontend/            # React application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── stores/      # Zustand state management
│   │   ├── services/    # API clients
│   │   ├── hooks/       # Custom React hooks
│   │   └── utils/       # Helper functions
│   └── tests/           # Frontend tests
│
├── scripts/             # Deployment and setup scripts
├── DESIGN_SPEC.md         # Technical specifications
├── IMPLEMENTATION_PLAN.md # Development guide
└── QUICKSTART.md        # User guide
```

## Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Setup Development Environment

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Start both
cd ..
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend
black backend/
isort backend/
mypy backend/

# Frontend
cd frontend
npm run lint
npm run format
```

## Deployment

### Single-Command Deployment

```bash
./scripts/deploy.sh
```

This will:
1. Install backend dependencies
2. Build frontend production bundle
3. Copy frontend to backend static folder
4. Initialize database
5. Start FastAPI server on port 8000

Access at http://localhost:8000

### Manual Deployment

```bash
# Build frontend
cd frontend
npm install
npm run build

# Copy to backend
mkdir -p ../backend/static
cp -r dist/* ../backend/static/

# Start backend
cd ../backend
pip install -r requirements.txt
python -c "from db.base import Base, engine; Base.metadata.create_all(bind=engine)"
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Performance

### Generation Times (Approximate)

| Depth | Circles | Time      | Use Case              |
|-------|---------|-----------|------------------------|
| 5     | ~100    | <100ms    | Quick exploration     |
| 7     | ~500    | ~500ms    | Interactive work      |
| 10    | ~5,000  | ~5s       | Detailed analysis     |
| 12    | ~50,000 | ~60s      | Publication graphics  |

### Optimization Strategies
- **Caching**: Repeat gaskets retrieved instantly from database
- **Streaming**: WebSocket sends circles as computed (no blocking)
- **Numba JIT**: Critical loops compiled to machine code
- **Canvas Virtualization**: Only render visible circles (future)
- **GPU Acceleration**: CuPy for massive computations (future)

## Use Cases

### Mathematical Research
- Explore integer sequences (OEIS integration)
- Analyze residue class patterns
- Study fractal dimensions
- Investigate curvature distributions

### Education
- Demonstrate Descartes Circle Theorem
- Visualize fractal growth
- Show parent-child relationships
- Interactive geometry lessons

### Art and Visualization
- Generate unique fractal patterns
- Create publication-quality graphics
- Design poster artwork
- Animated gasket construction

## API Documentation

### REST Endpoints

```
POST   /api/gaskets                    Create/retrieve gasket
GET    /api/gaskets/{id}               Get gasket by ID
GET    /api/gaskets/{id}/circles       Get circles with filters
POST   /api/sequences/detect           Detect sequence pattern
GET    /api/sequences/{id}             Get sequence by ID
POST   /api/export/svg                 Generate SVG export
POST   /api/export/json                Export as JSON
POST   /api/export/csv                 Export as CSV
```

### WebSocket

```
/ws/gasket/generate                    Real-time gasket generation
```

See [DESIGN_SPEC.md](DESIGN_SPEC.md) for detailed API reference.

## Contributing

### Adding New Sequence Types

1. Implement detector in `backend/core/sequence_detector.py`
2. Add schema in `backend/schemas/sequence.py`
3. Register in API config endpoint
4. Add UI option in `SequenceTypeSelector.jsx`
5. Write tests

Example:
```python
def detect_custom_sequence(circles: List[Circle], **params):
    """Detect custom pattern."""
    return [c for c in circles if custom_condition(c, params)]
```

### Improving Performance

- Profile with `cProfile` and `line_profiler`
- Identify hot paths in generation loop
- Consider Cython for critical sections
- Add parallelization with multiprocessing
- Implement GPU acceleration (CuPy)

### UI Enhancements

- Implement keyboard shortcuts
- Add touch gesture support
- Create animation mode
- Build comparison tool
- Add dark mode

## Roadmap

### v1.0 (Current MVP)
- [x] Core gasket generation
- [x] 5 sequence types
- [x] Interactive canvas
- [x] Export (SVG, JSON, CSV)
- [x] Caching system
- [x] Single-command deployment

### v1.1 (Next Release)
- [ ] GPU acceleration (CuPy)
- [ ] Web Workers for background computation
- [ ] Canvas virtualization (10,000+ circles)
- [ ] Animation mode
- [ ] Keyboard shortcuts

### v2.0 (Future)
- [ ] 3D Apollonian sphere packing
- [ ] Custom sequence builder (user-defined)
- [ ] Multi-user support with authentication
- [ ] PostgreSQL migration
- [ ] Cloud deployment
- [ ] Collaborative features

## Known Limitations

### Current Version
- Desktop-only (mobile support planned)
- Single-user (no authentication)
- SQLite database (PostgreSQL for production)
- Depth limited to 12 (memory constraints)
- Square root approximations lose exact arithmetic

### Workarounds
- For mobile: Use desktop in Chrome/Firefox
- For multi-user: Deploy multiple instances
- For deep gaskets: Export data, compute offline
- For exact positions: Consider symbolic computation (sympy)

## FAQ

**Q: Why are curvatures stored as fractions?**
A: Apollonian gasket curvatures are exactly rational. Using floats introduces cumulative errors.

**Q: How does caching work?**
A: Gaskets are hashed by their initial curvatures (canonical form). Identical configurations retrieved from database.

**Q: Can I export circles at deeper levels than displayed?**
A: Yes! SVG export allows configurable depth independent of visualization.

**Q: What's the maximum recursion depth?**
A: Default limit is 12 (configurable in .env). Beyond that, memory and time become prohibitive.

**Q: How do I add custom sequences?**
A: See "Contributing" section. Implement detector function, register in API, add UI option.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Apollonius of Perga (c. 240 BC): Original circle tangency theorems
- René Descartes (1643): Generalization to curvature formula
- OEIS (Online Encyclopedia of Integer Sequences): Sequence references
- FastAPI, React, Konva communities: Excellent frameworks

## Citation

If you use this tool in research, please cite:

```bibtex
@software{apollonian_gasket_visualizer,
  title={Apollonian Gasket Visualizer},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/ap-gask}
}
```

## Contact

- Issues: GitHub Issues (future)
- Discussions: GitHub Discussions (future)
- Email: your.email@example.com

---

**Built with mathematical precision and visual elegance.**
