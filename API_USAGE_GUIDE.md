# Apollonian Gasket API Usage Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-29

This document serves as the authoritative reference for the Apollonian Gasket Visualization Tool API. It ensures cohesion between frontend and backend implementations.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Headers](#authentication--headers)
3. [Data Formats](#data-formats)
4. [REST API Endpoints](#rest-api-endpoints)
5. [WebSocket API](#websocket-api)
6. [Error Handling](#error-handling)
7. [Request/Response Examples](#requestresponse-examples)
8. [Frontend Integration Patterns](#frontend-integration-patterns)

---

## Overview

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: TBD

### API Versioning
- Current version: `v1`
- All endpoints prefixed with `/api`

### Communication Protocols
- **REST API**: Standard HTTP methods for CRUD operations
- **WebSocket**: Real-time streaming for gasket generation

---

## Authentication & Headers

### Required Headers (All Requests)
```http
Content-Type: application/json
Accept: application/json
```

### Optional Headers
```http
X-Request-ID: <uuid>  # For request tracing
```

---

## Data Formats

### Rational Numbers
All curvatures, positions, and radii are represented as rational numbers.

**String Format**: `"numerator/denominator"` or `"integer"`

**Examples**:
```json
{
  "curvature": "3/2",
  "radius": "2/3",
  "center_x": "1",
  "center_y": "-1/4"
}
```

### Circle Object
```typescript
interface Circle {
  id: number;
  gasket_id: number;
  generation: number;
  curvature: string;           // Rational number
  center: {
    x: string;                 // Rational number
    y: string;                 // Rational number
  };
  radius: string;              // Rational number
  parent_ids: number[];        // IDs of parent circles
  tangent_ids: number[];       // IDs of tangent circles
  created_at: string;          // ISO 8601 timestamp
}
```

### Gasket Object
```typescript
interface Gasket {
  id: number;
  hash: string;                // SHA-256 hash of initial curvatures
  initial_curvatures: string[]; // Array of rational numbers
  num_circles: number;
  max_depth_cached: number;
  created_at: string;
  last_accessed_at: string;
  access_count: number;
}
```

### Sequence Object
```typescript
interface Sequence {
  id: number;
  gasket_id: number;
  sequence_type: 'curvature' | 'generation' | 'fibonacci' | 'residue' | 'lineage';
  parameters: Record<string, any>; // Type-specific parameters
  circle_ids: number[];            // Ordered array of circles in sequence
  hash: string;
  created_at: string;
}
```

---

## REST API Endpoints

### 1. Gaskets

#### `POST /api/gaskets`
Create a new gasket or retrieve existing from cache.

**Request Body**:
```json
{
  "curvatures": ["1", "1", "1"],
  "max_depth": 5
}
```

**Response** (201 Created or 200 OK if cached):
```json
{
  "id": 1,
  "hash": "a4f7c2...",
  "initial_curvatures": ["1", "1", "1"],
  "num_circles": 247,
  "max_depth_cached": 5,
  "circles": [
    {
      "id": 1,
      "gasket_id": 1,
      "generation": 0,
      "curvature": "1",
      "center": {"x": "0", "y": "0"},
      "radius": "1",
      "parent_ids": [],
      "tangent_ids": [2, 3],
      "created_at": "2025-10-29T10:00:00Z"
    }
    // ... more circles
  ],
  "cache_hit": false,
  "computation_time_ms": 123.45
}
```

**Error Responses**:
- `400 Bad Request`: Invalid curvatures or depth
  ```json
  {
    "detail": "Curvatures must be non-zero rational numbers",
    "error_code": "INVALID_CURVATURES"
  }
  ```
- `504 Gateway Timeout`: Generation exceeded 60 seconds
  ```json
  {
    "detail": "Gasket generation timed out. Try reducing max_depth.",
    "error_code": "GENERATION_TIMEOUT"
  }
  ```

---

#### `GET /api/gaskets/{id}`
Retrieve a specific gasket by ID.

**Path Parameters**:
- `id` (integer): Gasket ID

**Response** (200 OK):
```json
{
  "id": 1,
  "hash": "a4f7c2...",
  "initial_curvatures": ["1", "1", "1"],
  "num_circles": 247,
  "max_depth_cached": 5,
  "circles": [...],
  "created_at": "2025-10-29T10:00:00Z",
  "last_accessed_at": "2025-10-29T10:05:00Z",
  "access_count": 3
}
```

**Error Responses**:
- `404 Not Found`: Gasket does not exist
  ```json
  {
    "detail": "Gasket with id 999 not found",
    "error_code": "GASKET_NOT_FOUND"
  }
  ```

---

#### `GET /api/gaskets/{id}/circles`
Retrieve circles with optional filters.

**Path Parameters**:
- `id` (integer): Gasket ID

**Query Parameters**:
- `generation` (integer, optional): Filter by generation/depth
- `min_curvature` (string, optional): Minimum curvature (rational)
- `max_curvature` (string, optional): Maximum curvature (rational)
- `limit` (integer, optional, default=1000): Max circles to return
- `offset` (integer, optional, default=0): Pagination offset

**Example Request**:
```http
GET /api/gaskets/1/circles?generation=3&limit=50&offset=0
```

**Response** (200 OK):
```json
{
  "gasket_id": 1,
  "total_count": 156,
  "returned_count": 50,
  "offset": 0,
  "circles": [...]
}
```

---

#### `DELETE /api/gaskets/{id}`
Delete a gasket and all associated data.

**Path Parameters**:
- `id` (integer): Gasket ID

**Response** (204 No Content): Empty body

**Error Responses**:
- `404 Not Found`: Gasket does not exist

---

### 2. Sequences

#### `POST /api/sequences/detect`
Detect a sequence within a gasket.

**Request Body**:
```json
{
  "gasket_id": 1,
  "sequence_type": "curvature",
  "parameters": {
    "seed_curvatures": ["1", "3"]
  }
}
```

**Sequence Types and Parameters**:

1. **Curvature Sequence** (`curvature`)
   ```json
   {
     "seed_curvatures": ["1", "3"]  // Two initial curvatures
   }
   ```

2. **Generation-Based** (`generation`)
   ```json
   {
     "generation": 3  // All circles at depth 3
   }
   ```

3. **Fibonacci-Related** (`fibonacci`)
   ```json
   {
     "pattern": "direct"  // or "scaled", "modulo"
   }
   ```

4. **Residue Class** (`residue`)
   ```json
   {
     "modulus": 24,
     "residue": 5  // Circles where curvature ≡ 5 (mod 24)
   }
   ```

5. **Parent-Child Lineage** (`lineage`)
   ```json
   {
     "start_circle_id": 42  // Trace ancestors of this circle
   }
   ```

**Response** (201 Created or 200 OK if cached):
```json
{
  "id": 1,
  "gasket_id": 1,
  "sequence_type": "curvature",
  "parameters": {
    "seed_curvatures": ["1", "3"]
  },
  "circle_ids": [1, 5, 19, 77, 307],
  "hash": "b3d8e1...",
  "metadata": {
    "length": 5,
    "recurrence_formula": "a(n) = 4*a(n-1) - a(n-2)",
    "max_generation": 8
  },
  "cache_hit": true,
  "computation_time_ms": 5.23
}
```

**Error Responses**:
- `400 Bad Request`: Invalid sequence type or parameters
- `404 Not Found`: Gasket does not exist
- `422 Unprocessable Entity`: No sequence found matching criteria

---

#### `GET /api/sequences/{id}`
Retrieve a specific sequence by ID.

**Path Parameters**:
- `id` (integer): Sequence ID

**Response** (200 OK):
```json
{
  "id": 1,
  "gasket_id": 1,
  "sequence_type": "curvature",
  "parameters": {...},
  "circle_ids": [1, 5, 19, 77, 307],
  "circles": [
    // Full circle objects for each ID
  ],
  "hash": "b3d8e1...",
  "created_at": "2025-10-29T10:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Sequence does not exist

---

#### `GET /api/gaskets/{id}/sequences`
List all sequences for a gasket.

**Path Parameters**:
- `id` (integer): Gasket ID

**Query Parameters**:
- `type` (string, optional): Filter by sequence type

**Example Request**:
```http
GET /api/gaskets/1/sequences?type=fibonacci
```

**Response** (200 OK):
```json
{
  "gasket_id": 1,
  "count": 3,
  "sequences": [
    {
      "id": 1,
      "sequence_type": "fibonacci",
      "parameters": {...},
      "circle_count": 8,
      "created_at": "2025-10-29T10:00:00Z"
    }
    // ... more sequences
  ]
}
```

---

#### `DELETE /api/sequences/{id}`
Delete a sequence.

**Path Parameters**:
- `id` (integer): Sequence ID

**Response** (204 No Content): Empty body

---

### 3. Export

#### `POST /api/export/svg`
Generate and download SVG export.

**Request Body**:
```json
{
  "gasket_id": 1,
  "depth": 8,
  "width": 2000,
  "height": 2000,
  "highlighted_sequences": [1, 2],
  "background_color": "#FFFFFF",
  "show_non_sequence": true
}
```

**Response** (200 OK):
- **Content-Type**: `image/svg+xml`
- **Content-Disposition**: `attachment; filename="gasket_1_depth_8.svg"`
- **Body**: SVG file content

**Error Responses**:
- `404 Not Found`: Gasket or sequence not found
- `400 Bad Request`: Invalid dimensions or depth

---

#### `POST /api/export/json`
Export gasket data as JSON.

**Request Body**:
```json
{
  "gasket_id": 1,
  "include_relationships": true,
  "include_generation_tree": true
}
```

**Response** (200 OK):
- **Content-Type**: `application/json`
- **Content-Disposition**: `attachment; filename="gasket_1.json"`
- **Body**:
  ```json
  {
    "gasket": {
      "id": 1,
      "initial_curvatures": ["1", "1", "1"],
      "max_depth": 5
    },
    "circles": [...],
    "sequences": [...],
    "generation_tree": {
      "0": [1, 2, 3],
      "1": [4, 5, 6, 7],
      // ... by generation
    },
    "metadata": {
      "total_circles": 247,
      "exported_at": "2025-10-29T10:00:00Z"
    }
  }
  ```

---

#### `POST /api/export/csv`
Export circles as CSV.

**Request Body**:
```json
{
  "gasket_id": 1,
  "include_columns": ["id", "generation", "curvature", "center_x", "center_y", "radius", "parent_ids"]
}
```

**Response** (200 OK):
- **Content-Type**: `text/csv`
- **Content-Disposition**: `attachment; filename="gasket_1_circles.csv"`
- **Body**:
  ```csv
  id,generation,curvature,center_x,center_y,radius,parent_ids
  1,0,1,0,0,1,[]
  2,0,1,2,0,1,[]
  3,1,3/2,1,1/2,2/3,"[1,2]"
  ...
  ```

---

### 4. Configuration

#### `GET /api/config/sequence-types`
List available sequence types and their parameter schemas.

**Response** (200 OK):
```json
{
  "sequence_types": [
    {
      "type": "curvature",
      "name": "Curvature Sequence",
      "description": "Follows recurrence a(n) = 4*a(n-1) - a(n-2)",
      "parameters": {
        "seed_curvatures": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 2,
          "maxItems": 2,
          "description": "Two initial curvature values"
        }
      }
    },
    {
      "type": "generation",
      "name": "Generation-Based",
      "description": "All circles at a specific depth level",
      "parameters": {
        "generation": {
          "type": "integer",
          "minimum": 0,
          "description": "Depth level"
        }
      }
    }
    // ... more types
  ]
}
```

---

#### `GET /api/config/color-schemes`
List preset color schemes for highlighting.

**Response** (200 OK):
```json
{
  "default": "#E3DE9C",
  "presets": [
    {"name": "Purple", "color": "#9E59D9"},
    {"name": "Pink", "color": "#D874A6"},
    {"name": "Orange", "color": "#DCA26D"},
    {"name": "Green", "color": "#8FC986"},
    {"name": "Blue", "color": "#609BD8"}
  ]
}
```

---

#### `GET /api/cache/stats`
Retrieve cache performance statistics.

**Response** (200 OK):
```json
{
  "total_gaskets": 42,
  "total_sequences": 156,
  "cache_hits": 834,
  "cache_misses": 198,
  "hit_ratio": 0.808,
  "total_computation_time_saved_ms": 45678.9,
  "disk_usage_mb": 12.5
}
```

---

## WebSocket API

### Connection Endpoint
```
ws://localhost:8000/ws/gasket/generate
```

### Protocol

#### 1. Client Initiates Generation

**Client → Server**:
```json
{
  "action": "start",
  "curvatures": ["1", "1", "1"],
  "max_depth": 10
}
```

#### 2. Server Streams Progress

**Server → Client** (multiple messages):
```json
{
  "type": "progress",
  "generation": 3,
  "circles_count": 156,
  "circles": [
    {
      "id": 157,
      "gasket_id": 1,
      "generation": 3,
      "curvature": "3/2",
      "center": {"x": "1/4", "y": "1/3"},
      "radius": "2/3",
      "parent_ids": [42, 58, 91],
      "tangent_ids": [42, 58, 91],
      "created_at": "2025-10-29T10:00:03.456Z"
    }
    // ... batch of circles (typically 10-50 per message)
  ]
}
```

**Streaming Frequency**: Every ~50ms or every 20 circles, whichever comes first.

#### 3. Server Signals Completion

**Server → Client**:
```json
{
  "type": "complete",
  "gasket_id": 1,
  "total_circles": 12487,
  "total_generations": 10,
  "computation_time_ms": 5234.6,
  "hash": "a4f7c2..."
}
```

#### 4. Error Handling

**Server → Client** (on error):
```json
{
  "type": "error",
  "error_code": "GENERATION_FAILED",
  "message": "Numerical instability detected at generation 9",
  "details": {
    "last_successful_generation": 8,
    "circles_generated": 8765
  }
}
```

After sending an error, the server closes the WebSocket connection.

#### 5. Client Cancellation

**Client → Server**:
```json
{
  "action": "cancel"
}
```

**Server → Client** (acknowledgment):
```json
{
  "type": "cancelled",
  "circles_generated": 5432,
  "gasket_id": 1
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-10-29T10:00:00Z",
  "path": "/api/gaskets/1",
  "request_id": "uuid-here"
}
```

### HTTP Status Codes

| Code | Meaning | Common Scenarios |
|------|---------|------------------|
| 200 | OK | Successful GET, cached resource |
| 201 | Created | New resource created |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, validation errors |
| 404 | Not Found | Resource does not exist |
| 422 | Unprocessable Entity | Valid input but logically impossible (e.g., no sequence found) |
| 500 | Internal Server Error | Unexpected backend error |
| 504 | Gateway Timeout | Operation exceeded time limit |

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CURVATURES` | 400 | Curvatures are not valid rational numbers |
| `INVALID_DEPTH` | 400 | Depth must be between 1 and 15 |
| `GASKET_NOT_FOUND` | 404 | Gasket ID does not exist |
| `SEQUENCE_NOT_FOUND` | 404 | Sequence ID does not exist |
| `NO_SEQUENCE_DETECTED` | 422 | No sequence matches the criteria |
| `GENERATION_TIMEOUT` | 504 | Gasket generation exceeded 60 seconds |
| `GENERATION_FAILED` | 500 | Unexpected error during generation |
| `DATABASE_ERROR` | 500 | Database operation failed |

---

## Request/Response Examples

### Example 1: Complete Workflow - Generate and Analyze

#### Step 1: Generate Gasket
```bash
curl -X POST http://localhost:8000/api/gaskets \
  -H "Content-Type: application/json" \
  -d '{
    "curvatures": ["-1", "2", "2", "3"],
    "max_depth": 7
  }'
```

**Response**:
```json
{
  "id": 5,
  "hash": "f3a9d2...",
  "initial_curvatures": ["-1", "2", "2", "3"],
  "num_circles": 1247,
  "max_depth_cached": 7,
  "circles": [...],
  "cache_hit": false,
  "computation_time_ms": 1523.4
}
```

#### Step 2: Detect Curvature Sequence
```bash
curl -X POST http://localhost:8000/api/sequences/detect \
  -H "Content-Type: application/json" \
  -d '{
    "gasket_id": 5,
    "sequence_type": "curvature",
    "parameters": {
      "seed_curvatures": ["2", "3"]
    }
  }'
```

**Response**:
```json
{
  "id": 7,
  "gasket_id": 5,
  "sequence_type": "curvature",
  "parameters": {"seed_curvatures": ["2", "3"]},
  "circle_ids": [2, 4, 15, 58, 227],
  "hash": "e4b7c3...",
  "metadata": {
    "length": 5,
    "recurrence_formula": "a(n) = 4*a(n-1) - a(n-2)"
  },
  "cache_hit": false,
  "computation_time_ms": 8.7
}
```

#### Step 3: Export as SVG
```bash
curl -X POST http://localhost:8000/api/export/svg \
  -H "Content-Type: application/json" \
  -d '{
    "gasket_id": 5,
    "depth": 7,
    "width": 3000,
    "height": 3000,
    "highlighted_sequences": [7]
  }' \
  --output gasket_5.svg
```

---

### Example 2: WebSocket Real-Time Generation

```javascript
// Frontend JavaScript
const ws = new WebSocket('ws://localhost:8000/ws/gasket/generate');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'start',
    curvatures: ['1', '1', '1'],
    max_depth: 10
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    console.log(`Generation ${data.generation}: ${data.circles_count} circles`);
    // Add circles to state/store
    data.circles.forEach(circle => addCircleToCanvas(circle));
  }
  else if (data.type === 'complete') {
    console.log(`Complete! Gasket ID: ${data.gasket_id}`);
    console.log(`Total circles: ${data.total_circles}`);
    console.log(`Time: ${data.computation_time_ms}ms`);
    ws.close();
  }
  else if (data.type === 'error') {
    console.error(`Error: ${data.message}`);
    showErrorNotification(data.message);
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

---

## Frontend Integration Patterns

### Pattern 1: Zustand Store Integration

```javascript
// gasketStore.js
import create from 'zustand';
import axios from 'axios';

const useGasketStore = create((set, get) => ({
  currentGasket: null,
  circles: [],
  isGenerating: false,
  progress: 0,

  generateGasket: async (curvatures, maxDepth) => {
    set({ isGenerating: true, progress: 0 });

    try {
      const response = await axios.post('/api/gaskets', {
        curvatures,
        max_depth: maxDepth
      });

      set({
        currentGasket: response.data,
        circles: response.data.circles,
        isGenerating: false,
        progress: 100
      });
    } catch (error) {
      set({ isGenerating: false });
      throw error;
    }
  },

  addCircles: (newCircles) => {
    set(state => ({
      circles: [...state.circles, ...newCircles]
    }));
  },

  updateProgress: (generation, totalGenerations) => {
    set({ progress: (generation / totalGenerations) * 100 });
  }
}));
```

### Pattern 2: WebSocket Hook

```javascript
// useGasketGeneration.js
import { useEffect, useRef } from 'react';
import useGasketStore from '../stores/gasketStore';
import useUIStore from '../stores/uiStore';

export const useGasketGeneration = () => {
  const wsRef = useRef(null);
  const addCircles = useGasketStore(state => state.addCircles);
  const updateProgress = useGasketStore(state => state.updateProgress);
  const showNotification = useUIStore(state => state.showNotification);

  const startGeneration = (curvatures, maxDepth) => {
    const ws = new WebSocket('ws://localhost:8000/ws/gasket/generate');
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'start',
        curvatures,
        max_depth: maxDepth
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'progress':
          addCircles(data.circles);
          updateProgress(data.generation, maxDepth);
          break;

        case 'complete':
          showNotification('Gasket generation complete!', 'success');
          ws.close();
          break;

        case 'error':
          showNotification(data.message, 'error');
          ws.close();
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      showNotification('Connection error', 'error');
    };
  };

  const cancelGeneration = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: 'cancel' }));
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { startGeneration, cancelGeneration };
};
```

### Pattern 3: API Service Layer

```javascript
// gasketService.js
import axios from './api';

export const gasketService = {
  async create(curvatures, maxDepth) {
    const response = await axios.post('/api/gaskets', {
      curvatures,
      max_depth: maxDepth
    });
    return response.data;
  },

  async getById(id) {
    const response = await axios.get(`/api/gaskets/${id}`);
    return response.data;
  },

  async getCircles(id, filters = {}) {
    const response = await axios.get(`/api/gaskets/${id}/circles`, {
      params: filters
    });
    return response.data;
  },

  async delete(id) {
    await axios.delete(`/api/gaskets/${id}`);
  }
};

// sequenceService.js
export const sequenceService = {
  async detect(gasketId, sequenceType, parameters) {
    const response = await axios.post('/api/sequences/detect', {
      gasket_id: gasketId,
      sequence_type: sequenceType,
      parameters
    });
    return response.data;
  },

  async getById(id) {
    const response = await axios.get(`/api/sequences/${id}`);
    return response.data;
  },

  async list(gasketId, filters = {}) {
    const response = await axios.get(`/api/gaskets/${gasketId}/sequences`, {
      params: filters
    });
    return response.data;
  },

  async delete(id) {
    await axios.delete(`/api/sequences/${id}`);
  }
};

// exportService.js
export const exportService = {
  async exportSVG(options) {
    const response = await axios.post('/api/export/svg', options, {
      responseType: 'blob'
    });

    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `gasket_${options.gasket_id}.svg`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },

  async exportJSON(gasketId, options = {}) {
    const response = await axios.post('/api/export/json', {
      gasket_id: gasketId,
      ...options
    }, {
      responseType: 'blob'
    });

    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `gasket_${gasketId}.json`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },

  async exportCSV(gasketId, columns = []) {
    const response = await axios.post('/api/export/csv', {
      gasket_id: gasketId,
      include_columns: columns
    }, {
      responseType: 'blob'
    });

    // Trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `gasket_${gasketId}_circles.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
};
```

---

## Rate Limiting & Performance

### Current Limits (Subject to Change)
- **REST API**: No rate limiting for single-user deployment
- **WebSocket**: 1 concurrent generation per connection
- **Max Gasket Depth**: 15 (configurable via environment)

### Performance Expectations

| Operation | Target Time | Notes |
|-----------|-------------|-------|
| Depth 5 gasket | < 200ms | ~200-300 circles |
| Depth 7 gasket | < 500ms | ~1000 circles |
| Depth 10 gasket | < 5s | ~10,000 circles |
| Sequence detection | < 1s | Any type |
| SVG export (depth 8) | < 3s | 2000x2000px |

---

## Versioning & Changelog

### v1.0.0 (Current)
- Initial API design
- All core endpoints implemented
- WebSocket streaming support
- Five sequence types

### Upcoming (v1.1.0)
- Batch sequence detection
- Custom sequence definitions
- Enhanced caching with Redis support

---

## Support & Feedback

For issues or questions about this API:
- Open an issue in the project repository
- Refer to `DESIGN_SPEC.md` for implementation details
- Check `IMPLEMENTATION_PLAN.md` for development roadmap

---

**Document End**
