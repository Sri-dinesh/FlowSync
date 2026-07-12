from typing import Dict, List, Optional
from pydantic import BaseModel

class VehicleState(BaseModel):
    id: str
    lane: str          # direction: "north" | "south" | "east" | "west"
    turn: str          # "straight" | "left" | "right"
    position: float    # 0.0 → 1.0
    speed: float
    state: str         # "moving" | "waiting" | "passed"
    wait_time: float
    is_emergency: bool = False
    # Precomputed world coordinates for Three.js (server does the math once)
    world_x: float
    world_z: float

class SignalState(BaseModel):
    current_phase: int              # 0-3
    phase_label: str                # "NS_GREEN" | "EW_GREEN" | "NS_LEFT" | "EW_LEFT"
    color_per_lane: Dict[str, str]  # {"north": "green", "south": "green", ...}
    time_in_phase: float            # seconds
    phase_duration: float           # total duration of current phase
    is_transitioning: bool          # True during yellow/red
    pending_phase: Optional[int]    # next phase if transitioning

class QueueState(BaseModel):
    length: int
    max_capacity: int = 10
    occupancy_pct: float            # length / max_capacity * 100

class MetricsState(BaseModel):
    avg_wait_time: float
    max_wait_time: float
    throughput_total: int
    vehicles_in_sim: int
    congestion_level: str           # "low" | "moderate" | "high" | "critical"

class RLState(BaseModel):
    reward: float
    cumulative_reward: float
    epsilon: float
    last_action: int
    action_label: str
    q_values: List[float]           # [q0, q1, q2, q3] — all 4 action values
    is_exploring: bool              # True if this action was random (epsilon)

class SimulationFrame(BaseModel):
    # Meta
    timestep: int
    episode: int
    mode: str                       # "fixed" | "ai" | "manual"
    simulation_id: Optional[str]

    # Core data
    signal: SignalState
    queues: Dict[str, QueueState]   # {"north": QueueState, ...}
    vehicles: List[VehicleState]
    metrics: MetricsState
    rl: Optional[RLState]           # None in fixed/manual mode

    frame_type: str = "simulation"

PHASE_LABELS = {0: "NS_GREEN", 1: "EW_GREEN", 2: "NS_LEFT", 3: "EW_LEFT"}
PHASE_GREEN_DIRS = {
    0: ["north", "south"],
    1: ["east", "west"],
    2: ["north", "south"],
    3: ["east", "west"],
}

def _get_congestion_level(avg_wait: float) -> str:
    if avg_wait < 5: return "low"
    if avg_wait < 15: return "moderate"
    if avg_wait < 30: return "high"
    return "critical"

def _lane_to_world(lane: str, position: float) -> tuple[float, float]:
    """Convert lane direction + position to world X,Z coordinates."""
    # Intersection center at (0, 0)
    # North/South lanes run along Z axis
    # East/West lanes run along X axis
    road_offset = 1.0  # lane center offset from road center
    if lane == "north":
        return (-road_offset, 8.0 - position * 8.0)
    elif lane == "south":
        return (road_offset, -8.0 + position * 8.0)
    elif lane == "east":
        return (8.0 - position * 8.0, -road_offset)
    elif lane == "west":
        return (-8.0 + position * 8.0, road_offset)
    return (0.0, 0.0)

def _build_obs_from_intersection(intersection):
    # Local helper for when agent requires Q-value inference
    queues = intersection.get_queue_lengths()
    signal = intersection.signal
    total_vehicles = intersection.get_total_waiting()
    pending_phase = (
        signal.pending_phase
        if hasattr(signal, 'pending_phase') and signal.pending_phase is not None
        else signal.current_phase
    )
    import numpy as np
    return np.array([
        float(queues.get("north", 0)),
        float(queues.get("south", 0)),
        float(queues.get("east", 0)),
        float(queues.get("west", 0)),
        float(signal.current_phase),
        float(signal.time_in_phase),
        float(total_vehicles),
        float(pending_phase),
    ], dtype=np.float32)

