/**
 * GasketCanvas - deep-zoom canvas for Apollonian gaskets.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * Architecture: the projection worker (via rendererClient) owns all circle
 * geometry and sends packed Float32Array frames; this component draws them
 * imperatively in ONE Konva Shape (no per-circle nodes, no React state per
 * frame). The camera is exact (BigInt rational anchor), so zoom is
 * unbounded — the old 0.1-10x clamp is gone. Selection uses a math
 * hit-test in the worker instead of scene-graph picking.
 */

import {
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
  useCallback,
} from 'react';
import { Stage, Layer, Shape } from 'react-konva';
import type Konva from 'konva';
import rendererClient, { type Frame, FRAME_STRIDE } from '../../renderer/rendererClient';
import {
  type ExactCamera,
  createCamera,
  fitToBounds,
  pan,
  serializeCamera,
  screenToWorldRelative,
  zoomAt,
} from '../../camera/exactCamera';
import { toNumber } from '../../math/rational';
import type { HitResult } from '../../workers/projection';

/** Viewport information passed to the deepening callback. */
export interface ViewportInfo {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  /** Model-space radius of ~half a pixel at the current zoom. */
  minRadius: number;
  scale: number;
}

export interface GasketCanvasProps {
  width: number;
  height: number;
  onCircleSelect: (circle: HitResult | null) => void;
  /** Fired ~350ms after the camera stops moving (deepening hook). */
  onViewportSettle?: (viewport: ViewportInfo) => void;
  autoFit?: boolean;
}

export interface GasketCanvasHandle {
  fitToCanvas: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

/** Precomputed blue→red palette over t ∈ [0,1] (64 buckets). */
const PALETTE: string[] = Array.from({ length: 64 }, (_, i) => {
  const t = i / 63;
  const r = Math.round(33 + t * (244 - 33));
  const g = Math.round(150 - t * 83);
  const b = Math.round(243 - t * (243 - 54));
  return `rgb(${r}, ${g}, ${b})`;
});

const SETTLE_MS = 350;

export const GasketCanvas = forwardRef<GasketCanvasHandle, GasketCanvasProps>(
  ({ width, height, onCircleSelect, onViewportSettle, autoFit = true }, ref) => {
    const stageRef = useRef<Konva.Stage | null>(null);
    const shapeRef = useRef<Konva.Shape | null>(null);
    const frameRef = useRef<Frame | null>(null);
    const cameraRef = useRef<ExactCamera>(createCamera());
    const userInteractedRef = useRef(false);
    const dragRef = useRef<{ x: number; y: number; moved: number } | null>(null);
    const settleTimerRef = useRef<number | null>(null);
    const sizeRef = useRef({ width, height });
    sizeRef.current = { width, height };

    const redraw = useCallback(() => {
      shapeRef.current?.getLayer()?.batchDraw();
    }, []);

    const pushCamera = useCallback(
      (camera: ExactCamera) => {
        cameraRef.current = camera;
        const { width: w, height: h } = sizeRef.current;
        rendererClient.setCamera(serializeCamera(camera), w, h);
        if (onViewportSettle) {
          if (settleTimerRef.current !== null) {
            window.clearTimeout(settleTimerRef.current);
          }
          settleTimerRef.current = window.setTimeout(() => {
            settleTimerRef.current = null;
            const cam = cameraRef.current;
            const topLeft = screenToWorldRelative(cam, 0, 0, w, h);
            const bottomRight = screenToWorldRelative(cam, w, h, w, h);
            const originX = toNumber(cam.originX);
            const originY = toNumber(cam.originY);
            onViewportSettle({
              minX: originX + topLeft.relX,
              maxX: originX + bottomRight.relX,
              minY: originY + topLeft.relY,
              maxY: originY + bottomRight.relY,
              minRadius: 0.5 / cam.scale,
              scale: cam.scale,
            });
          }, SETTLE_MS);
        }
      },
      [onViewportSettle]
    );

    const fitToCanvas = useCallback(() => {
      const { width: w, height: h } = sizeRef.current;
      rendererClient.getBounds().then((bounds) => {
        if (bounds) {
          pushCamera(fitToBounds(bounds, w, h));
        }
      });
    }, [pushCamera]);

    // Frame subscription: draw imperatively, no React state involved.
    useEffect(() => {
      const unsubscribe = rendererClient.onFrame((frame) => {
        frameRef.current = frame;
        redraw();
      });
      return unsubscribe;
    }, [redraw]);

    // Auto-fit while circles stream in, until the user takes over.
    useEffect(() => {
      const unsubscribe = rendererClient.onStats((count) => {
        if (count === 0) {
          userInteractedRef.current = false;
          frameRef.current = null;
          redraw();
          return;
        }
        if (autoFit && !userInteractedRef.current) {
          fitToCanvas();
        }
      });
      return unsubscribe;
    }, [autoFit, fitToCanvas, redraw]);

    // Re-project on resize.
    useEffect(() => {
      pushCamera(cameraRef.current);
    }, [width, height, pushCamera]);

    useImperativeHandle(ref, () => ({
      fitToCanvas: () => {
        userInteractedRef.current = false;
        fitToCanvas();
      },
      zoomIn: () => {
        userInteractedRef.current = true;
        pushCamera(zoomAt(cameraRef.current, width / 2, height / 2, 1.5, width, height));
      },
      zoomOut: () => {
        userInteractedRef.current = true;
        pushCamera(zoomAt(cameraRef.current, width / 2, height / 2, 1 / 1.5, width, height));
      },
    }));

    const handleWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const pointer = stageRef.current?.getPointerPosition();
      if (!pointer) return;
      userInteractedRef.current = true;
      const factor = e.evt.deltaY < 0 ? 1.1 : 1 / 1.1;
      pushCamera(zoomAt(cameraRef.current, pointer.x, pointer.y, factor, width, height));
    };

    const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
      const pointer = stageRef.current?.getPointerPosition();
      if (!pointer || e.evt.button !== 0) return;
      dragRef.current = { x: pointer.x, y: pointer.y, moved: 0 };
    };

