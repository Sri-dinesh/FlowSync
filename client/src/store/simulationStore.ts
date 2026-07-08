import { create } from "zustand";

import type {
  SimulationFrame,
  SimulationMode,
  TrainingMetric,
} from "@/types/simulation";

interface SimulationStore {
  isConnected: boolean;
  isRunning: boolean;
  isTraining: boolean;
  mode: SimulationMode;
  currentFrame: SimulationFrame | null;
  lastFrameAt: number | null;
  trainingMetrics: TrainingMetric[];
  setFrame: (frame: SimulationFrame) => void;
  addTrainingMetric: (metric: TrainingMetric) => void;
  setMode: (mode: SimulationMode) => void;
  setConnected: (value: boolean) => void;
  setRunning: (value: boolean) => void;
  setTraining: (value: boolean) => void;
  resetMetrics: () => void;
  resetSimulation: () => void;
}

const MAX_TRAINING_METRICS = 1000;

export const useSimulationStore = create<SimulationStore>((set) => ({
  isConnected: false,
  isRunning: false,
  isTraining: false,
  mode: "fixed",
  currentFrame: null,
  lastFrameAt: null,
  trainingMetrics: [],
  setFrame: (frame) =>
    set((state) => ({
      currentFrame: frame,
      lastFrameAt: Date.now(),
      isRunning: true,
      mode:
        frame.mode === "fixed" || frame.mode === "ai" ? frame.mode : state.mode,
    })),
  addTrainingMetric: (metric) =>
    set((state) => {
      const next = [...state.trainingMetrics, metric];
      const trimmed =
        next.length > MAX_TRAINING_METRICS
          ? next.slice(-MAX_TRAINING_METRICS)
          : next;
      return { trainingMetrics: trimmed, isTraining: metric.is_training };
    }),
  setMode: (mode) => set({ mode }),
  setConnected: (value) => set({ isConnected: value }),
  setRunning: (value) => set({ isRunning: value }),
  setTraining: (value) => set({ isTraining: value }),
  resetMetrics: () => set({ trainingMetrics: [] }),
  resetSimulation: () =>
    set({
      isRunning: false,
      currentFrame: null,
      lastFrameAt: null,
    }),
}));
