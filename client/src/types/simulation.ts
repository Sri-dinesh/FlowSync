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

export type ScenarioType = "standard" | "stress" | "held_out" | "sweep";

export interface Scenario {
  id: string;
  name: string;
  seed: number;
  spawn_lambda: number;
  duration_seconds: number;
  created_at: string;
  is_held_out: boolean;
  scenario_type: ScenarioType;
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  model_id: string;
  model_episode: number;
  controller: string;     // "fixed" | "greedy" | "ai"
  scenario_hash: string;
  avg_wait_time: number;
  total_passed: number;
  max_queue: number;
  override_rate: number;
  run_group_id: string;
  median_delay: number;
  p95_delay: number;
  std_delay: number;
  queue_area: number;
  starvation_count: number;
  ran_at: string;
}

/** Per-controller result within a run group */
export interface ScenarioControllerResult {
  avg_wait_time: number;
  total_passed: number;
  max_queue: number;
  override_rate: number;
  median_delay: number;
  p95_delay: number;
  std_delay: number;
  queue_area: number;
  starvation_count: number;
  duration_seconds?: number;
}

/**
 * One full execution group: Fixed + Greedy + AI on the same seed.
 * Returned by /scenarios/{id}/runs/grouped.
 */
export interface ScenarioRunGroup {
  run_group_id: string;
  ran_at: string;
  model_episode: number;
  fixed?:  ScenarioControllerResult;
  greedy?: ScenarioControllerResult;
  ai?:     ScenarioControllerResult;
}

/** Cross-scenario aggregate statistics */
export interface ScenarioAggregateStats {
  total_scenarios: number;
  total_runs: number;
  total_groups: number;
  per_controller: Record<string, {
    mean_wait: number | null;
    std_wait: number | null;
    mean_throughput: number | null;
    mean_starvation: number | null;
  }>;
  dqn_win_rate: number;
  dqn_vs_greedy_delta: number | null;
  dqn_vs_fixed_delta: number | null;
}

/** Broadcast result from WS scenario_benchmark_results event */
export interface ScenarioBenchmarkResult extends ScenarioControllerResult {}

export interface ScenarioBenchmarkResults {
  type: "scenario_benchmark_results";
  scenario_id: string;
  run_group_id: string;
  model_id: string;
  model_episode: number;
  scenario_hash: string;
  benchmark_seed: number;
  duration_seconds: number;
  results: Record<string, ScenarioBenchmarkResult>;
}


