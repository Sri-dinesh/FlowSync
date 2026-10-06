import { create } from "zustand";
import type {
  ResearchScenario,
  NoisePresetKey,
  ResearchTelemetryFrame,
  PairedTelemetryFrame,
  ExperimentSummary,
} from "@/types/research";

export type RunStatus = "idle" | "starting" | "running" | "paused" | "completed" | "error" | "stopped";

export interface ActiveNoise {
  id: string;
  name: string;
  type: string;
  intensity: number;
  desc?: string;
}

export interface ReplayState {
  isPlaying: boolean;
  speed: number;
  currentStep: number;
  totalSteps: number;
}

interface ResearchState {
  // Configuration
  activeScenario: ResearchScenario;
  activeController: any;
  activeSeed: number;
  activeNoisePreset: NoisePresetKey;
  activeNoise: ActiveNoise;
  speedMultiplier: number;
  experimentId: string;
  
  // Connection State
  isWsConnected: boolean;
  
  // Execution State
  runStatus: RunStatus;
  errorMessage: string | null;
  currentFrame: ResearchTelemetryFrame | null;
  history: ResearchTelemetryFrame[];
  
  // Paired Comparison State
  isPairedMode: boolean;
  controllerA: string;
  controllerB: string;
  pairedFrame: PairedTelemetryFrame | null;
  pairedHistory: PairedTelemetryFrame[];
  pairedSummary: Record<string, unknown> | null;
  
  // Final Result & Provenance
  experimentSummary: ExperimentSummary | null;
  showProvenanceDrawer: boolean;
  
  // UI Display Modes
  debugOverlay: boolean;
  showPerceptionDebug: boolean;
  presentationMode: boolean;
  
  // Replay State
  replayFrames: ResearchTelemetryFrame[];
  replayIndex: number;
  isReplaying: boolean;
  replayState: ReplayState;

  // Actions
  setConfig: (config: {
    scenario?: ResearchScenario | null;
    controller?: any;
    seed?: number;
    noisePreset?: NoisePresetKey;
  }) => void;
  setSpeedMultiplier: (speed: number) => void;
  setFrame: (frame: ResearchTelemetryFrame) => void;
  setPairedFrame: (frame: PairedTelemetryFrame) => void;
  setRunStatus: (status: RunStatus, error?: string | null) => void;
  setExperimentId: (id: string) => void;
  setExperimentSummary: (summary: ExperimentSummary | null) => void;
  setPairedSummary: (summary: Record<string, unknown> | null) => void;
  setPairedMode: (isPaired: boolean, ctrlA?: string, ctrlB?: string) => void;
  selectNoise: (noise: any) => void;
  toggleDebugOverlay: (val?: any) => void;
  togglePerceptionDebug: (val?: any) => void;
  togglePresentationMode: (val?: any) => void;
  toggleProvenanceDrawer: (val?: any) => void;
  loadReplayTrace: (frames: ResearchTelemetryFrame[]) => void;
  setReplayIndex: (index: number) => void;
  setIsReplaying: (val: boolean) => void;
  setReplayState: (patch: Partial<ReplayState>) => void;
  setIsWsConnected: (connected: boolean) => void;
  resetRun: () => void;
}

const MAX_HISTORY = 300;

const defaultScenario: ResearchScenario = {
  id: "test_clean_balanced_01",
  scenario_id: "test_clean_balanced_01",
  name: "Test: Clean Balanced Arterial",
  split: "test",
  scenario_hash: "sha256:test_clean_balanced_01",
  duration_steps: 1200,
  duration_seconds: 120,
  yaml_file: "test_clean_balanced_01.yaml",
  exists: true,
  traffic_density: "medium",
  red_duration: 3.0,
  base_lambda: 0.4,
  description: "Balanced 4-way test arterial with nominal demand (frozen IEEE test split)",
};

