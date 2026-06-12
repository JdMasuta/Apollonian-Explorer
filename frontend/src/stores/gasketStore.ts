/**
 * Zustand store for Apollonian Gasket state management.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (Stage A).
 *
 * Holds METADATA only: bulk circle geometry lives in the projection worker
 * (src/workers/mathWorker.ts) behind rendererClient — pushing tens of
 * thousands of circles through React state was the source of the
 * "Maximum update depth exceeded" failures (DEBUG_LOG ERR-013).
 */

import { create } from 'zustand';
import type { HitResult } from '../workers/projection';

/**
 * Gasket metadata from backend.
 */
export interface GasketMetadata {
  id: number | null;
  initial_curvatures: string[];
  max_depth: number;
  total_circles: number;
}

interface GasketState {
  /** Number of circles held by the projection worker. */
  circleCount: number;

  /** Selected circle (group word is the identity). */
  selectedCircle: HitResult | null;

  // Generation state
  isGenerating: boolean;
  currentGeneration: number;
  progress: number; // 0-100

  gasket: GasketMetadata | null;
  error: string | null;

  // Actions
  setCircleCount: (count: number) => void;
  setSelectedCircle: (circle: HitResult | null) => void;
  setGenerating: (isGenerating: boolean) => void;
  setCurrentGeneration: (generation: number) => void;
  setProgress: (progress: number) => void;
  setGasket: (gasket: GasketMetadata | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  circleCount: 0,
  selectedCircle: null,
  isGenerating: false,
  currentGeneration: 0,
  progress: 0,
  gasket: null,
  error: null,
};

export const useGasketStore = create<GasketState>((set) => ({
  ...initialState,

  setCircleCount: (circleCount) => set({ circleCount }),
  setSelectedCircle: (selectedCircle) => set({ selectedCircle }),
  setGenerating: (isGenerating) => set({ isGenerating }),
  setCurrentGeneration: (generation) => set({ currentGeneration: generation }),
  setProgress: (progress) => set({ progress }),
  setGasket: (gasket) => set({ gasket }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));

export default useGasketStore;