def build_frame(
    intersection,
    mode: str,
    episode: int = 0,
    simulation_id: Optional[str] = None,
    agent=None,
    last_reward: float = 0.0,
    cumulative_reward: float = 0.0,
    epsilon: float = 0.0,
    last_action: int = 0,
    was_exploring: bool = False,
    # Support old keyword arguments mapping
    reward: Optional[float] = None,
) -> SimulationFrame:
    if reward is not None:
        last_reward = reward

    signal = intersection.signal
    queues_raw = intersection.get_queue_lengths()
    avg_wait = intersection.get_avg_wait_time()
    max_wait = max(
        (v.wait_time for vehicles in intersection.lanes.values() for v in vehicles
         if v.state != "passed"),
        default=0.0
    )

    # Signal state
    green_dirs = PHASE_GREEN_DIRS.get(signal.current_phase, [])
    all_dirs = ["north", "south", "east", "west"]
    color_per_lane = {}
    for d in all_dirs:
        if signal.color.name == "YELLOW":
            color_per_lane[d] = "yellow"
        elif d in green_dirs and signal.color.name == "GREEN":
            color_per_lane[d] = "green"
        else:
            color_per_lane[d] = "red"

    signal_state = SignalState(
        current_phase=signal.current_phase,
        phase_label=PHASE_LABELS[signal.current_phase],
        color_per_lane=color_per_lane,
        time_in_phase=round(signal.time_in_phase, 2),
        phase_duration=signal.fixed_duration,
        is_transitioning=signal.color.name in ("YELLOW", "RED"),
        pending_phase=signal.pending_phase,
    )

    # Queue states
    queue_states = {
        direction: QueueState(
            length=count,
            occupancy_pct=round(count / 10 * 100, 1)
        )
        for direction, count in queues_raw.items()
    }

    # Vehicle states with world coords
    all_vehicles = []
    for lane_key, vehicles in intersection.lanes.items():
        direction = lane_key.split("_")[0]
        turn = lane_key.split("_")[1] if "_" in lane_key else "straight"
        for v in vehicles:
            wx, wz = _lane_to_world(direction, v.position)
            all_vehicles.append(VehicleState(
                id=v.id,
                lane=direction,
                turn=turn,
                position=round(v.position, 4),
                speed=round(v.speed, 4),
                state=v.state,
                wait_time=round(v.wait_time, 2),
                is_emergency=getattr(v, 'is_emergency', False),
                world_x=round(wx, 3),
                world_z=round(wz, 3),
            ))

    # Metrics
    total_in_sim = sum(
        1 for vehicles in intersection.lanes.values()
        for v in vehicles if v.state != "passed"
    )
    metrics = MetricsState(
        avg_wait_time=round(avg_wait, 2),
        max_wait_time=round(max_wait, 2),
        throughput_total=intersection.total_passed,
        vehicles_in_sim=total_in_sim,
        congestion_level=_get_congestion_level(avg_wait),
    )

    # RL state (only in AI mode)
    rl_state = None
    if mode == "ai" and agent is not None:
        obs = _build_obs_from_intersection(intersection)
        q_values = agent.get_q_values(obs)
        rl_state = RLState(
            reward=round(last_reward, 3),
            cumulative_reward=round(cumulative_reward, 3),
            epsilon=round(epsilon, 4),
            last_action=last_action,
            action_label=PHASE_LABELS[last_action],
            q_values=[round(q, 3) for q in q_values],
            is_exploring=was_exploring,
        )

    return SimulationFrame(
        timestep=intersection.timestep,
        episode=episode,
        mode=mode,
        simulation_id=simulation_id,
        signal=signal_state,
        queues=queue_states,
        vehicles=all_vehicles,
        metrics=metrics,
        rl=rl_state,
        frame_type="simulation",
    )
