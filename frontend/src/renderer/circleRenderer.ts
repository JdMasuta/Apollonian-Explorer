/**
 * Circle renderers: WebGL2 instanced SDF (primary) and Canvas2D (fallback).
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage B).
 *
 * Both consume the projection worker's packed frames directly
 * ([sx, sy, rPx, colorT] per circle, FRAME_STRIDE floats) — the WebGL path
 * uploads the Float32Array as ONE instance buffer and draws a single
 * instanced quad batch, with the circle outline evaluated as a signed
 * distance field in the fragment shader: perfectly anti-aliased at any
 * radius, ~10^5 instances at 60fps.
 */

import type { Frame } from './rendererClient';
import { FRAME_STRIDE } from './rendererClient';

export interface CircleRenderer {
  draw(frame: Frame | null): void;
  resize(width: number, height: number, dpr: number): void;
  dispose(): void;
}

const BG = { r: 0xfa / 255, g: 0xfa / 255, b: 0xfa / 255 };

const VERTEX_SHADER = `#version 300 es
precision highp float;
layout(location = 0) in vec2 corner;     // unit quad corner (-1..1)
layout(location = 1) in vec4 instance;   // sx, sy, rPx, colorT
uniform vec2 resolution;                 // CSS pixels
out vec2 local;                          // CSS px offset from center
out float radius;
out float colorT;
void main() {
  float pad = instance.z + 1.5;
  local = corner * pad;
  radius = instance.z;
  colorT = instance.w;
  vec2 px = instance.xy + local;
  vec2 ndc = (px / resolution) * 2.0 - 1.0;
  gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
in vec2 local;
in float radius;
in float colorT;
uniform vec4 strokeOverride;   // a > 0: use rgb instead of the palette
uniform float fillAlpha;       // selected-circle translucent fill
out vec4 outColor;

vec3 palette(float t) {
  // Matches the Canvas2D palette: blue (33,150,243) -> red (244,67,54)
  return mix(vec3(33.0, 150.0, 243.0), vec3(244.0, 67.0, 54.0), t) / 255.0;
}

void main() {
  float dist = length(local);
  float d = abs(dist - radius);            // distance to the circle line
  float w = 0.75;                          // stroke half-width (CSS px)
  float alpha = 1.0 - smoothstep(w - 0.5, w + 0.5, d);
  vec3 rgb = strokeOverride.a > 0.0 ? strokeOverride.rgb : palette(colorT);
  float fill = fillAlpha * (1.0 - smoothstep(radius - 0.5, radius + 0.5, dist));
  float a = max(alpha, fill);
  if (a <= 0.001) discard;
  outColor = vec4(rgb, 1.0) * max(alpha, 0.0) +
             vec4(1.0, 0.92, 0.23, 1.0) * (fill * (1.0 - alpha));
  outColor.a = a;
}`;

function compile(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader);
    gl.deleteShader(shader);
    throw new Error(`Shader compile failed: ${info}`);
  }
  return shader;
}

export class WebGLCircleRenderer implements CircleRenderer {
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram;
  private instanceBuffer: WebGLBuffer;
  private selectedBuffer: WebGLBuffer;
  private vao: WebGLVertexArrayObject;
  private selectedVao: WebGLVertexArrayObject;
  private resolutionLoc: WebGLUniformLocation;
  private strokeLoc: WebGLUniformLocation;
  private fillLoc: WebGLUniformLocation;
  private canvas: HTMLCanvasElement;
  private width = 1;
  private height = 1;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const gl = canvas.getContext('webgl2', { antialias: false, alpha: false });
    if (!gl) {
      throw new Error('WebGL2 not available');
    }
    this.gl = gl;

