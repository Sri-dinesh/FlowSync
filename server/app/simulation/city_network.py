"""
CityNetwork — 2×2 grid of 4 intersections.

Layout:
    [A] ═══ [B]
     ║           ║
    [C] ═══ [D]

A = top-left,  B = top-right
C = bot-left,  D = bot-right

Inter-intersection connections:
    A ↔ B  (east/west)
    C ↔ D  (east/west)
    A ↔ C  (north/south)
    B ↔ D  (north/south)
"""

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

from .intersection import Intersection
from .vehicle import DEFAULT_SPEED, Vehicle

# Road travel time between intersections (seconds at 10 Hz → ticks)
ROAD_TRAVEL_TIME = 3.0   # seconds to cross a connecting road segment
ROAD_TICKS = int(ROAD_TRAVEL_TIME / 0.1)   # 30 ticks

MAX_QUEUE = 12  # per-lane cap at city intersections

# Which adjacent intersection + entry direction when a vehicle exits a given direction
# (from_intersection, exit_dir) → (to_intersection, entry_dir)
ROAD_CONNECTIONS: Dict[Tuple[str, str], Tuple[str, str]] = {
    # A's exits
    ("A", "east"):  ("B", "west"),
    ("A", "south"): ("C", "north"),
    # B's exits
    ("B", "west"):  ("A", "east"),
    ("B", "south"): ("D", "north"),
    # C's exits
    ("C", "north"): ("A", "south"),
    ("C", "east"):  ("D", "west"),
    # D's exits
    ("D", "north"): ("B", "south"),
    ("D", "west"):  ("C", "east"),
}

# External exits (when a vehicle leaves the city boundary)
EXTERNAL_EXITS: Dict[Tuple[str, str], str] = {
    ("A", "north"): "north_exit",
    ("A", "west"):  "west_exit",
    ("B", "north"): "north_exit",
    ("B", "east"):  "east_exit",
    ("C", "south"): "south_exit",
    ("C", "west"):  "west_exit",
    ("D", "south"): "south_exit",
    ("D", "east"):  "east_exit",
}

# Which directions map to which intersection outputs
# A lane_key like "north_straight" exits the intersection going SOUTH (opposite)
EXIT_DIR_MAP: Dict[str, str] = {
    "north_straight": "south",
    "south_straight": "north",
    "east_straight":  "west",
    "west_straight":  "east",
    "north_left":     "east",
    "north_right":    "west",
    "south_left":     "west",
    "south_right":    "east",
    "east_left":      "south",
    "east_right":     "north",
    "west_left":      "north",
    "west_right":     "south",
}


class RoadVehicle:
    """A vehicle currently traveling between two intersections on a road segment."""

    def __init__(
        self,
        vehicle_id: str,
        from_intersection: str,
        to_intersection: str,
        entry_dir: str,     # direction it will enter the destination intersection from
        wait_time: float = 0.0,
        prev_turn: str = "straight",
        next_turn: str = "straight",
    ) -> None:
        self.id = vehicle_id
        self.from_intersection = from_intersection
        self.to_intersection = to_intersection
        self.entry_dir = entry_dir      # e.g. "west" → enters B from the west
        self.progress: float = 0.0      # 0.0 → 1.0
        self.wait_time = wait_time
        self.ticks_traveled = 0
        self.prev_turn = prev_turn
        self.next_turn = next_turn

    def tick(self, dt: float) -> bool:
        """Returns True when the vehicle has reached the destination intersection."""
        self.progress = min(1.0, self.progress + dt / ROAD_TRAVEL_TIME)
        self.ticks_traveled += 1
        return self.progress >= 1.0


