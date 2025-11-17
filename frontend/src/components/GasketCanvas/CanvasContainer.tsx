/**
 * CanvasContainer - Wrapper component for gasket canvas with controls.
 *
 * Combines GasketCanvas and CanvasToolbar with state management.
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 3
 */

import { useRef, useImperativeHandle, forwardRef } from 'react';
import { Box } from '@mui/material';
import GasketCanvas, { type GasketCanvasHandle } from './GasketCanvas';
import CanvasToolbar from './CanvasToolbar';
import type { CircleData } from '../../services/websocketService';

/**
 * Props for CanvasContainer component.
 */
export interface CanvasContainerProps {
  circles: CircleData[];
  selectedCircleId: number | null;
  onCircleSelect: (id: number | null) => void;
  width: number;
  height: number;
  autoFit?: boolean;
  showToolbar?: boolean;
}

/**
 * Canvas control methods exposed via ref.
 */
export interface CanvasContainerHandle {
  fitToView: () => void;
  resetView: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

/**
 * CanvasContainer component with integrated toolbar.
 *
 * Usage:
 * ```tsx
 * const canvasRef = useRef<CanvasContainerHandle>(null);
 *
 * <CanvasContainer
 *   ref={canvasRef}
 *   circles={circles}
 *   selectedCircleId={selectedId}
 *   onCircleSelect={setSelectedId}
 *   width={800}
 *   height={600}
 * />
 *
 * // Later:
 * canvasRef.current?.fitToView();
 * ```
 */
export const CanvasContainer = forwardRef<
  CanvasContainerHandle,
  CanvasContainerProps
>(
  (
    {
      circles,
      selectedCircleId,
      onCircleSelect,
      width,
      height,
      autoFit = true,
      showToolbar = true,
    },
    ref
  ) => {
    const canvasRef = useRef<GasketCanvasHandle>(null);

    /**
     * Programmatic zoom in.
     */
    const zoomIn = () => {
      // Trigger zoom through event simulation on canvas
      // For now, user can use mouse wheel
      console.log('Zoom in');
    };

    /**
     * Programmatic zoom out.
     */
    const zoomOut = () => {
      console.log('Zoom out');
    };

    /**
     * Fit gasket to view.
     */
    const fitToView = () => {
      // Canvas auto-fits, so we can trigger re-fit by forcing update
      canvasRef.current?.fitToCanvas();
    };

    /**
     * Reset view to initial state.
     */
    const resetView = () => {
      fitToView();
    };

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      fitToView,
      resetView,
      zoomIn,
      zoomOut,
    }));

    return (
      <Box
        sx={{
          position: 'relative',
          width,
          height,
          overflow: 'hidden',
          borderRadius: 1,
          boxShadow: 1,
        }}
      >
        <GasketCanvas
          ref={canvasRef}
          circles={circles}
          selectedCircleId={selectedCircleId}
          onCircleSelect={onCircleSelect}
          width={width}
          height={height}
          autoFit={autoFit}
        />

        {showToolbar && (
          <CanvasToolbar
            onZoomIn={zoomIn}
            onZoomOut={zoomOut}
            onResetView={resetView}
            onFitView={fitToView}
            disabled={circles.length === 0}
          />
        )}
      </Box>
    );
  }
);

CanvasContainer.displayName = 'CanvasContainer';

export default CanvasContainer;
