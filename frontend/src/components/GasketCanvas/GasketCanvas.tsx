/**
 * GasketCanvas - deep-zoom canvas for Apollonian gaskets.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stages A+B).
 *
 * Architecture: the projection worker (via rendererClient) owns all circle
 * geometry and sends packed Float32Array frames; this component hands them
 * to a WebGL2 instanced SDF renderer (Canvas2D fallback) — no per-circle
 * nodes, no React state per frame, no scene graph. The camera is exact
 * (BigInt rational anchor), so zoom is unbounded; selection uses a math
 * hit-test in the worker.
 */

import {
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
  useCallback,
} from 'react';
import rendererClient from '../../renderer/rendererClient';
import {
  createCircleRenderer,
  type CircleRenderer,
} from '../../renderer/circleRenderer';
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

const SETTLE_MS = 350;

export const GasketCanvas = forwardRef<GasketCanvasHandle, GasketCanvasProps>(
  ({ width, height, onCircleSelect, onViewportSettle, autoFit = true }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const rendererRef = useRef<CircleRenderer | null>(null);
    const cameraRef = useRef<ExactCamera>(createCamera());
    const userInteractedRef = useRef(false);
    const dragRef = useRef<{ x: number; y: number; moved: number } | null>(null);
    const settleTimerRef = useRef<number | null>(null);
    const sizeRef = useRef({ width, height });
    sizeRef.current = { width, height };

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

    // Renderer lifecycle + frame subscription (imperative, no React state).
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const renderer = createCircleRenderer(canvas);
      rendererRef.current = renderer;
      renderer.resize(
        sizeRef.current.width,
        sizeRef.current.height,
        window.devicePixelRatio || 1
      );
      const unsubscribe = rendererClient.onFrame((frame) => {
        renderer.draw(frame);
      });
      return () => {
        unsubscribe();
        renderer.dispose();
        rendererRef.current = null;
      };
    }, []);

    // Auto-fit while circles stream in, until the user takes over.
    useEffect(() => {
      const unsubscribe = rendererClient.onStats((count) => {
        if (count === 0) {
          userInteractedRef.current = false;
          rendererRef.current?.draw(null);
          return;
        }
        if (autoFit && !userInteractedRef.current) {
          fitToCanvas();
        }
      });
      return unsubscribe;
    }, [autoFit, fitToCanvas]);

    // Resize: renderer surface + re-projection.
    useEffect(() => {
      rendererRef.current?.resize(width, height, window.devicePixelRatio || 1);
      pushCamera(cameraRef.current);
    }, [width, height, pushCamera]);

    // Non-passive wheel listener (React root wheel listeners are passive, so
    // preventDefault would be ignored there).
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const px = e.clientX - rect.left;
        const py = e.clientY - rect.top;
        userInteractedRef.current = true;
        const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
        const { width: w, height: h } = sizeRef.current;
        pushCamera(zoomAt(cameraRef.current, px, py, factor, w, h));
      };
      canvas.addEventListener('wheel', onWheel, { passive: false });
      return () => canvas.removeEventListener('wheel', onWheel);
    }, [pushCamera]);

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

    const pointerPos = (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };

    const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (e.button !== 0) return;
      const p = pointerPos(e);
      dragRef.current = { x: p.x, y: p.y, moved: 0 };
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
      const drag = dragRef.current;
      if (!drag) return;
      const p = pointerPos(e);
      const dx = p.x - drag.x;
      const dy = p.y - drag.y;
      if (dx === 0 && dy === 0) return;
      drag.x = p.x;
      drag.y = p.y;
      drag.moved += Math.abs(dx) + Math.abs(dy);
      if (drag.moved > 2) {
        userInteractedRef.current = true;
        pushCamera(pan(cameraRef.current, dx, dy));
      }
    };

    const handleMouseUp = async (e: React.MouseEvent<HTMLCanvasElement>) => {
      const drag = dragRef.current;
      dragRef.current = null;
      if (!drag) return;
      if (drag.moved <= 2) {
        // A click, not a drag: math hit-test in the worker.
        const p = pointerPos(e);
        const hit = await rendererClient.hitTest(p.x, p.y);
        onCircleSelect(hit);
        rendererClient.setSelected(hit ? hit.word : null);
      }
    };

    return (
      <canvas
        ref={canvasRef}
        style={{
          width,
          height,
          background: '#fafafa',
          cursor: 'grab',
          display: 'block',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          dragRef.current = null;
        }}
      />
    );
  }
);

GasketCanvas.displayName = 'GasketCanvas';

export default GasketCanvas;
