/** Tests for the exact deep-zoom camera. */

import { describe, it, expect } from 'vitest';
import {
  REBASE_THRESHOLD_PX,
  createCamera,
  fitToBounds,
  maybeRebase,
  pan,
  screenToWorldRelative,
  serializeCamera,
  worldToScreen,
  zoomAt,
} from './exactCamera';
import { add, fromNumber, fromString } from '../math/rational';

const W = 900;
const H = 600;

describe('exactCamera', () => {
  it('projects the origin to the canvas center', () => {
    const camera = createCamera();
    const { sx, sy } = worldToScreen(camera, fromNumber(0), fromNumber(0), W, H);
    expect(sx).toBe(W / 2);
    expect(sy).toBe(H / 2);
  });

  it('zoomAt keeps the world point under the cursor fixed', () => {
    let camera = { ...createCamera(), scale: 300 };
    const world = { x: fromString('1/3'), y: fromString('-2/7') };
    const before = worldToScreen(camera, world.x, world.y, W, H);

    camera = zoomAt(camera, before.sx, before.sy, 4, W, H);
    const after = worldToScreen(camera, world.x, world.y, W, H);

    expect(after.sx).toBeCloseTo(before.sx, 6);
    expect(after.sy).toBeCloseTo(before.sy, 6);
    expect(camera.scale).toBe(1200);
  });

  it('zoom is unclamped (the 0.1-10x limit is gone)', () => {
    let camera = { ...createCamera(), scale: 1 };
    for (let i = 0; i < 50; i += 1) {
      camera = zoomAt(camera, W / 2, H / 2, 2, W, H);
    }
    expect(camera.scale).toBe(2 ** 50); // ~1e15
  });

  it('pan moves the view and rebases beyond the threshold', () => {
    let camera = { ...createCamera(), scale: 100 };
    camera = pan(camera, REBASE_THRESHOLD_PX + 100, 0);
    // Rebase folded the offset into the exact origin
    expect(Math.abs(camera.offsetX)).toBeLessThan(1);
    expect(camera.originX.n).not.toBe(0n);
  });

  it('positions stay pixel-exact at deep zoom after rebasing', () => {
    // A circle 1e-12 away from a far-from-zero anchor point.
    const anchor = fromString('2/3');
    const target = add(anchor, fromString('1/1000000000000'));

    let camera = {
      originX: anchor,
      originY: fromNumber(0),
      scale: 1e14, // 1e-12 world units = 100px
      offsetX: 0,
      offsetY: 0,
    };

    const p = worldToScreen(camera, target, fromNumber(0), W, H);
    expect(p.sx - W / 2).toBeCloseTo(100, 6);

    // Pan far away and back; rebasing must not corrupt the geometry.
    camera = pan(camera, REBASE_THRESHOLD_PX * 2, 0);
    camera = pan(camera, -REBASE_THRESHOLD_PX * 2, 0);
    const p2 = worldToScreen(camera, target, fromNumber(0), W, H);
    expect(p2.sx - W / 2).toBeCloseTo(100, 3);
  });

  it('screenToWorldRelative inverts the projection (relative to origin)', () => {
    const camera = { ...createCamera(), scale: 250, offsetX: 13, offsetY: -7 };
    const { relX, relY } = screenToWorldRelative(camera, 500, 200, W, H);
    const sx = relX * camera.scale + W / 2 + camera.offsetX;
    const sy = relY * camera.scale + H / 2 + camera.offsetY;
    expect(sx).toBeCloseTo(500, 9);
    expect(sy).toBeCloseTo(200, 9);
  });

  it('fitToBounds frames the box with padding', () => {
    const camera = fitToBounds({ minX: -1, maxX: 1, minY: -1, maxY: 1 }, W, H, 0.1);
    // Height is the constraint: 600*0.8 / 2 = 240 px per unit
    expect(camera.scale).toBeCloseTo(240, 9);
    const corner = worldToScreen(camera, fromNumber(1), fromNumber(1), W, H);
    expect(corner.sx).toBeCloseTo(W / 2 + 240, 6);
  });

  it('maybeRebase is a no-op below the threshold', () => {
    const camera = { ...createCamera(), offsetX: 10, offsetY: -10 };
    expect(maybeRebase(camera)).toEqual(camera);
  });

  it('serializes for the worker', () => {
    const camera = { ...createCamera(), scale: 42 };
    const message = serializeCamera(camera);
    expect(message.originX).toBe('0/1');
    expect(message.scale).toBe(42);
  });
});
