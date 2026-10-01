/**
 * FlowSync Research Mode TypeScript Definitions
 * ==============================================
 * Conforms strictly to the versioned Research Telemetry Contract in Section 27
 * of FlowSync_Frontend_UI_Research_Readiness_Implementation_Plan.md.
 */

export type ScenarioSplit = "train" | "validation" | "test" | "ood";

export interface ResearchScenario {
  id: string;
  scenario_id: string;
  name: string;
  split: ScenarioSplit;
  scenario_hash: string;
  duration_steps: number;
  duration_seconds: number;
  yaml_file: string;
  exists: boolean;
  [key: string]: unknown;
}

export interface ResearchController {
  id: string;
  name: string;
  description: string;
  is_proposed_method: boolean;
  capabilities: {
    handles_continuous_obs?: boolean;
    produces_q_values?: boolean;
    supports_safety_shield?: boolean;
    supports_hysteretic_fallback?: boolean;
    uses_uncertainty_estimation?: boolean;
    [key: string]: unknown;
  };
}

export type NoisePresetKey =
  | "clean"
  | "miss_05"
  | "miss_10"
  | "miss_20"
  | "miss_30"
  | "miss_40"
  | "burst_occlusion"
  | "latency_500ms"
  | "combined_stress";

export interface NoisePreset {
  key: NoisePresetKey;
  label: string;
  profile: {
    name: string;
    miss_rate: number;
    burst_miss_prob: number;
    burst_miss_duration: number;
    false_positive_lambda: number;
    jitter_std: number;
    latency_ms: number;
    [key: string]: unknown;
  };
}

export interface SignalState {
  current_phase: number;
  requested_phase: number;
  executed_phase: number;
  fsm_state: "MIN_GREEN" | "YELLOW_CLEARANCE" | "ALL_RED_CLEARANCE" | "IDLE" | string;
  transition_remaining_s: number;
  green_elapsed_s: number;
  min_green_remaining_s: number;
}

export interface PolicyState {
  q_values: number[]; // [q0, q1, q2, q3]
  proposed_action: number;
  valid_actions: boolean[];
  is_exploring: boolean;
  epsilon: number;
}

export interface UncertaintyState {
  score: number;
  composite_u?: number;
  threshold_high: number; // default 0.65
  threshold_low: number;  // default 0.50
  detector: number;
  tracking: number;
  flicker: number;
  occlusion: number;
  observation_age_s: number;
  [key: string]: unknown;
}

export interface SupervisorState {
  mode: "d3qn" | "fallback" | "nominal" | string;
  reason: string;
  fallback_action: number | null;
  active_controller: string;
  dwell_remaining_s: number;
  [key: string]: unknown;
}

export interface SafetyState {
  shield_override: boolean;
  fsm_deferred: boolean;
  reason: string;
  premature_switch_attempts: number;
  executed_violations: number; // Always 0 under PhysicalSignalFSM
  [key: string]: unknown;
}

export interface ResearchMetricsState {
  mean_delay_s: number;
  delay_mean_s?: number;
  p95_delay_s: number;
  delay_p95_s?: number;
  queue_area_veh_s: number;
  throughput: number;
  throughput_total_veh?: number;
  service_rate: number;
  service_rate_vph?: number;
  starvation_events: number;
  starvation_count?: number;
  spillback_incidents: number;
  spillback_seconds?: number;
  max_queue: number;
  queue_length_north?: number;
  queue_length_south?: number;
  queue_length_east?: number;
  queue_length_west?: number;
  [key: string]: unknown;
}

export type VehicleDetectionState =
  | "detected"
  | "missed_ground_truth"
  | "false_positive"
  | "uncertain_track";

export interface ResearchVehicleState {
  id: string;
  lane: string;
  turn: "straight" | "left" | "right";
  position: number;
  state: string;
  wait_time: number;
  is_emergency?: boolean;
  detection_state?: VehicleDetectionState;
}

export interface PerceptionHealthState {
  camera_health: "HEALTHY" | "DEGRADED" | "OCCLUDED" | "OFFLINE";
  detected_count: number;
  ground_truth_count: number;
  missed_count: number;
  false_positive_count: number;
  occluded_count: number;
  cv_latency_ms: number;
  track_confidence_avg: number;
  noise_type: string;
  noise_intensity: number;
  active_cues: string[];
}

export interface ResearchTelemetryFrame {
  type: "research_frame";
  experiment_id: string;
  scenario_id: string;
  scenario_hash: string;
  seed: number;
  controller: string;
  model_hash: string;
  step: number;
  sim_time_s: number;
  sim_time?: number;
  signal: SignalState;
  policy: PolicyState;
  uncertainty: UncertaintyState;
  supervisor: SupervisorState;
  safety: SafetyState;
  metrics: ResearchMetricsState;
  vehicles: ResearchVehicleState[];
  perception?: PerceptionHealthState;
  actions?: Record<string, any>;
  fsm?: Record<string, any>;
  [key: string]: unknown;
}

export interface PairedControllerState {
  name: string;
  phase: number;
  fsm_state: string;
  mean_delay: number;
  queue_area: number;
  throughput: number;
  uncertainty?: number;
  fallback_active?: boolean;
  vehicles: ResearchVehicleState[];
}

export interface PairedTelemetryFrame {
  type: "paired_telemetry";
  step: number;
  sim_time_s: number;
  scenario_id: string;
  seed: number;
  trace_hash: string;
  controller_a: PairedControllerState;
  controller_b: PairedControllerState;
  deltas: {
    delay_delta: number;      // delay_b - delay_a
    queue_area_delta: number;
    throughput_delta: number; // throughput_b - throughput_a
    starvation_delta?: number;
  };
}

export interface ExperimentSummary {
  experiment_id: string;
  scenario_id: string;
  scenario_hash: string;
  controller: string;
  seed: number;
  num_steps: number;
  avg_delay: number;
  p95_delay: number;
  queue_area: number;
  throughput: number;
  service_rate: number;
  starvation_count: number;
  premature_switch_attempts: number;
  executed_violations: number;
  status: "COMPLETED" | "FAILED" | "INTERRUPTED";
}

export interface ExperimentProvenance {
  experiment_id: string;
  scenario_id: string;
  scenario_hash: string;
  seed: number;
  controller: string;
  model_hash: string;
  config_hash?: string;
  noise_profile: Record<string, unknown>;
  git_commit: string;
  environment_version: string;
  timestamp: string;
  status: string;
}
