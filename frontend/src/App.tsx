/**
 * Main App component for Apollonian Gasket Visualizer.
 *
 * Integrates canvas, WebSocket streaming, and state management.
 */

import { useEffect, useState } from 'react';
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
import websocketService from './services/websocketService';

function App() {
  const [curvatures, setCurvatures] = useState('1, 1, 1');
  const [maxDepth, setMaxDepth] = useState(3);
  const [isConnected, setIsConnected] = useState(false);

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

  // Connect to WebSocket on mount
  useEffect(() => {
    const connect = async () => {
      try {
        await websocketService.connect();
        setIsConnected(true);
        setError(null);
      } catch (err) {
        setError('Failed to connect to server');
        setIsConnected(false);
      }
    };

    connect();

    return () => {
      websocketService.disconnect();
    };
  }, []);

  /**
   * Handle generate button click.
   */
  const handleGenerate = async () => {
    if (!isConnected) {
      setError('Not connected to server');
      return;
    }

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
      clearCircles();
      setError(null);
      setGenerating(true);
      setProgress(0);

      // Start generation
      websocketService.generateGasket(curvatureArray, maxDepth, {
        onProgress: (data) => {
          console.log('Progress:', data.generation, data.circles_count);
          addCircles(data.circles);
          setCurrentGeneration(data.generation);

          // Estimate progress (rough approximation)
          const progressPercent = Math.min(
            95,
            ((data.generation + 1) / (maxDepth + 1)) * 100
          );
          setProgress(progressPercent);
        },

        onComplete: (data) => {
          console.log('Complete:', data.total_circles);
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
          setError(data.message);
          setGenerating(false);
          setProgress(0);
        },
      });
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
                  disabled={!isConnected || isGenerating}
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

                {!isConnected && (
                  <Alert severity="warning">Not connected to server</Alert>
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
