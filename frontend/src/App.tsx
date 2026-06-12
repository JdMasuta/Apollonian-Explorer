/**
 * Main App component for Apollonian Gasket Visualizer.
 *
 * Integrates the deep-zoom canvas (projection worker), WebSocket streaming,
 * viewport-driven deepening, and state management.
 */

import { useEffect, useRef, useState } from 'react';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  Stack,
  Alert,
  LinearProgress,
  Paper,
  Grid,
} from '@mui/material';
import { CanvasContainer } from './components/GasketCanvas';
import type { ViewportInfo } from './components/GasketCanvas/GasketCanvas';
import { useGasketStore } from './stores/gasketStore';
import websocketService from './services/websocketService';
import rendererClient from './renderer/rendererClient';
import { parseValue } from './components/GasketCanvas/utils';

/**
 * Resolution bound sent to the backend: circles smaller than roughly half a
 * pixel at the initial fit are pruned server-side (subtree and all), keeping
 * deep generations output-sensitive instead of exponential.
 */
function deriveMinRadius(curvatureStrings: string[], canvasPx = 900): number {
  const radii = curvatureStrings
    .map((c) => Math.abs(1 / parseValue(c)))
    .filter((r) => Number.isFinite(r) && r > 0);
  const extent = 2 * Math.max(...radii, 1);
  return extent / (2 * canvasPx);
}

/** Hard cap on how deep viewport deepening may request (wire precision). */
const DEEPEN_MIN_RADIUS_FLOOR = 1e-13;
/** Above this resolution, deepen the global cache; below it, refine locally
 * by word-replay (a global epsilon costs ~(1/eps)^1.3 circles, which is also
 * why the ensure-resolution POST clamps to this value). */
const GLOBAL_DEEPEN_MIN_RADIUS = 2e-3;
/** Depth for resolution-driven generation (resolution prunes the tree;
 * near-cusp chains need depth ~ sqrt(bend), so this must be generous). */
const DEEPEN_MAX_DEPTH = 64;
const DEEPEN_FETCH_LIMIT = 50000;
/** How many smallest on-screen circles anchor a local refinement round. */
const DEEPEN_WORD_SAMPLES = 8;
/** Local refinement rounds per settle: each round re-anchors on the now
 * smallest visible circles, so jumps of many decades converge. */
const DEEPEN_MAX_ROUNDS = 3;

