# Apollonian Gasket Visualizer - Quick Start Guide

## Overview

This guide will get you from zero to a working Apollonian gasket visualization in 30 minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git
- 500MB free disk space

## Installation (5 minutes)

```bash
# Clone the repository (once implemented)
cd /mnt/c/Users/meeseyj/Downloads/ap-gask

# Run setup script
./scripts/setup.sh

# Or manually:
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

## Running the Application (1 minute)

### Development Mode

```bash
# From project root
npm run dev
```

This starts:
- Backend API on http://localhost:8000
- Frontend UI on http://localhost:5173

Open your browser to http://localhost:5173

### Production Mode

```bash
./scripts/deploy.sh
```

Opens on http://localhost:8000

## First Gasket (2 minutes)

1. **Set Initial Curvatures**
   - Default: 1, 1, 1 (three mutually tangent circles)
   - Try: 1, 2, 3 for different configuration

2. **Choose Recursion Depth**
   - Light (5-7): Fast, good for exploration
   - Medium (8-10): Detailed visualization
   - Heavy (11+): Research-grade, slow

3. **Click "Generate"**
   - Watch circles appear in real-time
   - Wait for completion message

4. **Interact with Canvas**
   - **Mouse wheel**: Zoom in/out
   - **Click + drag**: Pan around
   - **Click circle**: Select and view details
   - **Reset button**: Fit all circles

## Detecting Sequences (2 minutes)

1. **Choose Sequence Type**
   - Curvature: Classic a(n) = 4a(n-1) - a(n-2)
   - Generation: All circles at depth N
   - Fibonacci: Curvatures matching Fibonacci patterns
   - Residue (mod 24): Number theory patterns
   - Lineage: Parent-child chains

2. **Click "Detect Sequence"**
   - Circles in sequence highlight automatically

3. **Customize Highlighting**
   - Click color picker to change sequence color
   - Toggle visibility with eye icon
   - Hide non-sequence circles with checkbox

4. **Add More Sequences**
   - Repeat process for different types
   - Each gets a different color
   - Up to 20 sequences supported

## Exploring Circle Data (1 minute)

### Circle Details Panel (Right Side)

When you click a circle, you see:
- **Sequence Info**: Which sequences contain this circle
- **Properties**: Curvature, center, radius, generation
- **Parents**: Circles that generated this one (clickable)
- **Tangencies**: Circles touching this one (clickable)

### Circle List (Left Side)

- Searchable list of all circles
- Filter by generation, curvature
- Click to select (syncs with canvas)

## Exporting (2 minutes)

### SVG Export

1. Click "Export" button
2. Select "SVG" tab
3. Choose options:
   - Depth: How many generations to include
   - Size: Width/height in pixels (default: 2000x2000)
   - Sequences: Which highlighted sequences to include
4. Click "Download SVG"

Use in: Inkscape, Illustrator, academic papers

### JSON Export

1. Select "Data" tab
2. Choose "JSON" format
3. Click "Download"

Contains: Full gasket data structure, all circle properties, relationships

### CSV Export

1. Select "Data" tab
2. Choose "CSV" format
3. Click "Download"

Contains: Spreadsheet with columns: id, generation, curvature, center_x, center_y, radius, parents

## Common Workflows

### Research: Finding Patterns

1. Generate gasket at depth 10+
2. Detect curvature sequence
3. Detect residue class patterns (mod 24)
4. Export JSON for analysis in Python/R
5. Compare curvatures with OEIS sequences

### Visualization: Publication-Quality Graphics

1. Generate gasket at desired depth
2. Detect interesting sequences
3. Choose color scheme matching publication style
4. Hide non-sequence circles for clarity
5. Export high-res SVG (3000x3000+)
6. Post-process in vector editor

### Education: Demonstrating Concepts

1. Start with simple (1,1,1) at depth 5
2. Show generation-by-generation growth
3. Highlight curvature sequence
4. Show parent-child relationships
5. Export images for slides

## Tips and Tricks

### Performance

- **Depth 5-7**: Instant, great for experimentation
- **Depth 8-10**: 1-5 seconds, good for research
- **Depth 11+**: 10+ seconds, use for final renders

### Caching

- Same curvatures = instant retrieval
- More you use it, faster it gets
- Cache survives application restart

### Visualization

- **Zoom in**: See tiny circles at deep levels
- **Use sequences**: Reduce visual clutter
- **Hide non-sequence**: Focus on patterns
- **Multiple sequences**: Show relationships

### Data Export

- **SVG**: Vector graphics, infinite zoom
- **JSON**: Programmatic analysis
- **CSV**: Spreadsheet analysis, plotting

## Keyboard Shortcuts (Future)

- `Space`: Toggle pan mode
- `R`: Reset view
- `+/-`: Zoom in/out
- `Esc`: Clear selection
- `Ctrl+E`: Export dialog

## Troubleshooting

### "Generation failed"

- Check curvatures are valid (positive numbers)
- Reduce depth if too high (>12)
- Refresh page and retry

### "Canvas is blank"

- Click "Reset View" button
- Check console for errors (F12)
- Verify circles generated (check Circle List)

### "Slow performance"

- Reduce depth
- Close other browser tabs
- Try different browser (Chrome recommended)
- Check system resources

### "WebSocket disconnected"

- Check backend is running
- Verify no firewall blocking
- Retry generation

## API Usage (Advanced)

### Generate Gasket Programmatically

```bash
curl -X POST http://localhost:8000/api/gaskets \
  -H "Content-Type: application/json" \
  -d '{
    "curvatures": ["1", "1", "1"],
    "max_depth": 7
  }'
