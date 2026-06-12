/**
 * Projection index: the worker-side circle store.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * Holds every received circle with its EXACT world coordinates (BigInt
 * rationals parsed once from the wire's "num/denom" strings) and a cache of
 * float coordinates RELATIVE to the camera's exact origin. The cache is
 * rebuilt only when the origin rebases (rare); per-frame projection is then
 * pure float math, so panning/zooming 10^5 circles costs a few ms.
 *
 * Pure module (no Worker APIs) so it is unit-testable; mathWorker.ts is the
 * thin message shell around it.
 */

import {
  type BigRational,
  fromString,
  sub,
  toNumber,
} from '../math/rational';
import type { CameraMessage } from '../camera/exactCamera';
import type { CircleData } from '../services/websocketService';

/** Floats per instance in a projected frame: sx, sy, rPx, colorT. */
export const FRAME_STRIDE = 4;

/** Circles smaller than this many pixels are culled. */
const MIN_PIXEL_RADIUS = 0.25;

export interface HitResult {
  word: string;
  curvature: string;
  generation: number;
  id: number | null;
}

export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface ParsedCamera {
  originX: BigRational;
  originY: BigRational;
  originKey: string;
  scale: number;
  offsetX: number;
  offsetY: number;
}

function parseCamera(message: CameraMessage): ParsedCamera {
  return {
    originX: fromString(message.originX),
    originY: fromString(message.originY),
    originKey: `${message.originX}|${message.originY}`,
    scale: message.scale,
    offsetX: message.offsetX,
    offsetY: message.offsetY,
  };
}

export class ProjectionIndex {
  private words: string[] = [];
  private wordSet = new Set<string>();
  private xs: BigRational[] = [];
  private ys: BigRational[] = [];
  private radii: number[] = [];
  private generations: number[] = [];
  private curvatures: string[] = [];
  private ids: (number | null)[] = [];

  private maxGeneration = 0;
  private bounds: Bounds | null = null;

  /** Float coordinates relative to the cached origin. */
  private relX: number[] = [];
  private relY: number[] = [];
  private cachedOriginKey: string | null = null;

  get count(): number {
    return this.words.length;
  }

  clear(): void {
    this.words = [];
    this.wordSet.clear();
    this.xs = [];
    this.ys = [];
    this.radii = [];
    this.generations = [];
    this.curvatures = [];
    this.ids = [];
    this.maxGeneration = 0;
    this.bounds = null;
    this.relX = [];
    this.relY = [];
    this.cachedOriginKey = null;
  }

  /**
   * Add circles, deduplicating by group word (re-fetches from the viewport
   * endpoint overlap what streaming already delivered).
   * Returns the number actually added.
   */
  add(circles: CircleData[]): number {
    let added = 0;
    for (const circle of circles) {
      const word = circle.word ?? `anon-${this.words.length}`;
      if (this.wordSet.has(word)) {
        continue;
      }
      const x = fromString(circle.center.x);
      const y = fromString(circle.center.y);
      const r = Math.abs(toNumber(fromString(circle.radius)));

      this.wordSet.add(word);
      this.words.push(word);
      this.xs.push(x);
      this.ys.push(y);
      this.radii.push(r);
      this.generations.push(circle.generation);
      this.curvatures.push(circle.curvature);
      this.ids.push(circle.id ?? null);
      added += 1;

      if (circle.generation > this.maxGeneration) {
        this.maxGeneration = circle.generation;
      }

      const xf = toNumber(x);
      const yf = toNumber(y);
      if (!this.bounds) {
        this.bounds = { minX: xf - r, maxX: xf + r, minY: yf - r, maxY: yf + r };
      } else {
        if (xf - r < this.bounds.minX) this.bounds.minX = xf - r;
        if (xf + r > this.bounds.maxX) this.bounds.maxX = xf + r;
        if (yf - r < this.bounds.minY) this.bounds.minY = yf - r;
        if (yf + r > this.bounds.maxY) this.bounds.maxY = yf + r;
      }

      // Keep the relative cache coherent if one exists.
      if (this.cachedOriginKey !== null) {
        this.relX.push(this.lastOriginRelX(x));
        this.relY.push(this.lastOriginRelY(y));
      }
    }
    return added;
  }

  getBounds(): Bounds | null {
    return this.bounds ? { ...this.bounds } : null;
  }

