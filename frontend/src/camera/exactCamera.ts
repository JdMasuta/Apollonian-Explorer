/**
 * Exact deep-zoom camera.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * The camera anchors the view to an exact rational world point (originX/Y).
 * Screen position of a world point p:
 *
 *     sx = toNumber(p.x − originX) · scale + width/2 + offsetX
 *
 * The exact subtraction happens against the anchor, so the float conversion
 * only ever sees a residual that is small relative to the viewport — pixel
 * precision is preserved at any zoom level (no 0.1–10× clamp anymore).
 *
 * Panning accumulates in the float pixel offset; when it grows beyond
 * REBASE_THRESHOLD_PX the offset is folded into the exact origin
 * (`maybeRebase`), keeping residuals small. Folding uses the exact dyadic
 * value of the float shift, so no drift accumulates.
 */

import {
  type BigRational,
  add,
  fromNumber,
  sub,
  toNumber,
} from '../math/rational';

export interface ExactCamera {
  originX: BigRational;
  originY: BigRational;
  /** Pixels per world unit (unbounded; 10^15 is fine). */
  scale: number;
  /** Pixel offset of the origin relative to the canvas center. */
  offsetX: number;
  offsetY: number;
}

/** Fold the pan offset into the origin beyond this many pixels. */
export const REBASE_THRESHOLD_PX = 4096;

export function createCamera(): ExactCamera {
  return {
    originX: fromNumber(0),
    originY: fromNumber(0),
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  };
}

/** Screen coordinates of an exact world point. */
export function worldToScreen(
  camera: ExactCamera,
  x: BigRational,
  y: BigRational,
  width: number,
  height: number
): { sx: number; sy: number } {
  return {
    sx: toNumber(sub(x, camera.originX)) * camera.scale + width / 2 + camera.offsetX,
    sy: toNumber(sub(y, camera.originY)) * camera.scale + height / 2 + camera.offsetY,
  };
}

/**
 * Approximate world coordinates of a screen point, relative to the origin.
 * Returned as floats (sufficient for hit-testing and viewport queries; the
 * absolute world point is origin + the returned relative offset).
 */
export function screenToWorldRelative(
  camera: ExactCamera,
  sx: number,
  sy: number,
  width: number,
  height: number
): { relX: number; relY: number } {
  return {
    relX: (sx - width / 2 - camera.offsetX) / camera.scale,
    relY: (sy - height / 2 - camera.offsetY) / camera.scale,
  };
}

/** Pan by a pixel delta. */
export function pan(camera: ExactCamera, dxPx: number, dyPx: number): ExactCamera {
  return maybeRebase({
    ...camera,
    offsetX: camera.offsetX + dxPx,
    offsetY: camera.offsetY + dyPx,
  });
}

/**
 * Zoom by `factor` keeping the world point under the cursor fixed.
 * No bounds: deep zoom is the point.
 */
export function zoomAt(
  camera: ExactCamera,
  cursorX: number,
  cursorY: number,
  factor: number,
  width: number,
  height: number
): ExactCamera {
  const relX = cursorX - width / 2 - camera.offsetX;
  const relY = cursorY - height / 2 - camera.offsetY;
  return maybeRebase({
    ...camera,
    scale: camera.scale * factor,
    offsetX: cursorX - width / 2 - relX * factor,
    offsetY: cursorY - height / 2 - relY * factor,
  });
}

/**
 * Fold large pixel offsets into the exact origin. The float world shift is
 * converted exactly (every double is a dyadic rational), and the residual
 * offset is recomputed from the exact difference, so rebasing introduces no
 * cumulative drift.
 */
export function maybeRebase(camera: ExactCamera): ExactCamera {
  if (
    Math.abs(camera.offsetX) <= REBASE_THRESHOLD_PX &&
    Math.abs(camera.offsetY) <= REBASE_THRESHOLD_PX
  ) {
    return camera;
  }
  const shiftWorldX = fromNumber(-camera.offsetX / camera.scale);
  const shiftWorldY = fromNumber(-camera.offsetY / camera.scale);
  const originX = add(camera.originX, shiftWorldX);
  const originY = add(camera.originY, shiftWorldY);
  return {
    ...camera,
    originX,
    originY,
    // Residual after the exact fold (≈0 up to one float rounding).
    offsetX: camera.offsetX + toNumber(shiftWorldX) * camera.scale,
    offsetY: camera.offsetY + toNumber(shiftWorldY) * camera.scale,
  };
}

/** Camera framing a float bounding box with padding. */
export function fitToBounds(
  bounds: { minX: number; maxX: number; minY: number; maxY: number },
  width: number,
  height: number,
  padding = 0.1
): ExactCamera {
  const spanX = Math.max(bounds.maxX - bounds.minX, 1e-12);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1e-12);
  const scale = Math.min(
    (width * (1 - 2 * padding)) / spanX,
    (height * (1 - 2 * padding)) / spanY
  );
  return {
    originX: fromNumber((bounds.minX + bounds.maxX) / 2),
    originY: fromNumber((bounds.minY + bounds.maxY) / 2),
    scale,
    offsetX: 0,
    offsetY: 0,
  };
}

/** Serializable form for postMessage to the projection worker. */
export interface CameraMessage {
  originX: string; // "n/d"
  originY: string;
  scale: number;
  offsetX: number;
  offsetY: number;
}

export function serializeCamera(camera: ExactCamera): CameraMessage {
  return {
    originX: `${camera.originX.n}/${camera.originX.d}`,
    originY: `${camera.originY.n}/${camera.originY.d}`,
    scale: camera.scale,
    offsetX: camera.offsetX,
    offsetY: camera.offsetY,
  };
}
