/**
 * Main-thread client for the projection worker.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * Owns the Worker, coalesces camera updates (latest-wins; at most one frame
 * request in flight), and exposes a small async API. Bulk geometry never
 * touches React state: components subscribe to frames and draw them
 * imperatively.
 */

import type { CameraMessage } from '../camera/exactCamera';
import type { CircleData } from '../services/websocketService';
import type { HitResult, Bounds } from '../workers/projection';
import { FRAME_STRIDE } from '../workers/projection';

export { FRAME_STRIDE };

export interface Frame {
  positions: Float32Array; // packed [sx, sy, rPx, colorT]
  count: number;
  selected: Float32Array | null; // [sx, sy, rPx] of the selected circle
}

type FrameListener = (frame: Frame) => void;
type StatsListener = (count: number) => void;

class RendererClient {
  private worker: Worker | null = null;
  private frameListeners = new Set<FrameListener>();
  private statsListeners = new Set<StatsListener>();
  private pending = new Map<number, (value: unknown) => void>();
  private requestCounter = 0;
  private frameCounter = 0;
  private frameInFlight = false;
  private queuedCamera: { camera: CameraMessage; width: number; height: number } | null =
    null;

  private ensureWorker(): Worker {
    if (!this.worker) {
      this.worker = new Worker(new URL('../workers/mathWorker.ts', import.meta.url), {
        type: 'module',
      });
      this.worker.onmessage = (event) => this.handleMessage(event.data);
    }
    return this.worker;
  }

  private handleMessage(message: {
    type: string;
    [key: string]: unknown;
  }): void {
    switch (message.type) {
      case 'frame': {
        this.frameInFlight = false;
        const frame: Frame = {
          positions: new Float32Array(message.buffer as ArrayBuffer),
          count: message.count as number,
          selected: (message.selected as Float32Array | null) ?? null,
        };
        for (const listener of this.frameListeners) {
          listener(frame);
        }
        // A camera update arrived while this frame was rendering: send it now.
        if (this.queuedCamera) {
          const queued = this.queuedCamera;
          this.queuedCamera = null;
          this.sendCamera(queued.camera, queued.width, queued.height);
        }
        break;
      }
      case 'stats': {
        for (const listener of this.statsListeners) {
          listener(message.count as number);
        }
        break;
      }
      case 'hitResult':
      case 'smallestResult':
      case 'boundsResult': {
        const requestId = message.requestId as number;
        const resolve = this.pending.get(requestId);
        if (resolve) {
          this.pending.delete(requestId);
          resolve(message.circle ?? message.circles ?? message.bounds ?? null);
        }
        break;
      }
    }
  }

  onFrame(listener: FrameListener): () => void {
    this.frameListeners.add(listener);
    return () => this.frameListeners.delete(listener);
  }

  onStats(listener: StatsListener): () => void {
    this.statsListeners.add(listener);
    return () => this.statsListeners.delete(listener);
  }

  addCircles(circles: CircleData[]): void {
    this.ensureWorker().postMessage({ type: 'add', circles });
  }

  clear(): void {
    this.ensureWorker().postMessage({ type: 'clear' });
  }

  setSelected(word: string | null): void {
    this.ensureWorker().postMessage({ type: 'select', word });
  }

  /** Latest-wins camera update; coalesced while a frame is in flight. */
  setCamera(camera: CameraMessage, width: number, height: number): void {
    if (this.frameInFlight) {
      this.queuedCamera = { camera, width, height };
      return;
    }
    this.sendCamera(camera, width, height);
  }

  private sendCamera(camera: CameraMessage, width: number, height: number): void {
    this.frameCounter += 1;
    this.frameInFlight = true;
    this.ensureWorker().postMessage({
      type: 'camera',
      camera,
      width,
      height,
      frameId: this.frameCounter,
    });
  }

  hitTest(sx: number, sy: number): Promise<HitResult | null> {
    return this.request<HitResult | null>((requestId) => ({
      type: 'hitTest',
      sx,
      sy,
      requestId,
    }));
  }

  /** Words of the N smallest circles intersecting the current viewport. */
  smallestVisible(limit: number): Promise<{ word: string; radius: number }[]> {
    return this.request<{ word: string; radius: number }[]>((requestId) => ({
      type: 'smallestVisible',
      limit,
      requestId,
    }));
  }

  getBounds(): Promise<Bounds | null> {
    return this.request<Bounds | null>((requestId) => ({ type: 'bounds', requestId }));
  }

  private request<T>(build: (requestId: number) => object): Promise<T> {
    this.requestCounter += 1;
    const requestId = this.requestCounter;
    return new Promise<T>((resolve) => {
      this.pending.set(requestId, resolve as (value: unknown) => void);
      this.ensureWorker().postMessage(build(requestId));
    });
  }
}

/** Singleton: one worker for the app. */
const rendererClient = new RendererClient();
export default rendererClient;