export const useResearchStore = create<ResearchState>((set) => ({
  activeScenario: defaultScenario,
  activeController: { id: "flowsync_uq", name: "FlowSync-UQ" },
  activeSeed: 1101,
  activeNoisePreset: "clean",
  activeNoise: {
    id: "clean",
    name: "Clean Baseline",
    type: "NONE",
    intensity: 0.0,
    desc: "Zero corruption on camera sensors",
  },
  speedMultiplier: 1.0,
  experimentId: "exp_live_active",

  isWsConnected: false,
  runStatus: "idle",
  errorMessage: null,
  currentFrame: null,
  history: [],

  isPairedMode: false,
  controllerA: "d3qn",
  controllerB: "flowsync_uq",
  pairedFrame: null,
  pairedHistory: [],
  pairedSummary: null,

  experimentSummary: null,
  showProvenanceDrawer: false,

  debugOverlay: false,
  showPerceptionDebug: false,
  presentationMode: false,

  replayFrames: [],
  replayIndex: 0,
  isReplaying: false,
  replayState: {
    isPlaying: false,
    speed: 1.0,
    currentStep: 0,
    totalSteps: 600,
  },

  setConfig: (config) =>
    set((state) => ({
      activeScenario: config.scenario
        ? ({ ...config.scenario, id: config.scenario.id || config.scenario.scenario_id } as ResearchScenario)
        : state.activeScenario,
      activeController: config.controller !== undefined ? config.controller : state.activeController,
      activeSeed: config.seed !== undefined ? config.seed : state.activeSeed,
      activeNoisePreset: config.noisePreset !== undefined ? config.noisePreset : state.activeNoisePreset,
    })),

  setSpeedMultiplier: (speed) => set({ speedMultiplier: Math.max(0.1, Math.min(10.0, speed)) }),

  setExperimentId: (id) => set({ experimentId: id }),

  selectNoise: (noise) =>
    set({
      activeNoise: noise,
      activeNoisePreset: noise.id as NoisePresetKey,
    }),

  setFrame: (frame) =>
    set((state) => {
      const nextHistory = [...state.history, frame];
      const trimmed =
        nextHistory.length > MAX_HISTORY
          ? nextHistory.slice(-MAX_HISTORY)
          : nextHistory;
      const shouldPromote = state.runStatus === "idle" || state.runStatus === "starting";
      return {
        currentFrame: frame,
        history: trimmed,
        runStatus: shouldPromote ? "running" : state.runStatus,
      };
    }),

  setPairedFrame: (frame) =>
    set((state) => {
      const nextPaired = [...state.pairedHistory, frame];
      const trimmed =
        nextPaired.length > MAX_HISTORY
          ? nextPaired.slice(-MAX_HISTORY)
          : nextPaired;
      const shouldPromote = state.runStatus === "idle" || state.runStatus === "starting";
      return {
        pairedFrame: frame,
        pairedHistory: trimmed,
        runStatus: shouldPromote ? "running" : state.runStatus,
      };
    }),

  setRunStatus: (status, error = null) => set({ runStatus: status, errorMessage: error }),

  setExperimentSummary: (summary) => set({ experimentSummary: summary }),

  setPairedSummary: (summary) => set({ pairedSummary: summary }),

  setPairedMode: (isPaired, ctrlA = "d3qn", ctrlB = "flowsync_uq") =>
    set({
      isPairedMode: isPaired,
      controllerA: ctrlA,
      controllerB: ctrlB,
      pairedFrame: null,
      pairedHistory: [],
      pairedSummary: null,
    }),

  toggleDebugOverlay: (val) =>
    set((s) => {
      const next = typeof val === "boolean" ? val : !s.debugOverlay;
      return { debugOverlay: next, showPerceptionDebug: next };
    }),

  togglePerceptionDebug: (val) =>
    set((s) => {
      const next = typeof val === "boolean" ? val : !s.showPerceptionDebug;
      return { showPerceptionDebug: next, debugOverlay: next };
    }),

  togglePresentationMode: (val) =>
    set((s) => ({ presentationMode: typeof val === "boolean" ? val : !s.presentationMode })),

  toggleProvenanceDrawer: (val) =>
    set((s) => ({ showProvenanceDrawer: typeof val === "boolean" ? val : !s.showProvenanceDrawer })),

  loadReplayTrace: (frames) =>
    set({
      replayFrames: frames,
      replayIndex: 0,
      isReplaying: true,
      currentFrame: frames[0] ?? null,
      history: frames.slice(0, 1),
    }),

  setReplayIndex: (index) =>
    set((state) => {
      const clamped = Math.max(0, Math.min(state.replayFrames.length - 1, index));
      return {
        replayIndex: clamped,
        currentFrame: state.replayFrames[clamped] ?? null,
        history: state.replayFrames.slice(Math.max(0, clamped - MAX_HISTORY), clamped + 1),
      };
    }),

  setIsReplaying: (val) => set({ isReplaying: val }),

  setReplayState: (patch) =>
    set((state) => ({
      replayState: { ...state.replayState, ...patch },
    })),

  setIsWsConnected: (connected) => set({ isWsConnected: connected }),

  resetRun: () =>
    set({
      runStatus: "idle",
      errorMessage: null,
      currentFrame: null,
      history: [],
      pairedFrame: null,
      pairedHistory: [],
      pairedSummary: null,
      experimentSummary: null,
      replayFrames: [],
      replayIndex: 0,
      isReplaying: false,
    }),
}));
