/**
 * CanvasContainer - wrapper for the deep-zoom gasket canvas with toolbar.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A). Circle geometry no
 * longer flows through props: the canvas subscribes to the projection
 * worker via rendererClient.
 */

import { useRef, useImperativeHandle, forwardRef } from 'react';
import { Box } from '@mui/material';
import GasketCanvas, {
  type GasketCanvasHandle,
  type ViewportInfo,
} from './GasketCanvas';
import CanvasToolbar from './CanvasToolbar';
import type { HitResult } from '../../workers/projection';

export interface CanvasContainerProps {
  circleCount: number;
  onCircleSelect: (circle: HitResult | null) => void;
  onViewportSettle?: (viewport: ViewportInfo) => void;
  width: number;
  height: number;
  autoFit?: boolean;
  showToolbar?: boolean;
}

export interface CanvasContainerHandle {
  fitToView: () => void;
  resetView: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

export const CanvasContainer = forwardRef<
  CanvasContainerHandle,
  CanvasContainerProps
>(
  (
    {
      circleCount,
      onCircleSelect,
      onViewportSettle,
      width,
      height,
      autoFit = true,
      showToolbar = true,
    },
    ref
  ) => {
    const canvasRef = useRef<GasketCanvasHandle>(null);

    const zoomIn = () => canvasRef.current?.zoomIn();
    const zoomOut = () => canvasRef.current?.zoomOut();
    const fitToView = () => canvasRef.current?.fitToCanvas();
    const resetView = () => fitToView();

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
          onCircleSelect={onCircleSelect}
          onViewportSettle={onViewportSettle}
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
            disabled={circleCount === 0}
          />
        )}
      </Box>
    );
  }
);

CanvasContainer.displayName = 'CanvasContainer';

export default CanvasContainer;
