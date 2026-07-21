"""
Pydantic schema for CityFrame — the WebSocket message sent to the city simulation client.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class CitySignalState(BaseModel):
    current_phase: int
    phase_label: str
    color: str          # "green" | "yellow" | "red"
    time_in_phase: float
    is_transitioning: bool


class CityQueueState(BaseModel):
    north: int
    south: int
    east: int
    west: int


class CityVehicleState(BaseModel):
    id: str
    lane: str           # approach direction
    turn: str
    position: float     # 0.0 → 1.0
    state: str          # "moving" | "waiting" | "passed"
    wait_time: float
    world_x: float
    world_z: float


class CityIntersectionState(BaseModel):
    id: str                         # "A" | "B" | "C" | "D"
    signal: CitySignalState
    queue_lengths: CityQueueState
    avg_wait_time: float
    total_waiting: int
    vehicles: List[CityVehicleState]
    q_values: Optional[List[float]] = None   # DQN Q-values (AI mode only)
    # Grid position for Three.js layout
    grid_x: float       # world X of intersection center
    grid_z: float       # world Z of intersection center


class RoadVehicleState(BaseModel):
    id: str
    from_intersection: str
    to_intersection: str
    progress: float         # 0.0 → 1.0 along the road segment
    world_x: float
    world_z: float


class CityMetrics(BaseModel):
    avg_wait_time: float
    total_throughput: int
    active_vehicles: int
    road_vehicles: int
    congestion_level: str       # "low" | "moderate" | "high" | "critical"
    worst_intersection: str
    best_intersection: str


class CityFrame(BaseModel):
    frame_type: str = "city_simulation"
    timestep: int
    mode: str               # "fixed" | "greedy" | "ai"
    city_metrics: CityMetrics
    intersections: Dict[str, CityIntersectionState]
    road_vehicles: List[RoadVehicleState]


# ── Phase metadata (mirrors single-intersection schema) ───────────────────────

PHASE_LABELS = {0: "NS_GREEN", 1: "EW_GREEN", 2: "NS_LEFT", 3: "EW_LEFT"}

PHASE_GREEN_DIRS = {
    0: ["north", "south"],
    1: ["east", "west"],
    2: ["north", "south"],
    3: ["east", "west"],
}

# World positions of the 4 intersection centers in Three.js coords
# Grid spacing = 20 units
INTERSECTION_WORLD_POS = {
    "A": (-10.0, -10.0),   # (world_x, world_z)  top-left
    "B": ( 10.0, -10.0),   # top-right
    "C": (-10.0,  10.0),   # bottom-left
    "D": ( 10.0,  10.0),   # bottom-right
}

LANE_LOCAL_OFFSETS = {
    "north": (-1.0,  8.0),
    "south": ( 1.0, -8.0),
    "east":  ( 8.0, -1.0),
    "west":  (-8.0,  1.0),
}


def _lane_to_world(iid: str, lane: str, position: float):
    """
    Convert a lane position (0.0-1.0) to world (x, z) coordinates.
    position=0.0 → far end of approach road
    position=1.0 → intersection center
    """
    cx, cz = INTERSECTION_WORLD_POS[iid]
    road_len = 6.0   # half-road length from center
    lateral = 1.0    # lane offset from road center

    if lane == "north":
        wx = cx - lateral
        wz = cz - road_len + position * road_len
    elif lane == "south":
        wx = cx + lateral
        wz = cz + road_len - position * road_len
    elif lane == "east":
        wx = cx + road_len - position * road_len
        wz = cz - lateral
    elif lane == "west":
        wx = cx - road_len + position * road_len
        wz = cz + lateral
    else:
        wx, wz = cx, cz

    return round(wx, 3), round(wz, 3)


def _road_vehicle_world(rv) -> tuple:
    """Compute the world position of a road vehicle traveling between intersections.
    Starts 8 units away from the source intersection and ends 8 units away from destination.
    """
    ax, az = INTERSECTION_WORLD_POS[rv.from_intersection]
    bx, bz = INTERSECTION_WORLD_POS[rv.to_intersection]
    
    # Vector from A to B
    dx, dz = bx - ax, bz - az
    dist = (dx**2 + dz**2)**0.5
    if dist == 0:
        return ax, az
    
    # Normalized direction
    nx, nz = dx / dist, dz / dist
    
    # Start and end points (8 units from center)
    offset = 8.0
    start_x, start_z = ax + nx * offset, az + nz * offset
    end_x, end_z = bx - nx * offset, bz - nz * offset
    
    wx = start_x + (end_x - start_x) * rv.progress
    wz = start_z + (end_z - start_z) * rv.progress
    return round(wx, 3), round(wz, 3)


def build_city_frame(city_network, mode: str, shared_agent=None) -> CityFrame:
    """Build a complete CityFrame from the current city network state."""

    metrics_raw = city_network.get_city_metrics()
    city_metrics = CityMetrics(
        avg_wait_time=metrics_raw["avg_wait_time"],
        total_throughput=metrics_raw["total_throughput"],
        active_vehicles=metrics_raw["active_vehicles"],
        road_vehicles=metrics_raw["road_vehicles"],
        congestion_level=metrics_raw["congestion_level"],
        worst_intersection=metrics_raw["worst_intersection"],
        best_intersection=metrics_raw["best_intersection"],
    )

    inter_states: Dict[str, CityIntersectionState] = {}
    for iid, intersection in city_network.intersections.items():
        signal = intersection.signal
        queues = intersection.get_queue_lengths()
        cx, cz = INTERSECTION_WORLD_POS[iid]

        # Determine color per lane
        green_dirs = PHASE_GREEN_DIRS.get(signal.current_phase, [])
        if signal.color.name == "YELLOW":
            color = "yellow"
        elif signal.color.name == "GREEN":
            color = "green"
        else:
            color = "red"

        city_signal = CitySignalState(
            current_phase=signal.current_phase,
            phase_label=PHASE_LABELS[signal.current_phase],
            color=color,
            time_in_phase=round(signal.time_in_phase, 2),
            is_transitioning=signal.color.name in ("YELLOW", "RED"),
        )

        # Vehicles
        vehicles: list[CityVehicleState] = []
        for lane_key, lane_queue in intersection.lanes.items():
            direction = lane_key.split("_")[0]
            turn = lane_key.split("_")[1] if "_" in lane_key else "straight"
            for v in lane_queue:
                wx, wz = _lane_to_world(iid, direction, v.position)
                vehicles.append(CityVehicleState(
                    id=v.id,
                    lane=lane_key.split('_')[0],
                    turn=turn,
                    position=round(v.position, 4),
                    state=v.state,
                    wait_time=round(v.wait_time, 2),
                    world_x=wx,
                    world_z=wz,
                ))

        # Q-values (AI mode only)
        q_vals = None
        if mode == "ai" and shared_agent is not None:
            obs = city_network.build_obs(iid)
            q_vals = [round(q, 3) for q in shared_agent.get_q_values(obs)]

        inter_states[iid] = CityIntersectionState(
            id=iid,
            signal=city_signal,
            queue_lengths=CityQueueState(
                north=queues.get("north", 0),
                south=queues.get("south", 0),
                east=queues.get("east", 0),
                west=queues.get("west", 0),
            ),
            avg_wait_time=round(intersection.get_avg_wait_time(), 2),
            total_waiting=intersection.get_total_waiting(),
            vehicles=vehicles,
            q_values=q_vals,
            grid_x=cx,
            grid_z=cz,
        )

    # Road vehicles
    road_veh_states: list[RoadVehicleState] = []
    for rv in city_network.road_vehicles:
        wx, wz = _road_vehicle_world(rv)
        road_veh_states.append(RoadVehicleState(
            id=rv.id,
            from_intersection=rv.from_intersection,
            to_intersection=rv.to_intersection,
            progress=round(rv.progress, 3),
            world_x=wx,
            world_z=wz,
        ))

    return CityFrame(
        timestep=city_network.timestep,
        mode=mode,
        city_metrics=city_metrics,
        intersections=inter_states,
        road_vehicles=road_veh_states,
    )
