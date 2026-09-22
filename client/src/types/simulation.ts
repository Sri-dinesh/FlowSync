export type SimulationMode = "fixed" | "ai" | "manual" | "greedy";

export interface VehicleState {
  id: string;
  lane: string;
  turn: "straight" | "left" | "right";
  position: number;
  state: string;
  wait_time: number;
  is_emergency?: boolean;
}

export interface RLInfo {
  reward: number;
  cumulative_reward: number;
  epsilon: number;
  last_action: number;
  action_label: string;
  q_values: number[];   // [q0, q1, q2, q3] — all 4 phase Q-values
  is_exploring: boolean;
}

export interface SimulationFrame {
  timestep: number;
  mode: SimulationMode | string;
  signal_phase: number;
  signal_color: string;
  vehicles: VehicleState[];
  queue_lengths: Record<string, number>;
  avg_wait_time: number;
  throughput: number;
  reward: number;
  episode: number;
  rl?: RLInfo | null;   // only populated in AI mode
}

export interface TrainingMetric {
  episode: number;
  total_reward: number;
  avg_wait_time: number;
  throughput: number;
  epsilon: number;
  loss: number | null;
  is_training: boolean;
  steps?: number;
  buffer_ready?: boolean;
}

export interface EpisodeRecord {
  id: string;
  simulationId: string;
  episodeNumber: number;
  totalReward: number;
  avgWaitTime: number;
  throughput: number;
  epsilon: number;
  loss: number | null;
  steps: number;
}

// ─── Scenario Builder ─────────────────────────────────────────────────────────

export interface Scenario {
  id: string;
  name: string;
  seed: number;
  spawn_lambda: number;
  duration_seconds: number;
  created_at: string;
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  model_id: string;
  model_episode: number;
  controller: string;
  scenario_hash: string;
  avg_wait_time: number;
  total_passed: number;
  max_queue: number;
  override_rate: number;
  ran_at: string;
}

export interface ScenarioBenchmarkResult {
  avg_wait_time: number;
  total_passed: number;
  max_queue: number;
  override_rate: number;
  duration_seconds: number;
}

export interface ScenarioBenchmarkResults {
  type: "scenario_benchmark_results";
  scenario_id: string;
  model_id: string;
  model_episode: number;
  scenario_hash: string;
  benchmark_seed: number;
  duration_seconds: number;
  results: Record<string, ScenarioBenchmarkResult>;
}