  /**
   * Project all circles through the camera into a packed Float32Array of
   * [sx, sy, rPx, colorT] for visible circles. The exact->relative-float
   * conversion happens only when the camera origin changed.
   */
  project(
    camera: CameraMessage,
    width: number,
    height: number,
    selectedWord: string | null
  ): { buffer: Float32Array; count: number; selected: Float32Array | null } {
    const parsed = parseCamera(camera);
    this.ensureRelativeCache(parsed);

    const { scale, offsetX, offsetY } = parsed;
    const cx = width / 2 + offsetX;
    const cy = height / 2 + offsetY;
    const n = this.words.length;
    const out = new Float32Array(n * FRAME_STRIDE);
    let m = 0;
    let selected: Float32Array | null = null;
    const genScale = this.maxGeneration > 0 ? 1 / this.maxGeneration : 0;

    for (let i = 0; i < n; i += 1) {
      const sx = this.relX[i] * scale + cx;
      const sy = this.relY[i] * scale + cy;
      const rPx = this.radii[i] * scale;
      const isSelected = selectedWord !== null && this.words[i] === selectedWord;
      if (isSelected) {
        selected = new Float32Array([sx, sy, rPx]);
      }
      if (rPx < MIN_PIXEL_RADIUS) continue;
      if (sx + rPx < 0 || sx - rPx > width || sy + rPx < 0 || sy - rPx > height) {
        continue;
      }
      const base = m * FRAME_STRIDE;
      out[base] = sx;
      out[base + 1] = sy;
      out[base + 2] = rPx;
      out[base + 3] = this.generations[i] * genScale;
      m += 1;
    }
    return { buffer: out.slice(0, m * FRAME_STRIDE), count: m, selected };
  }

  /**
   * Smallest circle containing the screen point (math hit-test; no scene
   * graph). Returns null when the point is in a gap.
   */
  hitTest(
    camera: CameraMessage,
    sx: number,
    sy: number,
    width: number,
    height: number
  ): HitResult | null {
    const parsed = parseCamera(camera);
    this.ensureRelativeCache(parsed);
    const px = (sx - width / 2 - parsed.offsetX) / parsed.scale;
    const py = (sy - height / 2 - parsed.offsetY) / parsed.scale;

    let best = -1;
    let bestR = Infinity;
    for (let i = 0; i < this.words.length; i += 1) {
      const dx = this.relX[i] - px;
      const dy = this.relY[i] - py;
      const r = this.radii[i];
      if (dx * dx + dy * dy <= r * r && r < bestR) {
        best = i;
        bestR = r;
      }
    }
    if (best === -1) {
      return null;
    }
    return {
      word: this.words[best],
      curvature: this.curvatures[best],
      generation: this.generations[best],
      id: this.ids[best],
    };
  }

  /**
   * The N smallest circles intersecting the viewport (any pixel size).
   * These provide the group words that viewport deepening resumes from:
   * their subtrees fill the on-screen gaps.
   */
  smallestVisible(
    camera: CameraMessage,
    width: number,
    height: number,
    limit: number
  ): { word: string; radius: number }[] {
    const parsed = parseCamera(camera);
    this.ensureRelativeCache(parsed);
    const { scale, offsetX, offsetY } = parsed;
    const cx = width / 2 + offsetX;
    const cy = height / 2 + offsetY;

    const candidates: { word: string; radius: number }[] = [];
    for (let i = 0; i < this.words.length; i += 1) {
      const sx = this.relX[i] * scale + cx;
      const sy = this.relY[i] * scale + cy;
      const rPx = this.radii[i] * scale;
      if (sx + rPx < 0 || sx - rPx > width || sy + rPx < 0 || sy - rPx > height) {
        continue;
      }
      candidates.push({ word: this.words[i], radius: this.radii[i] });
    }
    candidates.sort((a, b) => a.radius - b.radius);
    return candidates.slice(0, limit);
  }

  // ------------------------------------------------------------------

  private lastOrigin: ParsedCamera | null = null;

  private ensureRelativeCache(camera: ParsedCamera): void {
    if (this.cachedOriginKey === camera.originKey && this.relX.length === this.words.length) {
      return;
    }
    this.lastOrigin = camera;
    this.cachedOriginKey = camera.originKey;
    const n = this.words.length;
    this.relX = new Array(n);
    this.relY = new Array(n);
    for (let i = 0; i < n; i += 1) {
      this.relX[i] = toNumber(sub(this.xs[i], camera.originX));
      this.relY[i] = toNumber(sub(this.ys[i], camera.originY));
    }
  }

  private lastOriginRelX(x: BigRational): number {
    return this.lastOrigin ? toNumber(sub(x, this.lastOrigin.originX)) : 0;
  }

  private lastOriginRelY(y: BigRational): number {
    return this.lastOrigin ? toNumber(sub(y, this.lastOrigin.originY)) : 0;
  }
}
