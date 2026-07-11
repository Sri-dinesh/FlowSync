export type SimulationMode = "fixed" | "ai" | "manual";

export interface VehicleState {
  id: string;
  lane: string;
  turn: "straight" | "left" | "right";
  position: number;
  state: string;
  wait_time: number;
  is_emergency?: boolean;
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
}

export interface TrainingMetric {
  episode: number;
  total_reward: number;
  avg_wait_time: number;
  throughput: number;
  epsilon: number;
  loss: number | null;
  is_training: boolean;
}
