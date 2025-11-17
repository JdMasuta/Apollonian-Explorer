/**
 * Utility functions for canvas coordinate transformations and calculations.
 *
 * Reference: DESIGN_SPEC.md section 10.1 (Canvas Rendering)
 */

import type { CircleData } from '../../services/websocketService';

/**
 * Bounding box for a set of circles.
 */
export interface BoundingBox {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

/**
 * Parse fraction string to number.
 *
 * Handles both simple decimals and fraction notation.
 *
 * @param value - String value ("3", "3/2", "1.5")
 * @returns Numeric value
 */
export function parseValue(value: string): number {
  if (value.includes('/')) {
    const [num, denom] = value.split('/').map(Number);
    return num / denom;
  }
  return parseFloat(value);
}

/**
 * Convert curvature to radius.
 *
 * @param curvature - Curvature string
 * @returns Radius as number
 */
export function curvatureToRadius(curvature: string): number {
  const k = parseValue(curvature);
  return Math.abs(1 / k);
}

/**
 * Calculate bounding box for a set of circles.
 *
 * Finds the min/max coordinates of all circles to determine the
 * area that needs to be visible on the canvas.
 *
 * @param circles - Array of circle data
 * @returns Bounding box containing all circles
 */
export function calculateBoundingBox(circles: CircleData[]): BoundingBox {
  if (circles.length === 0) {
    return {
      minX: -1,
      maxX: 1,
      minY: -1,
      maxY: 1,
      width: 2,
      height: 2,
      centerX: 0,
      centerY: 0,
    };
  }

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  circles.forEach((circle) => {
    const x = parseValue(circle.center.x);
    const y = parseValue(circle.center.y);
    const radius = curvatureToRadius(circle.curvature);

    // Circle bounds
    const left = x - radius;
    const right = x + radius;
    const top = y - radius;
    const bottom = y + radius;

    minX = Math.min(minX, left);
    maxX = Math.max(maxX, right);
    minY = Math.min(minY, top);
    maxY = Math.max(maxY, bottom);
  });

  const width = maxX - minX;
  const height = maxY - minY;

  return {
    minX,
    maxX,
    minY,
    maxY,
    width,
    height,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
  };
}

/**
 * Calculate scale and position to fit bounding box in canvas.
 *
 * Returns the scale factor and offsets needed to center and fit
 * the gasket in the canvas with some padding.
 *
 * @param bbox - Bounding box to fit
 * @param canvasWidth - Canvas width in pixels
 * @param canvasHeight - Canvas height in pixels
 * @param padding - Padding as fraction (0-1, default 0.1 = 10%)
 * @returns Scale and position transform
 */
export function calculateFitTransform(
  bbox: BoundingBox,
  canvasWidth: number,
  canvasHeight: number,
  padding: number = 0.1
): { scale: number; x: number; y: number } {
  // Calculate available space with padding
  const availableWidth = canvasWidth * (1 - 2 * padding);
  const availableHeight = canvasHeight * (1 - 2 * padding);

  // Calculate scale to fit (use the more constrained dimension)
  const scaleX = availableWidth / bbox.width;
  const scaleY = availableHeight / bbox.height;
  const scale = Math.min(scaleX, scaleY);

  // Calculate offset to center
  const x = canvasWidth / 2 - bbox.centerX * scale;
  const y = canvasHeight / 2 - bbox.centerY * scale;

  return { scale, x, y };
}

/**
 * Generate color based on circle generation.
 *
 * Uses a gradient from blue (gen 0) to red (deeper generations).
 *
 * @param generation - Circle generation (0, 1, 2, ...)
 * @param maxGeneration - Maximum generation in the gasket
 * @returns CSS color string
 */
export function getCircleColor(
  generation: number,
  maxGeneration: number
): string {
  if (maxGeneration === 0) {
    return '#2196f3'; // Blue for single generation
  }

  // Normalize generation to 0-1
  const t = generation / maxGeneration;

  // Interpolate from blue to red
  const r = Math.round(33 + t * (244 - 33)); // 33 -> 244
  const g = Math.round(150 - t * (83)); // 150 -> 67
  const b = Math.round(243 - t * (243 - 54)); // 243 -> 54

  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Get stroke width based on circle size and selection state.
 *
 * @param radius - Circle radius in canvas coordinates
 * @param isSelected - Whether circle is selected
 * @returns Stroke width in pixels
 */
export function getStrokeWidth(radius: number, isSelected: boolean): number {
  if (isSelected) {
    return Math.max(2, Math.min(radius * 0.1, 5));
  }
  return Math.max(0.5, Math.min(radius * 0.05, 2));
}

/**
 * Format curvature for display.
 *
 * @param curvature - Curvature string
 * @returns Formatted string
 */
export function formatCurvature(curvature: string): string {
  if (curvature.includes('/')) {
    return curvature; // Keep fraction notation
  }
  const value = parseFloat(curvature);
  // Format with up to 4 decimal places
  return value.toFixed(4).replace(/\.?0+$/, '');
}