    const program = gl.createProgram()!;
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(`Program link failed: ${gl.getProgramInfoLog(program)}`);
    }
    this.program = program;
    this.resolutionLoc = gl.getUniformLocation(program, 'resolution')!;
    this.strokeLoc = gl.getUniformLocation(program, 'strokeOverride')!;
    this.fillLoc = gl.getUniformLocation(program, 'fillAlpha')!;

    // Shared unit quad
    const quad = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );

    const makeVao = (instanceBuffer: WebGLBuffer) => {
      const vao = gl.createVertexArray()!;
      gl.bindVertexArray(vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
      gl.enableVertexAttribArray(1);
      gl.vertexAttribPointer(1, 4, gl.FLOAT, false, FRAME_STRIDE * 4, 0);
      gl.vertexAttribDivisor(1, 1);
      gl.bindVertexArray(null);
      return vao;
    };

    this.instanceBuffer = gl.createBuffer()!;
    this.vao = makeVao(this.instanceBuffer);
    this.selectedBuffer = gl.createBuffer()!;
    this.selectedVao = makeVao(this.selectedBuffer);

    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  }

  resize(width: number, height: number, dpr: number): void {
    this.width = width;
    this.height = height;
    this.canvas.width = Math.max(1, Math.round(width * dpr));
    this.canvas.height = Math.max(1, Math.round(height * dpr));
    this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
  }

  draw(frame: Frame | null): void {
    const gl = this.gl;
    gl.clearColor(BG.r, BG.g, BG.b, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!frame || frame.count === 0) return;

    gl.useProgram(this.program);
    gl.uniform2f(this.resolutionLoc, this.width, this.height);

    // Main batch: palette strokes, no fill.
    gl.uniform4f(this.strokeLoc, 0, 0, 0, 0);
    gl.uniform1f(this.fillLoc, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instanceBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, frame.positions, gl.DYNAMIC_DRAW);
    gl.bindVertexArray(this.vao);
    gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, frame.count);

    // Selection highlight: orange stroke + translucent yellow fill.
    if (frame.selected) {
      const [sx, sy, r] = frame.selected;
      gl.uniform4f(this.strokeLoc, 0xf5 / 255, 0x7c / 255, 0x00 / 255, 1);
      gl.uniform1f(this.fillLoc, 0.25);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.selectedBuffer);
      gl.bufferData(
        gl.ARRAY_BUFFER,
        new Float32Array([sx, sy, Math.max(r, 3), 0]),
        gl.DYNAMIC_DRAW
      );
      gl.bindVertexArray(this.selectedVao);
      gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, 1);
    }
    gl.bindVertexArray(null);
  }

  dispose(): void {
    const gl = this.gl;
    gl.deleteProgram(this.program);
    gl.deleteBuffer(this.instanceBuffer);
    gl.deleteBuffer(this.selectedBuffer);
    gl.deleteVertexArray(this.vao);
    gl.deleteVertexArray(this.selectedVao);
  }
}

/** Precomputed blue→red palette (64 buckets), shared with the 2D fallback. */
export const PALETTE: string[] = Array.from({ length: 64 }, (_, i) => {
  const t = i / 63;
  const r = Math.round(33 + t * (244 - 33));
  const g = Math.round(150 - t * 83);
  const b = Math.round(243 - t * (243 - 54));
  return `rgb(${r}, ${g}, ${b})`;
});

export class Canvas2DCircleRenderer implements CircleRenderer {
  private ctx: CanvasRenderingContext2D;
  private canvas: HTMLCanvasElement;
  private width = 1;
  private height = 1;
  private dpr = 1;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('2D canvas not available');
    }
    this.ctx = ctx;
  }

  resize(width: number, height: number, dpr: number): void {
    this.width = width;
    this.height = height;
    this.dpr = dpr;
    this.canvas.width = Math.max(1, Math.round(width * dpr));
    this.canvas.height = Math.max(1, Math.round(height * dpr));
  }

  draw(frame: Frame | null): void {
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.fillStyle = '#fafafa';
    ctx.fillRect(0, 0, this.width, this.height);
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
  }

  dispose(): void {
    // nothing to release
  }
}

/** WebGL2 when available, Canvas2D otherwise (also exercised by tests). */
export function createCircleRenderer(canvas: HTMLCanvasElement): CircleRenderer {
  try {
    return new WebGLCircleRenderer(canvas);
  } catch {
    return new Canvas2DCircleRenderer(canvas);
  }
}