function App() {
  const [curvatures, setCurvatures] = useState('1, 1, 1');
  const [maxDepth, setMaxDepth] = useState(3);

  // Gasket store state (metadata only; geometry lives in the worker)
  const circleCount = useGasketStore((state) => state.circleCount);
  const selectedCircle = useGasketStore((state) => state.selectedCircle);
  const isGenerating = useGasketStore((state) => state.isGenerating);
  const progress = useGasketStore((state) => state.progress);
  const error = useGasketStore((state) => state.error);
  const gasket = useGasketStore((state) => state.gasket);

  const setCircleCount = useGasketStore((state) => state.setCircleCount);
  const setSelectedCircle = useGasketStore((state) => state.setSelectedCircle);
  const setGenerating = useGasketStore((state) => state.setGenerating);
  const setError = useGasketStore((state) => state.setError);
  const setGasket = useGasketStore((state) => state.setGasket);
  const setCurrentGeneration = useGasketStore(
    (state) => state.setCurrentGeneration
  );
  const setProgress = useGasketStore((state) => state.setProgress);

  // Worker stats drive the circle counter.
  useEffect(() => {
    return rendererClient.onStats(setCircleCount);
  }, [setCircleCount]);

  // No eager connection: generateGasket() connects on demand (the backend
  // serves one generation per connection; see DEBUG_LOG ERR-011).
  useEffect(() => {
    return () => {
      websocketService.disconnect();
    };
  }, []);

  // Progress/generation updates are coalesced per animation frame
  // (DEBUG_LOG ERR-013).
  const pendingMetaRef = useRef<{ generation: number; progress: number } | null>(null);
  const rafRef = useRef<number | null>(null);

  const flushPending = () => {
    rafRef.current = null;
    if (pendingMetaRef.current) {
      setCurrentGeneration(pendingMetaRef.current.generation);
      setProgress(pendingMetaRef.current.progress);
      pendingMetaRef.current = null;
    }
  };

  const scheduleFlush = () => {
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(flushPending);
    }
  };

  /**
   * Handle generate button click.
   */
  const handleGenerate = async () => {
    try {
      const curvatureArray = curvatures
        .split(',')
        .map((c) => c.trim())
        .filter((c) => c.length > 0);

      if (curvatureArray.length < 3 || curvatureArray.length > 4) {
        setError('Please enter 3 or 4 curvatures');
        return;
      }

      // Clear previous data
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      pendingMetaRef.current = null;
      deepenStateRef.current = null;
      rendererClient.clear();
      setSelectedCircle(null);
      setError(null);
      setGenerating(true);
      setProgress(0);

      // Start generation (connects on demand; resolution-bounded stream)
      await websocketService.generateGasket(
        curvatureArray,
        maxDepth,
        {
          onProgress: (data) => {
            rendererClient.addCircles(data.circles);
            pendingMetaRef.current = {
              generation: data.generation,
              progress: Math.min(95, ((data.generation + 1) / (maxDepth + 1)) * 100),
            };
            scheduleFlush();
          },

          onComplete: (data) => {
            console.log('Complete:', data.total_circles);
            flushPending();
            setGenerating(false);
            setProgress(100);
            setGasket({
              id: data.gasket_id,
              initial_curvatures: curvatureArray,
              max_depth: maxDepth,
              total_circles: data.total_circles,
            });
          },

          onError: (data) => {
            console.error('Error:', data.message);
            flushPending();
            setError(data.message);
            setGenerating(false);
            setProgress(0);
          },
        },
        { minRadius: deriveMinRadius(curvatureArray) }
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setGenerating(false);
    }
  };

  /**
   * Viewport-driven deepening: when the user zooms in, fetch finer circles
   * for the visible region (REVAMP_BLUEPRINT.md Milestone 3 Stage A).
   * The POST ensures the cache covers the resolution (incremental expansion
   * server-side); the GET pulls only the visible window.
   */
  const deepenStateRef = useRef<{ minRadius: number; vp: ViewportInfo } | null>(null);
  const deepenBusyRef = useRef(false);

  const handleViewportSettle = async (vp: ViewportInfo) => {
    const state = useGasketStore.getState();
    const currentGasket = state.gasket;
    if (!currentGasket || state.isGenerating || deepenBusyRef.current) return;

    const desired = Math.max(vp.minRadius, DEEPEN_MIN_RADIUS_FLOOR);
    const last = deepenStateRef.current;
    const contained =
      last &&
      desired >= last.minRadius * 0.95 &&
      vp.minX >= last.vp.minX &&
      vp.maxX <= last.vp.maxX &&
      vp.minY >= last.vp.minY &&
      vp.maxY <= last.vp.maxY;
    if (contained) return;

    deepenBusyRef.current = true;
    try {
      // Ensure the GLOBAL cache covers a shallow base resolution (cheap:
      // bounded circle count) and resolve the gasket id without payload.
      const post = await fetch('/api/gaskets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          curvatures: currentGasket.initial_curvatures,
          max_depth: DEEPEN_MAX_DEPTH,
          min_radius: Math.max(desired, GLOBAL_DEEPEN_MIN_RADIUS),
          include_circles: false,
        }),
      });
      if (!post.ok) throw new Error(`ensure-resolution failed: ${post.status}`);
      const meta = await post.json();

      // Pull the viewport window from the global cache.
      const params = new URLSearchParams({
        min_x: String(vp.minX),
        max_x: String(vp.maxX),
        min_y: String(vp.minY),
        max_y: String(vp.maxY),
        min_radius: String(Math.max(desired, GLOBAL_DEEPEN_MIN_RADIUS)),
        limit: String(DEEPEN_FETCH_LIMIT),
      });
      const res = await fetch(`/api/gaskets/${meta.id}/circles?${params}`);
      if (!res.ok) throw new Error(`viewport query failed: ${res.status}`);
      rendererClient.addCircles((await res.json()).circles);

      // Deep zoom: refine locally around the smallest on-screen circles —
      // their group words address the exact walk-tree nodes whose subtrees
      // fill the visible gaps. Each round re-anchors, so multi-decade zoom
      // jumps converge geometrically.
      if (desired < GLOBAL_DEEPEN_MIN_RADIUS) {
        const seen = new Set<string>();
        for (let round = 0; round < DEEPEN_MAX_ROUNDS; round += 1) {
          const anchors = await rendererClient.smallestVisible(DEEPEN_WORD_SAMPLES);
          const words = [...new Set(anchors.map((a) => a.word))].filter(
            (w) => !seen.has(w)
          );
          if (words.length === 0) break;
          const fineEnough = anchors.some((a) => a.radius <= desired * 4);
          for (const word of words) {
            seen.add(word);
            const deepenRes = await fetch(`/api/gaskets/${meta.id}/deepen`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                word,
                min_radius: desired,
                max_extra_depth: 64,
              }),
            });
            if (!deepenRes.ok) continue;
            rendererClient.addCircles((await deepenRes.json()).circles);
          }
          if (fineEnough) break;
        }
      }
      deepenStateRef.current = { minRadius: desired, vp };
    } catch (err) {
      console.warn('[deepen] viewport refinement failed:', err);
    } finally {
      deepenBusyRef.current = false;
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Apollonian Gasket Visualizer
        </Typography>

        <Grid container spacing={3}>
          {/* Left Panel - Controls */}
          <Grid size={{ xs: 12, md: 4, lg: 3 }}>
            <Paper elevation={2} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Generate Gasket
              </Typography>

              <Stack spacing={2}>
                <TextField
                  label="Initial Curvatures"
                  value={curvatures}
                  onChange={(e) => setCurvatures(e.target.value)}
                  helperText="Enter 3 or 4 curvatures (e.g., 1, 1, 1)"
                  fullWidth
                  disabled={isGenerating}
                />

                <TextField
                  label="Max Depth"
                  type="number"
                  value={maxDepth}
                  onChange={(e) =>
                    setMaxDepth(Math.max(1, Math.min(15, parseInt(e.target.value) || 1)))
                  }
                  inputProps={{ min: 1, max: 15 }}
                  helperText="Recursion depth (1-15); zooming refines further"
                  fullWidth
                  disabled={isGenerating}
                />

                <Button
                  variant="contained"
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  fullWidth
                >
                  {isGenerating ? 'Generating...' : 'Generate'}
                </Button>

                {isGenerating && (
                  <Box>
                    <LinearProgress variant="determinate" value={progress} />
                    <Typography variant="caption" sx={{ mt: 0.5 }}>
                      {Math.round(progress)}% - {circleCount} circles
                    </Typography>
                  </Box>
                )}

                {error && <Alert severity="error">{error}</Alert>}

                {gasket && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Current Gasket
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Curvatures: {gasket.initial_curvatures.join(', ')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Depth: {gasket.max_depth}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Circles: {circleCount}
                    </Typography>
                  </Box>
                )}

                {selectedCircle && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Selected Circle
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Curvature: {selectedCircle.curvature}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Generation: {selectedCircle.generation}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Word: {selectedCircle.word}
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Paper>
          </Grid>

          {/* Right Panel - Canvas */}
          <Grid size={{ xs: 12, md: 8, lg: 9 }}>
            <Paper elevation={2} sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Gasket Visualization
              </Typography>

              {circleCount === 0 && !isGenerating ? (
                <Box
                  sx={{
                    height: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: '#fafafa',
                    borderRadius: 1,
                  }}
                >
                  <Typography color="text.secondary">
                    Enter curvatures and click Generate to visualize
                  </Typography>
                </Box>
              ) : (
                <CanvasContainer
                  circleCount={circleCount}
                  onCircleSelect={setSelectedCircle}
                  onViewportSettle={handleViewportSettle}
                  width={900}
                  height={600}
                  autoFit={true}
                />
              )}
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
}

export default App;