class CityNetwork:
    """
    Manages a 2×2 grid of 4 intersections.
    Handles:
      - Independent traffic signal control per intersection
      - Vehicle transfers between intersections via road segments
      - City-wide metrics aggregation
    """

    def __init__(self, spawn_lambda: float = 0.3, red_duration: float = 3.0) -> None:
        self.intersections: Dict[str, Intersection] = {
            "A": Intersection(red_duration=red_duration, spawn_lambda=0.0),  # city spawner handles it
            "B": Intersection(red_duration=red_duration, spawn_lambda=0.0),
            "C": Intersection(red_duration=red_duration, spawn_lambda=0.0),
            "D": Intersection(red_duration=red_duration, spawn_lambda=0.0),
        }
        # Disable internal spawners — city spawner (city_spawner.py) handles spawning
        for inter in self.intersections.values():
            inter.spawner.set_enabled(False)

        self.road_vehicles: List[RoadVehicle] = []
        self.timestep: int = 0
        self.total_city_throughput: int = 0   # vehicles that exited the city
        self._spawn_lambda = spawn_lambda

    # ── Observation builder (matches existing single-intersection obs exactly) ──

    def build_obs(self, intersection_id: str) -> np.ndarray:
        """Build the 20-dim observation for one intersection (same format as single-intersection training)."""
        intersection = self.intersections[intersection_id]
        movement_queues = intersection.get_movement_queues()
        signal = intersection.signal
        MAX_CAP = 10.0

        movements = [
            movement_queues.get("north_straight", 0) / MAX_CAP,
            movement_queues.get("north_left",     0) / MAX_CAP,
            movement_queues.get("north_right",    0) / MAX_CAP,
            movement_queues.get("south_straight", 0) / MAX_CAP,
            movement_queues.get("south_left",     0) / MAX_CAP,
            movement_queues.get("south_right",    0) / MAX_CAP,
            movement_queues.get("east_straight",  0) / MAX_CAP,
            movement_queues.get("east_left",      0) / MAX_CAP,
            movement_queues.get("east_right",     0) / MAX_CAP,
            movement_queues.get("west_straight",  0) / MAX_CAP,
            movement_queues.get("west_left",      0) / MAX_CAP,
            movement_queues.get("west_right",     0) / MAX_CAP,
        ]

        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[signal.current_phase] = 1.0

        time_norm = min(signal.time_in_phase / signal.MAX_GREEN_TIME, 1.0)
        is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0

        dest_map = {
            "north_straight": "south", "north_left": "east",  "north_right": "west",
            "south_straight": "north", "south_left": "west",  "south_right": "east",
            "east_straight":  "west",  "east_left":  "south", "east_right":  "north",
            "west_straight":  "east",  "west_left":  "north", "west_right":  "south",
        }
        outgoing = intersection.get_outgoing_counts()
        total_pressure = 0.0
        for movement, dest in dest_map.items():
            incoming = movement_queues.get(movement, 0) / MAX_CAP
            out = outgoing.get(dest, 0) / MAX_CAP
            total_pressure += max(0.0, incoming - out)
        pressure_norm = min(total_pressure / 20.0, 1.0)

        max_starv_norm = min(
            max(signal.starvation_timer.values()) / signal.STARVATION_THRESHOLD, 1.0
        )

        obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm]
        return np.array(obs, dtype=np.float32)

    # ── Greedy action helper ────────────────────────────────────────────────────

    def get_greedy_action(self, intersection_id: str) -> int:
        intersection = self.intersections[intersection_id]
        signal = intersection.signal
        queues = intersection.get_movement_queues()
        PHASE_DIRS = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
        PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}
        phase_counts = {}
        for ph in range(4):
            count = sum(queues.get(f"{d}_{t}", 0) for d in PHASE_DIRS[ph] for t in PHASE_TURNS[ph])
            phase_counts[ph] = count
        best_phase = max(phase_counts, key=lambda p: phase_counts[p])
        return best_phase if signal.can_switch_phase else signal.current_phase

    # ── Tick ───────────────────────────────────────────────────────────────────

    def tick(self, dt: float, mode: str, shared_agent=None) -> None:
        """
        Advance city simulation by one tick (dt seconds).

        1. Tick each intersection (with appropriate control mode)
        2. Collect vehicles that have 'passed' from intersections
        3. Route them to road segments or city exits
        4. Advance road vehicles; inject arrived ones into destination intersections
        """
        # --- Step 1: Tick each intersection ---
        all_passed_vehicles: List[Tuple[str, Vehicle]] = []
        for iid, intersection in self.intersections.items():
            if mode == "ai" and shared_agent is not None:
                obs = self.build_obs(iid)
                action = shared_agent.select_action(obs, epsilon=0.0)
                passed = intersection.tick(dt=dt, action=action)
            elif mode == "greedy":
                action = self.get_greedy_action(iid)
                passed = intersection.tick(dt=dt, action=action)
            else:
                # fixed timer — intersection handles it internally
                passed = intersection.tick(dt=dt, action=None)
            
            for v in (passed or []):
                all_passed_vehicles.append((iid, v))

        # --- Step 2: Collect passed vehicles and route them ---
        self._route_passed_vehicles(dt, all_passed_vehicles)

        # --- Step 3: Advance road vehicles ---
        arrived: List[RoadVehicle] = []
        still_traveling: List[RoadVehicle] = []

        for rv in self.road_vehicles:
            reached = rv.tick(dt)
            if reached:
                arrived.append(rv)
            else:
                still_traveling.append(rv)

        # --- Step 4: Inject arrived vehicles into destination intersections ---
        for rv in arrived:
            dest = self.intersections.get(rv.to_intersection)
            injected = False
            if dest:
                injected = self._inject_vehicle(dest, rv)
            
            if not injected and dest is not None:
                # Keep it waiting at the end of the road
                rv.progress = 1.0
                still_traveling.append(rv)

        self.road_vehicles = still_traveling
        self.timestep += 1

    def _route_passed_vehicles(self, dt: float, passed_vehicles: List[Tuple[str, Vehicle]]) -> None:
        """
        For each intersection, find all just-passed vehicles and route them:
        - To an adjacent intersection (via a road segment)
        - Or out of the city (city throughput++)
        """
        for iid, vehicle in passed_vehicles:
            lane_key = f"{vehicle.lane}_{vehicle.turn}"
            exit_dir = EXIT_DIR_MAP.get(lane_key)
            if exit_dir is None:
                continue  # unknown lane

            connection_key = (iid, exit_dir)

            if connection_key in ROAD_CONNECTIONS:
                to_inter, entry_dir = ROAD_CONNECTIONS[connection_key]
                next_turn = str(np.random.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25]))
                rv = RoadVehicle(
                    vehicle_id=vehicle.id,
                    from_intersection=iid,
                    to_intersection=to_inter,
                    entry_dir=entry_dir,
                    wait_time=vehicle.wait_time,
                    prev_turn=getattr(vehicle, "turn", "straight"),
                    next_turn=next_turn,
                )
                self.road_vehicles.append(rv)
            else:
                # Exits the city boundary
                self.total_city_throughput += 1

    def _inject_vehicle(self, intersection: Intersection, rv: RoadVehicle) -> bool:
        """Insert an arriving road vehicle into the destination intersection's lane."""
        turn = rv.next_turn
        lane_key = f"{rv.entry_dir}_{turn}"
        lane_queue = intersection.lanes.get(lane_key, [])

        if len(lane_queue) < MAX_QUEUE:
            vehicle = Vehicle(
                id=rv.id,
                lane=rv.entry_dir,
                turn=turn,
                position=0.0,
                wait_time=rv.wait_time,   # carries accumulated wait time
                speed=DEFAULT_SPEED,
                state="waiting",
            )
            lane_queue.append(vehicle)
            intersection._spawned_this_interval += 1
            return True
        return False

    # ── Metrics ────────────────────────────────────────────────────────────────

    def get_city_metrics(self) -> Dict:
        all_waits = []
        total_vehicles = 0
        per_inter: Dict[str, Dict] = {}

        for iid, inter in self.intersections.items():
            q = inter.get_queue_lengths()
            avg_wait = inter.get_avg_wait_time()
            total_w = inter.get_total_waiting()
            total_vehicles += total_w
            if avg_wait > 0:
                all_waits.append(avg_wait)

            per_inter[iid] = {
                "avg_wait_time": round(avg_wait, 2),
                "total_waiting": total_w,
                "queue_lengths": q,
                "signal_phase": inter.signal.current_phase,
                "signal_color": inter.signal.color.value,
                "time_in_phase": round(inter.signal.time_in_phase, 2),
            }

        city_avg_wait = round(sum(all_waits) / len(all_waits), 2) if all_waits else 0.0
        road_vehicles_count = len(self.road_vehicles)

        # Congestion level
        if city_avg_wait < 5:
            congestion = "low"
        elif city_avg_wait < 15:
            congestion = "moderate"
        elif city_avg_wait < 30:
            congestion = "high"
        else:
            congestion = "critical"

        worst_inter = max(per_inter, key=lambda k: per_inter[k]["avg_wait_time"]) if per_inter else "A"
        best_inter  = min(per_inter, key=lambda k: per_inter[k]["avg_wait_time"]) if per_inter else "A"

        return {
            "avg_wait_time": city_avg_wait,
            "total_throughput": self.total_city_throughput,
            "active_vehicles": total_vehicles + road_vehicles_count,
            "road_vehicles": road_vehicles_count,
            "congestion_level": congestion,
            "worst_intersection": worst_inter,
            "best_intersection": best_inter,
            "per_intersection": per_inter,
        }

    def set_spawn_rate(self, lambda_rate: float) -> None:
        self._spawn_lambda = max(0.0, lambda_rate)

    def reset(self) -> None:
        for inter in self.intersections.values():
            inter.reset()
            inter.spawner.set_enabled(False)
        self.road_vehicles.clear()
        self.timestep = 0
        self.total_city_throughput = 0
