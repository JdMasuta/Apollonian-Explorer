/**
 * CanvasToolbar - Control buttons overlay for the canvas.
 *
 * Provides zoom in/out, reset view, and other canvas controls.
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 3 Task 5
 */

import {
  IconButton,
  Tooltip,
  Paper,
  Stack,
  Divider,
} from '@mui/material';
import {
  ZoomIn,
  ZoomOut,
  CenterFocusStrong,
  FullscreenExit,
} from '@mui/icons-material';

/**
 * Props for CanvasToolbar component.
 */
export interface CanvasToolbarProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  onFitView: () => void;
  disabled?: boolean;
}

/**
 * CanvasToolbar component.
 *
 * Overlay toolbar with canvas control buttons.
 *
 * Usage:
 * ```tsx
 * <CanvasToolbar
 *   onZoomIn={handleZoomIn}
 *   onZoomOut={handleZoomOut}
 *   onResetView={handleReset}
 *   onFitView={handleFit}
 * />
 * ```
 */
export function CanvasToolbar({
  onZoomIn,
  onZoomOut,
  onResetView,
  onFitView,
  disabled = false,
}: CanvasToolbarProps) {
  return (
    <Paper
      elevation={3}
      sx={{
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 10,
        padding: 1,
      }}
    >
      <Stack spacing={0.5}>
        <Tooltip title="Zoom In" placement="left">
          <span>
            <IconButton
              onClick={onZoomIn}
              disabled={disabled}
              size="small"
              aria-label="zoom in"
            >
              <ZoomIn />
            </IconButton>
          </span>
        </Tooltip>

        <Tooltip title="Zoom Out" placement="left">
          <span>
            <IconButton
              onClick={onZoomOut}
              disabled={disabled}
              size="small"
              aria-label="zoom out"
            >
              <ZoomOut />
            </IconButton>
          </span>
        </Tooltip>

        <Divider />

        <Tooltip title="Fit to View" placement="left">
          <span>
            <IconButton
              onClick={onFitView}
              disabled={disabled}
              size="small"
              aria-label="fit to view"
            >
              <CenterFocusStrong />
            </IconButton>
          </span>
        </Tooltip>

        <Tooltip title="Reset View" placement="left">
          <span>
            <IconButton
              onClick={onResetView}
              disabled={disabled}
              size="small"
              aria-label="reset view"
            >
              <FullscreenExit />
            </IconButton>
          </span>
        </Tooltip>
      </Stack>
    </Paper>
  );
}

export default CanvasToolbar;
