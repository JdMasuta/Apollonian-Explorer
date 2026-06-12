/** Tests for the Canvas2D fallback renderer (WebGL2 needs a real GPU). */

import { describe, it, expect, vi } from 'vitest';
import { Canvas2DCircleRenderer, PALETTE } from './circleRenderer';
import { FRAME_STRIDE } from './rendererClient';

function stubContext() {
  return {
    setTransform: vi.fn(),
    fillRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    arc: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 0,
  };
}

function stubCanvas(ctx: ReturnType<typeof stubContext>) {
  return {
    getContext: vi.fn(() => ctx),
    width: 0,
    height: 0,
  } as unknown as HTMLCanvasElement;
}

function makeFrame(circles: [number, number, number, number][]) {
  const positions = new Float32Array(circles.length * FRAME_STRIDE);
  circles.forEach((c, i) => positions.set(c, i * FRAME_STRIDE));
  return { positions, count: circles.length, selected: null };
}

describe('Canvas2DCircleRenderer', () => {
  it('clears the background and draws one arc per circle', () => {
    const ctx = stubContext();
    const renderer = new Canvas2DCircleRenderer(stubCanvas(ctx));
    renderer.resize(900, 600, 2);

    renderer.draw(makeFrame([
      [450, 300, 100, 0],
      [200, 200, 50, 1],
    ]));

    expect(ctx.setTransform).toHaveBeenCalledWith(2, 0, 0, 2, 0, 0);
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, 900, 600);
    expect(ctx.arc).toHaveBeenCalledTimes(2);
    expect(ctx.arc).toHaveBeenCalledWith(450, 300, 100, 0, Math.PI * 2);
  });

  it('groups strokes by palette bucket', () => {
    const ctx = stubContext();
    const renderer = new Canvas2DCircleRenderer(stubCanvas(ctx));
    renderer.resize(900, 600, 1);

    // Two circles in the same bucket (t=0) and one in another (t=1):
    renderer.draw(makeFrame([
      [100, 100, 10, 0],
      [200, 200, 10, 0],
      [300, 300, 10, 1],
    ]));

    expect(ctx.stroke).toHaveBeenCalledTimes(2); // one per used bucket
  });

  it('draws the selection highlight', () => {
    const ctx = stubContext();
    const renderer = new Canvas2DCircleRenderer(stubCanvas(ctx));
    renderer.resize(900, 600, 1);

    const frame = makeFrame([[450, 300, 100, 0]]);
    renderer.draw({ ...frame, selected: new Float32Array([450, 300, 100]) });

    expect(ctx.fill).toHaveBeenCalledTimes(1);
    expect(ctx.arc).toHaveBeenCalledWith(450, 300, 100, 0, Math.PI * 2);
  });

  it('handles empty frames', () => {
    const ctx = stubContext();
    const renderer = new Canvas2DCircleRenderer(stubCanvas(ctx));
    renderer.resize(900, 600, 1);
    renderer.draw(null);
    expect(ctx.fillRect).toHaveBeenCalled();
    expect(ctx.arc).not.toHaveBeenCalled();
  });

  it('palette spans blue to red', () => {
    expect(PALETTE[0]).toBe('rgb(33, 150, 243)');
    expect(PALETTE[63]).toBe('rgb(244, 67, 54)');
  });
});