    const handleMouseMove = () => {
      const drag = dragRef.current;
      const pointer = stageRef.current?.getPointerPosition();
      if (!drag || !pointer) return;
      const dx = pointer.x - drag.x;
      const dy = pointer.y - drag.y;
      if (dx === 0 && dy === 0) return;
      drag.x = pointer.x;
      drag.y = pointer.y;
      drag.moved += Math.abs(dx) + Math.abs(dy);
      if (drag.moved > 2) {
        userInteractedRef.current = true;
        pushCamera(pan(cameraRef.current, dx, dy));
      }
    };

    const handleMouseUp = async () => {
      const drag = dragRef.current;
      dragRef.current = null;
      const pointer = stageRef.current?.getPointerPosition();
      if (!drag || !pointer) return;
      if (drag.moved <= 2) {
        // A click, not a drag: math hit-test in the worker.
        const hit = await rendererClient.hitTest(pointer.x, pointer.y);
        onCircleSelect(hit);
        rendererClient.setSelected(hit ? hit.word : null);
      }
    };

    const sceneFunc = (context: Konva.Context) => {
      const frame = frameRef.current;
      const ctx = context._context as CanvasRenderingContext2D;
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#fafafa';
      ctx.fillRect(0, 0, width, height);
      if (!frame) return;

      const data = frame.positions;
      ctx.lineWidth = 1;
      // Group strokes by palette bucket to minimize state changes.
      for (let bucket = 0; bucket < PALETTE.length; bucket += 1) {
        let begun = false;
        for (let i = 0; i < frame.count; i += 1) {
          const t = data[i * FRAME_STRIDE + 3];
          if (Math.min(63, Math.round(t * 63)) !== bucket) continue;
          if (!begun) {
            ctx.beginPath();
            begun = true;
          }
          const x = data[i * FRAME_STRIDE];
          const y = data[i * FRAME_STRIDE + 1];
          const r = data[i * FRAME_STRIDE + 2];
          ctx.moveTo(x + r, y);
          ctx.arc(x, y, r, 0, Math.PI * 2);
        }
        if (begun) {
          ctx.strokeStyle = PALETTE[bucket];
          ctx.stroke();
        }
      }

      // Selection highlight ring.
      if (frame.selected) {
        const [sx, sy, sr] = frame.selected;
        ctx.beginPath();
        ctx.arc(sx, sy, Math.max(sr, 3), 0, Math.PI * 2);
        ctx.strokeStyle = '#f57c00';
        ctx.lineWidth = 2.5;
        ctx.stroke();
        ctx.fillStyle = 'rgba(255, 235, 59, 0.25)';
        ctx.fill();
      }
    };

    return (
      <Stage
        ref={stageRef}
        width={width}
        height={height}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{ background: '#fafafa', cursor: 'grab' }}
      >
        <Layer listening={false}>
          <Shape ref={shapeRef} sceneFunc={sceneFunc} />
        </Layer>
      </Stage>
    );
  }
);

GasketCanvas.displayName = 'GasketCanvas';

export default GasketCanvas;
