/** Tests for the worker-side projection index. */

import { describe, it, expect, beforeEach } from 'vitest';
import { FRAME_STRIDE, ProjectionIndex } from './projection';
import { serializeCamera, createCamera, type ExactCamera } from '../camera/exactCamera';
import type { CircleData } from '../services/websocketService';

const W = 900;
const H = 600;

function circle(
  word: string,
  x: string,
  y: string,
  radius: string,
  generation = 0,
  curvature = '1/1'
): CircleData {
  return {
    curvature,
    center: { x, y },
    radius,
    generation,
    word,
    parent_ids: [],
    tangent_ids: [],
  };
}

/** The classic seed quartet in exact coordinates. */
function classicSeed(): CircleData[] {
  return [
    circle('S0', '0/1', '0/1', '-1/1', 0, '-1/1'),
    circle('S1', '1/2', '0/1', '1/2', 0, '2/1'),
    circle('S2', '-1/2', '0/1', '1/2', 0, '2/1'),
    circle('S3', '0/1', '2/3', '1/3', 0, '3/1'),
  ];
}

function cameraAt(scale: number, overrides: Partial<ExactCamera> = {}): ExactCamera {
  return { ...createCamera(), scale, ...overrides };
}

describe('ProjectionIndex', () => {
  let index: ProjectionIndex;

  beforeEach(() => {
    index = new ProjectionIndex();
  });

  it('adds circles and deduplicates by word', () => {
    expect(index.add(classicSeed())).toBe(4);
    expect(index.add(classicSeed())).toBe(0); // same words, all skipped
    expect(index.count).toBe(4);
  });

  it('projects to screen coordinates', () => {
    index.add(classicSeed());
    const { buffer, count } = index.project(
      serializeCamera(cameraAt(200)),
      W,
      H,
      null
    );

    expect(count).toBe(4);
    // The bounding circle (radius 1) is centered at the canvas center
    const rows = [] as number[][];
    for (let i = 0; i < count; i += 1) {
      rows.push(Array.from(buffer.slice(i * FRAME_STRIDE, (i + 1) * FRAME_STRIDE)));
    }
    const bounding = rows.find((r) => Math.abs(r[2] - 200) < 1e-6);
    expect(bounding).toBeDefined();
    expect(bounding![0]).toBeCloseTo(W / 2, 5);
    expect(bounding![1]).toBeCloseTo(H / 2, 5);
  });

  it('culls circles outside the viewport and below pixel size', () => {
    index.add(classicSeed());
    index.add([circle('far', '1000/1', '0/1', '1/1')]);
    index.add([circle('tiny', '0/1', '0/1', '1/100000')]);

    const { count } = index.project(serializeCamera(cameraAt(200)), W, H, null);
    expect(count).toBe(4); // far + tiny are culled
  });

  it('reports the selected circle even when culled by size', () => {
    index.add(classicSeed());
    const { selected } = index.project(serializeCamera(cameraAt(200)), W, H, 'S3');
    expect(selected).not.toBeNull();
    expect(selected![2]).toBeCloseTo(200 / 3, 4); // r=1/3 at 200px/unit
  });

  it('hit-tests the smallest containing circle', () => {
    index.add(classicSeed());
    const camera = serializeCamera(cameraAt(200));
    index.project(camera, W, H, null);

    // Click the center of the top circle (0, 2/3)
    const hit = index.hitTest(camera, W / 2, H / 2 + (2 / 3) * 200, W, H);
    expect(hit).not.toBeNull();
    expect(hit!.word).toBe('S3');
    expect(hit!.curvature).toBe('3/1');

    // A point inside the bounding circle but in a gap hits the bounding circle
    const gap = index.hitTest(camera, W / 2 + 0.62 * 200, H / 2 + 0.62 * 200, W, H);
    expect(gap!.word).toBe('S0');

    // A point outside everything hits nothing
    const miss = index.hitTest(camera, W / 2 + 300, H / 2 + 300, W, H);
    expect(miss).toBeNull();
  });

  it('keeps pixel precision at deep zoom (exact relative cache)', () => {
    // Two circles exactly 1e-12 apart in world space:
    // b.x = 1/3 + 1/10^12 = (10^12 + 3) / (3·10^12)
    index.add([
      circle('a', '1/3', '0/1', '1/1000000000000'),
      circle('b', '1000000000003/3000000000000', '0/1', '1/1000000000000'),
    ]);
    const camera = {
      ...createCamera(),
      originX: { n: 1n, d: 3n },
      scale: 1e14, // 1e-12 world = 100 px
    };
    const { buffer, count } = index.project(serializeCamera(camera), W, H, null);
    expect(count).toBe(2);
    const xs = [buffer[0], buffer[FRAME_STRIDE]].sort((p, q) => p - q);
    // Separation must be ~100px, exact to sub-pixel despite coordinates ~1/3
    expect(xs[1] - xs[0]).toBeCloseTo(100, 3);
  });

  it('returns the smallest visible circles for deepening anchors', () => {
    index.add(classicSeed());
    index.add([circle('far', '1000/1', '0/1', '1/1')]);
    const camera = serializeCamera(cameraAt(200));

    const smallest = index.smallestVisible(camera, W, H, 2);
    expect(smallest.map((c) => c.word)).toEqual(['S3', 'S1']);
    expect(smallest[0].radius).toBeCloseTo(1 / 3, 9);

    // Zoomed onto the top circle: the off-screen seeds drop out
    const zoomed = serializeCamera({
      ...cameraAt(50000),
      originX: { n: 0n, d: 1n },
      originY: { n: 2n, d: 3n },
    });
    index.project(zoomed, W, H, null);
    const words = index.smallestVisible(zoomed, W, H, 8).map((c) => c.word);
    expect(words).toContain('S3');
    expect(words).not.toContain('far');
  });

  it('computes coloring metrics', () => {
    index.add(classicSeed());
    const camera = serializeCamera(cameraAt(200));

    const t = (metric: import('./projection').ColorMetric) => {
      const { buffer, count } = index.project(camera, W, H, null, metric);
      const map = new Map<number, number>();
      for (let i = 0; i < count; i += 1) {
        map.set(buffer[i * 4 + 2], buffer[i * 4 + 3]); // rPx -> t
      }
      return map;
    };

    // residue mod 24: bend 3 -> 3/23, bend -1 -> 23/23
    const residue = t({ kind: 'residue', modulus: 24 });
    expect(residue.get(Math.fround(200 / 3))).toBeCloseTo(3 / 23, 6); // bend-3 circle
    expect(residue.get(200)).toBeCloseTo(1, 6); // bend -1 -> residue 23

    // parity: bend 2 -> 0, bend 3 -> 1
    const parity = t({ kind: 'parity' });
    expect(parity.get(100)).toBe(0);
    expect(parity.get(Math.fround(200 / 3))).toBe(1);

    // prime: 2 and 3 prime -> 1; -1 -> 0
    const prime = t({ kind: 'prime' });
    expect(prime.get(100)).toBe(1);
    expect(prime.get(200)).toBe(0);
  });

  it('integerBend and isPrimeBend helpers', async () => {
    const { integerBend, isPrimeBend } = await import('./projection');
    expect(integerBend('6/1')).toBe(6);
    expect(integerBend('-1/1')).toBe(-1);
    expect(integerBend('3/2')).toBeNull();
    expect(isPrimeBend(11)).toBe(true);
    expect(isPrimeBend(-11)).toBe(true);
    expect(isPrimeBend(1)).toBe(false);
    expect(isPrimeBend(null)).toBe(false);
  });

  it('tracks bounds incrementally', () => {
    index.add(classicSeed());
    const bounds = index.getBounds()!;
    expect(bounds.minX).toBeCloseTo(-1, 9);
    expect(bounds.maxX).toBeCloseTo(1, 9);
    expect(bounds.minY).toBeCloseTo(-1, 9);
    expect(bounds.maxY).toBeCloseTo(1, 9);
  });

  it('clear resets everything', () => {
    index.add(classicSeed());
    index.clear();
    expect(index.count).toBe(0);
    expect(index.getBounds()).toBeNull();
  });
});
