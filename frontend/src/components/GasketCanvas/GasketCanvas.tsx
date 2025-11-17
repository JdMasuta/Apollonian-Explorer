/**
 * GasketCanvas - Interactive canvas for visualizing Apollonian gaskets.
 *
 * Features:
 * - Circle rendering with react-konva
 * - Pan and zoom functionality
 * - Circle selection
 * - Auto-fit to canvas
 * - Generation-based coloring
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 3
 */

import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';
import { Stage, Layer, Circle as KonvaCircle } from 'react-konva';
import type { CircleData } from '../../services/websocketService';
import {
  parseValue,
  curvatureToRadius,
  calculateBoundingBox,
  calculateFitTransform,
  getCircleColor,
  getStrokeWidth,
} from './utils';

/**
 * Props for GasketCanvas component.
 */
export interface GasketCanvasProps {
  circles: CircleData[];
  selectedCircleId: number | null;
  onCircleSelect: (id: number | null) => void;
  width: number;
  height: number;
  autoFit?: boolean; // Auto-fit on circles change
}

/**
 * Transform state for pan/zoom.
 */
interface TransformState {
  scale: number;
  x: number;
  y: number;
}

/**
 * Methods exposed via ref.
 */
export interface GasketCanvasHandle {
  fitToCanvas: () => void;
}

/**
 * GasketCanvas component.
 *
 * Renders Apollonian gasket circles with interactive pan/zoom.
 *
 * Usage:
 * ```tsx
 * <GasketCanvas
 *   circles={circles}
 *   selectedCircleId={selectedId}
 *   onCircleSelect={setSelectedId}
 *   width={800}
 *   height={600}
 *   autoFit={true}
 * />
 * ```
 */
export const GasketCanvas = forwardRef<GasketCanvasHandle, GasketCanvasProps>(
  (
    {
      circles,
      selectedCircleId,
      onCircleSelect,
      width,
      height,
      autoFit = true,
    },
    ref
  ) => {
  const [transform, setTransform] = useState<TransformState>({
    scale: 1,
    x: 0,
    y: 0,
  });

  const stageRef = useRef<any>(null);
  const [maxGeneration, setMaxGeneration] = useState(0);

  // Calculate max generation for coloring
  useEffect(() => {
    if (circles.length > 0) {
      const max = Math.max(...circles.map((c) => c.generation));
      setMaxGeneration(max);
    }
  }, [circles]);

  // Auto-fit when circles change
  useEffect(() => {
    if (autoFit && circles.length > 0) {
      fitToCanvas();
    }
  }, [circles, autoFit, width, height]);

  /**
   * Fit gasket to canvas with padding.
   */
  const fitToCanvas = () => {
    if (circles.length === 0) return;

    const bbox = calculateBoundingBox(circles);
    const fit = calculateFitTransform(bbox, width, height, 0.1);

    setTransform({
      scale: fit.scale,
      x: fit.x,
      y: fit.y,
    });
  };

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    fitToCanvas,
  }));

  /**
   * Handle wheel zoom.
   */
  const handleWheel = (e: any) => {
    e.evt.preventDefault();

    const stage = stageRef.current;
    if (!stage) return;

    const oldScale = transform.scale;
    const pointer = stage.getPointerPosition();

    // Mouse wheel delta (negative = zoom in, positive = zoom out)
    const delta = e.evt.deltaY;
    const scaleBy = 1.1;

    // Calculate new scale
    const newScale = delta < 0 ? oldScale * scaleBy : oldScale / scaleBy;

    // Limit scale (0.1x to 10x)
    const boundedScale = Math.max(0.1, Math.min(10, newScale));

    // Calculate new position to zoom toward mouse pointer
    const mousePointTo = {
      x: (pointer.x - transform.x) / oldScale,
      y: (pointer.y - transform.y) / oldScale,
    };

    const newX = pointer.x - mousePointTo.x * boundedScale;
    const newY = pointer.y - mousePointTo.y * boundedScale;

    setTransform({
      scale: boundedScale,
      x: newX,
      y: newY,
    });
  };

  /**
   * Handle circle click.
   */
  const handleCircleClick = (circle: CircleData) => {
    if (circle.id !== undefined) {
      onCircleSelect(circle.id);
    }
  };

  /**
   * Handle canvas background click (deselect).
   */
  const handleStageClick = (e: any) => {
    // Only deselect if clicking on the stage itself (not a shape)
    if (e.target === e.target.getStage()) {
      onCircleSelect(null);
    }
  };

  return (
    <Stage
      ref={stageRef}
      width={width}
      height={height}
      onWheel={handleWheel}
      onClick={handleStageClick}
      draggable
      scaleX={transform.scale}
      scaleY={transform.scale}
      x={transform.x}
      y={transform.y}
      style={{ background: '#fafafa', cursor: 'grab' }}
    >
      <Layer>
        {circles.map((circle, index) => {
          const x = parseValue(circle.center.x);
          const y = parseValue(circle.center.y);
          const radius = curvatureToRadius(circle.curvature);
          const isSelected = circle.id === selectedCircleId;

          return (
            <KonvaCircle
              key={circle.id ?? `circle-${index}`}
              x={x}
              y={y}
              radius={radius}
              fill={
                isSelected
                  ? 'rgba(255, 235, 59, 0.3)' // Yellow highlight
                  : 'rgba(255, 255, 255, 0.8)'
              }
              stroke={
                isSelected
                  ? '#f57c00' // Orange stroke for selection
                  : getCircleColor(circle.generation, maxGeneration)
              }
              strokeWidth={getStrokeWidth(radius, isSelected)}
              onClick={() => handleCircleClick(circle)}
              onTap={() => handleCircleClick(circle)}
              onMouseEnter={(e) => {
                const container = e.target.getStage()?.container();
                if (container) {
                  container.style.cursor = 'pointer';
                }
              }}
              onMouseLeave={(e) => {
                const container = e.target.getStage()?.container();
                if (container) {
                  container.style.cursor = 'grab';
                }
              }}
            />
          );
        })}
      </Layer>
    </Stage>
  );
});

GasketCanvas.displayName = 'GasketCanvas';

export default GasketCanvas;
