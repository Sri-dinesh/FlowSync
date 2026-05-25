import { create } from "zustand";

import type {
  SimulationFrame,
  SimulationMode,
  TrainingMetric,
} from "@/types/simulation";

interface SimulationStore {
  isConnected: boolean;
  isTraining: boolean;
  mode: SimulationMode;
  currentFrame: SimulationFrame | null;
  trainingMetrics: TrainingMetric[];
  setFrame: (frame: SimulationFrame) => void;
  addTrainingMetric: (metric: TrainingMetric) => void;
  setMode: (mode: SimulationMode) => void;
  setConnected: (value: boolean) => void;
  setTraining: (value: boolean) => void;
  resetMetrics: () => void;
}

const MAX_TRAINING_METRICS = 1000;

export const useSimulationStore = create<SimulationStore>((set) => ({
  isConnected: false,
  isTraining: false,
  mode: "fixed",
  currentFrame: null,
  trainingMetrics: [],
  setFrame: (frame) =>
    set((state) => ({
      currentFrame: frame,
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
  setTraining: (value) => set({ isTraining: value }),
  resetMetrics: () => set({ trainingMetrics: [] }),
}));