```

### Get Circles

```bash
curl http://localhost:8000/api/gaskets/1/circles?generation=3
```

### Detect Sequence

```bash
curl -X POST http://localhost:8000/api/sequences/detect \
  -H "Content-Type: application/json" \
  -d '{
    "gasket_id": 1,
    "sequence_type": "curvature",
    "parameters": {"seed": ["1", "1"]}
  }'
```

## Configuration

### Backend (.env)

```
DATABASE_URL=sqlite:///./apollonian_gasket.db
DEBUG=true
MAX_RECURSION_DEPTH=12
CACHE_SIZE_LIMIT_MB=500
```

### Frontend (.env)

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## What's Next?

1. **Explore Sample Gaskets**: Try different initial curvatures
2. **Read the Docs**: See IMPLEMENTATION_PLAN.md for technical details
3. **Contribute**: Add new sequence types, improve algorithms
4. **Research**: Use for mathematical exploration

## Getting Help

- Check IMPLEMENTATION_PLAN.md for architecture
- Review DESIGN_SPEC.md for technical specifications
- See code comments for algorithm details
- Open issues on GitHub (future)

## Example Configurations

### Classic Apollonian Gasket
```
Curvatures: 1, 1, 1
Depth: 8
Result: ~2,000 circles
```

### Asymmetric Packing
```
Curvatures: 1, 2, 3
Depth: 7
Result: Interesting non-uniform distribution
```

### Dense Packing
```
Curvatures: 2, 3, 6
Depth: 6
Result: Many small circles
```

## Sequence Examples

### Curvature Sequence
Starting from (1, 1):
- 1, 1, 2, 7, 26, 97, 362, 1351...
- Follows a(n) = 4a(n-1) - a(n-2)

### Generation Sequence
All circles at depth 5:
- Shows structure of gasket at specific level
- Good for analyzing growth patterns

### Residue Class (mod 24)
Curvatures ≡ 1 (mod 24):
- 1, 25, 49, 73, 97...
- Related to number-theoretic properties

## Advanced Features

### Custom Color Schemes

Edit `frontend/src/utils/colorSchemes.js`:

```javascript
export const customScheme = {
  name: 'My Scheme',
  colors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
}
```

### New Sequence Types

1. Implement detector in `backend/core/sequence_detector.py`
2. Add to sequence type enum
3. Register in API config
4. Add UI option

See IMPLEMENTATION_PLAN.md Phase 4 for details.

---

**Happy exploring! May your gaskets be plentiful and your sequences intriguing.**
