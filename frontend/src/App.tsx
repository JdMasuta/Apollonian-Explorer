/**
 * Main App component for Apollonian Gasket Visualizer.
 *
 * Integrates canvas, WebSocket streaming, and state management.
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
import { useGasketStore } from './stores/gasketStore';
import websocketService, {
  type CircleData,
} from './services/websocketService';
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

function App() {
  const [curvatures, setCurvatures] = useState('1, 1, 1');
  const [maxDepth, setMaxDepth] = useState(3);

  // Gasket store state
  const circles = useGasketStore((state) => state.circles);
  const selectedCircleId = useGasketStore((state) => state.selectedCircleId);
  const isGenerating = useGasketStore((state) => state.isGenerating);
  const progress = useGasketStore((state) => state.progress);
  const error = useGasketStore((state) => state.error);
  const gasket = useGasketStore((state) => state.gasket);

  const setSelectedCircle = useGasketStore((state) => state.setSelectedCircle);
  const setGenerating = useGasketStore((state) => state.setGenerating);
  const clearCircles = useGasketStore((state) => state.clearCircles);
  const addCircles = useGasketStore((state) => state.addCircles);
  const setError = useGasketStore((state) => state.setError);
  const setGasket = useGasketStore((state) => state.setGasket);
  const setCurrentGeneration = useGasketStore(
    (state) => state.setCurrentGeneration
  );
  const setProgress = useGasketStore((state) => state.setProgress);

  // No eager connection: generateGasket() connects on demand (the backend
  // serves one generation per connection). Connecting in a mount effect
  // also produced StrictMode console noise (DEBUG_LOG ERR-011).
  useEffect(() => {
    return () => {
      websocketService.disconnect();
    };
  }, []);

  // Incoming circles are buffered and flushed to the store at most once per
  // animation frame. Per-message store updates flooded React with nested
  // update cascades ("Maximum update depth exceeded", DEBUG_LOG ERR-013).
  const pendingCirclesRef = useRef<CircleData[]>([]);
  const pendingMetaRef = useRef<{ generation: number; progress: number } | null>(null);
  const rafRef = useRef<number | null>(null);

  const flushPending = () => {
    rafRef.current = null;
    if (pendingCirclesRef.current.length > 0) {
      const batch = pendingCirclesRef.current;
      pendingCirclesRef.current = [];
      addCircles(batch);
    }
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
      // Parse curvatures
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
      pendingCirclesRef.current = [];
      pendingMetaRef.current = null;
      clearCircles();
      setError(null);
      setGenerating(true);
      setProgress(0);

      // Start generation (connects on demand; resolution-bounded stream)
      await websocketService.generateGasket(
        curvatureArray,
        maxDepth,
        {
          onProgress: (data) => {
            pendingCirclesRef.current.push(...data.circles);
            pendingMetaRef.current = {
              generation: data.generation,
              progress: Math.min(95, ((data.generation + 1) / (maxDepth + 1)) * 100),
            };
            scheduleFlush();
          },

          onComplete: (data) => {
            console.log('Complete:', data.total_circles);
            if (rafRef.current !== null) {
              cancelAnimationFrame(rafRef.current);
            }
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
            if (rafRef.current !== null) {
              cancelAnimationFrame(rafRef.current);
            }
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
                  helperText="Recursion depth (1-15)"
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
                      {Math.round(progress)}% - {circles.length} circles
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
                      Circles: {gasket.total_circles}
                    </Typography>
                  </Box>
                )}

                {selectedCircleId !== null && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Selected Circle
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      ID: {selectedCircleId}
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

              {circles.length === 0 ? (
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
                  circles={circles}
                  selectedCircleId={selectedCircleId}
                  onCircleSelect={setSelectedCircle}
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
