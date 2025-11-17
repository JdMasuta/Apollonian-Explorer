/**
 * Zustand store for Apollonian Gasket state management.
 *
 * Manages circles data, selection state, generation progress, and WebSocket integration.
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 3 Task 7
 */

import { create } from 'zustand';
import type { CircleData } from '../services/websocketService';

/**
 * Gasket metadata from backend.
 */
export interface GasketMetadata {
  id: number | null;
  initial_curvatures: string[];
  max_depth: number;
  total_circles: number;
}

/**
 * Gasket store state interface.
 */
interface GasketState {
  // Circle data
  circles: CircleData[];

  // Selection state
  selectedCircleId: number | null;

  // Generation state
  isGenerating: boolean;
  currentGeneration: number;
  progress: number; // 0-100

  // Gasket metadata
  gasket: GasketMetadata | null;

  // Error state
  error: string | null;

  // Actions
  setCircles: (circles: CircleData[]) => void;
  addCircles: (circles: CircleData[]) => void;
  clearCircles: () => void;

  setSelectedCircle: (id: number | null) => void;

  setGenerating: (isGenerating: boolean) => void;
  setCurrentGeneration: (generation: number) => void;
  setProgress: (progress: number) => void;

  setGasket: (gasket: GasketMetadata | null) => void;
  setError: (error: string | null) => void;

  reset: () => void;
}

/**
 * Initial state.
 */
const initialState = {
  circles: [],
  selectedCircleId: null,
  isGenerating: false,
  currentGeneration: 0,
  progress: 0,
  gasket: null,
  error: null,
};

/**
 * Zustand store for gasket state.
 *
 * Usage:
 * ```typescript
 * import useGasketStore from './stores/gasketStore';
 *
 * function MyComponent() {
 *   const circles = useGasketStore((state) => state.circles);
 *   const addCircles = useGasketStore((state) => state.addCircles);
 *
 *   return <div>Circles: {circles.length}</div>;
 * }
 * ```
 */
export const useGasketStore = create<GasketState>((set) => ({
  ...initialState,

  setCircles: (circles) => set({ circles }),

  addCircles: (newCircles) =>
    set((state) => ({
      circles: [...state.circles, ...newCircles],
    })),

  clearCircles: () => set({ circles: [] }),

  setSelectedCircle: (id) => set({ selectedCircleId: id }),

  setGenerating: (isGenerating) => set({ isGenerating }),

  setCurrentGeneration: (generation) => set({ currentGeneration: generation }),

  setProgress: (progress) => set({ progress }),

  setGasket: (gasket) => set({ gasket }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}));

export default useGasketStore;
