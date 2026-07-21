export type CityMode = "fixed" | "greedy" | "ai";
export type CongestionLevel = "low" | "moderate" | "high" | "critical";
export type SignalColor = "green" | "yellow" | "red";

export interface CitySignalState {
  current_phase: number;    // 0-3
  phase_label: string;      // "NS_GREEN" | "EW_GREEN" | ...
  color: SignalColor;
  time_in_phase: number;
  is_transitioning: boolean;
}

export interface CityQueueState {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface CityVehicleState {
  id: string;
  lane: string;
  turn: "straight" | "left" | "right";
  position: number;
  state: string;
  wait_time: number;
  world_x: number;
  world_z: number;
  prev_turn?: "straight" | "left" | "right";
  next_turn?: "straight" | "left" | "right";
}

export interface CityIntersectionState {
  id: string;           // "A" | "B" | "C" | "D"
  signal: CitySignalState;
  queue_lengths: CityQueueState;
  avg_wait_time: number;
  total_waiting: number;
  vehicles: CityVehicleState[];
  q_values?: number[] | null;
  grid_x: number;
  grid_z: number;
}

export interface RoadVehicleState {
  id: string;
  from_intersection: string;
  to_intersection: string;
  progress: number;
  world_x: number;
  world_z: number;
  prev_turn: "straight" | "left" | "right";
  next_turn: "straight" | "left" | "right";
}

export interface CityMetrics {
  avg_wait_time: number;
  total_throughput: number;
  active_vehicles: number;
  road_vehicles: number;
  congestion_level: CongestionLevel;
  worst_intersection: string;
  best_intersection: string;
}

export interface ComparisonProgress {
  running: boolean;
  current_mode?: CityMode;
  elapsed?: number;
  total?: number;
  mode_index?: number;
  total_modes?: number;
}

export interface ComparisonResult {
  avg_wait_time: number;
  throughput: number;
}

export interface CityFrame {
  frame_type: "city_simulation";
  timestep: number;
  mode: CityMode;
  city_metrics: CityMetrics;
  intersections: Record<string, CityIntersectionState>;
  road_vehicles: RoadVehicleState[];
  comparison_progress?: ComparisonProgress;
}

export interface ComparisonResultsFrame {
  frame_type: "comparison_results";
  results: Record<string, ComparisonResult>;
}
