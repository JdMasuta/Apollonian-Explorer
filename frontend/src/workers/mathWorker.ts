/**
 * Math worker: thin message shell around ProjectionIndex.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * Owns the bulk circle geometry off the main thread: parsing of exact wire
 * strings, exact->camera-relative conversion, viewport culling, frame
 * packing, hit-testing and bounds. The main thread (rendererClient.ts) only
 * ever sees small messages and transferable Float32Array frames.
 */

import { ProjectionIndex } from './projection';
import type { CameraMessage } from '../camera/exactCamera';
import type { CircleData } from '../services/websocketService';

export type WorkerRequest =
  | { type: 'add'; circles: CircleData[] }
  | { type: 'clear' }
  | { type: 'select'; word: string | null }
  | {
      type: 'camera';
      camera: CameraMessage;
      width: number;
      height: number;
      frameId: number;
    }
  | { type: 'hitTest'; sx: number; sy: number; requestId: number }
  | { type: 'smallestVisible'; limit: number; requestId: number }
  | { type: 'bounds'; requestId: number };

export type WorkerResponse =
  | { type: 'stats'; count: number }
  | {
      type: 'frame';
      frameId: number;
      buffer: ArrayBuffer;
      count: number;
      selected: Float32Array | null;
    }
  | { type: 'hitResult'; requestId: number; circle: ReturnType<ProjectionIndex['hitTest']> }
  | {
      type: 'smallestResult';
      requestId: number;
      circles: ReturnType<ProjectionIndex['smallestVisible']>;
    }
  | { type: 'boundsResult'; requestId: number; bounds: ReturnType<ProjectionIndex['getBounds']> };

const index = new ProjectionIndex();
let lastCamera: { camera: CameraMessage; width: number; height: number } | null = null;
let selectedWord: string | null = null;
let frameCounter = 0;

const scope = self as unknown as {
  postMessage: (message: WorkerResponse, transfer?: Transferable[]) => void;
  onmessage: ((event: MessageEvent<WorkerRequest>) => void) | null;
};

function emitFrame(frameId: number): void {
  if (!lastCamera) return;
  const { buffer, count, selected } = index.project(
    lastCamera.camera,
    lastCamera.width,
    lastCamera.height,
    selectedWord
  );
  const transferable = buffer.buffer as ArrayBuffer;
  scope.postMessage(
    { type: 'frame', frameId, buffer: transferable, count, selected },
    [transferable]
  );
}

scope.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  switch (message.type) {
    case 'add': {
      index.add(message.circles);
      scope.postMessage({ type: 'stats', count: index.count });
      // Re-render with the new data under the current camera.
      frameCounter += 1;
      emitFrame(frameCounter);
      break;
    }
    case 'clear': {
      index.clear();
      selectedWord = null;
      scope.postMessage({ type: 'stats', count: 0 });
      frameCounter += 1;
      emitFrame(frameCounter);
      break;
    }
    case 'select': {
      selectedWord = message.word;
      frameCounter += 1;
      emitFrame(frameCounter);
      break;
    }
    case 'camera': {
      lastCamera = {
        camera: message.camera,
        width: message.width,
        height: message.height,
      };
      emitFrame(message.frameId);
      break;
    }
    case 'hitTest': {
      const circle = lastCamera
        ? index.hitTest(
            lastCamera.camera,
            message.sx,
            message.sy,
            lastCamera.width,
            lastCamera.height
          )
        : null;
      scope.postMessage({ type: 'hitResult', requestId: message.requestId, circle });
      break;
    }
    case 'smallestVisible': {
      const circles = lastCamera
        ? index.smallestVisible(
            lastCamera.camera,
            lastCamera.width,
            lastCamera.height,
            message.limit
          )
        : [];
      scope.postMessage({
        type: 'smallestResult',
        requestId: message.requestId,
        circles,
      });
      break;
    }
    case 'bounds': {
      scope.postMessage({
        type: 'boundsResult',
        requestId: message.requestId,
        bounds: index.getBounds(),
      });
      break;
    }
  }
};
