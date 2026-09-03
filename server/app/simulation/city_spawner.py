"""
CitySpawner — spawns vehicles at 8 external entry points of the 2×2 city grid.

Entry points:
    North-of-A, North-of-B  (top edge)
    South-of-C, South-of-D  (bottom edge)
    West-of-A,  West-of-C   (left edge)
    East-of-B,  East-of-D   (right edge)

Each entry point feeds directly into an intersection's approach lane.
"""

from typing import Dict, List
from uuid import uuid4

import numpy as np

from .intersection import Intersection
from .vehicle import DEFAULT_SPEED, Vehicle

MAX_QUEUE = 12

# Maps each external entry point to (intersection_id, approach_direction)
ENTRY_POINTS: Dict[str, tuple] = {
    "north_A": ("A", "north"),
    "north_B": ("B", "north"),
    "south_C": ("C", "south"),
    "south_D": ("D", "south"),
    "west_A":  ("A", "west"),
    "west_C":  ("C", "west"),
    "east_B":  ("B", "east"),
    "east_D":  ("D", "east"),
}


# Pre-defined journey routes per entry point:
# 50% Trans-metropolitan arterials, 25% full ring rotations, 25% perpendicular arterials
ROUTES_BY_ENTRY: Dict[str, List[List[str]]] = {
    "north_A": [
        ["straight", "straight"],               # North -> A -> C -> South exit
        ["straight", "left", "left", "left"],  # Ring: A -> C -> D -> B
        ["left", "straight"],                   # North -> A -> B -> East exit
    ],
    "west_A": [
        ["straight", "straight"],               # West -> A -> B -> East exit
        ["straight", "right", "right", "right"],# Ring: A -> B -> D -> C
        ["right", "straight"],                  # West -> A -> C -> South exit
    ],
    "north_B": [
        ["straight", "straight"],               # North -> B -> D -> South exit
        ["straight", "right", "right", "right"],# Ring: B -> D -> C -> A
        ["right", "straight"],                  # North -> B -> A -> West exit
    ],
    "east_B": [
        ["straight", "straight"],               # East -> B -> A -> West exit
        ["straight", "left", "left", "left"],  # Ring: B -> A -> C -> D
        ["left", "straight"],                   # East -> B -> D -> South exit
    ],
    "south_C": [
        ["straight", "straight"],               # South -> C -> A -> North exit
        ["straight", "right", "right", "right"],# Ring: C -> A -> B -> D
        ["right", "straight"],                  # South -> C -> D -> East exit
    ],
    "west_C": [
        ["straight", "straight"],               # West -> C -> D -> East exit
        ["straight", "left", "left", "left"],  # Ring: C -> D -> B -> A
        ["left", "straight"],                   # West -> C -> A -> North exit
    ],
    "south_D": [
        ["straight", "straight"],               # South -> D -> B -> North exit
        ["straight", "left", "left", "left"],  # Ring: D -> B -> A -> C
        ["left", "straight"],                   # South -> D -> C -> West exit
    ],
    "east_D": [
        ["straight", "straight"],               # East -> D -> C -> West exit
        ["straight", "right", "right", "right"],# Ring: D -> C -> A -> B
        ["right", "straight"],                  # East -> D -> B -> North exit
    ],
}


class CitySpawner:
    """
    Poisson-process vehicle spawner for the 2×2 city grid.
    Spawns vehicles with planned multi-hop itineraries across the city.
    """

    def __init__(self, lambda_rate: float = 0.3) -> None:
        self.lambda_rate = lambda_rate
        self.enabled = False
        self._rng = np.random.default_rng()

    def set_rate(self, lambda_rate: float) -> None:
        self.lambda_rate = max(0.0, lambda_rate)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def set_seed(self, seed: int | None = None) -> None:
        """
        Set seed for deterministic benchmark testing (CRN).
        Pass None to restore natural unseeded stochastic generation.
        """
        if seed is not None:
            self._rng = np.random.default_rng(int(seed))
        else:
            self._rng = np.random.default_rng()

    def spawn(self, dt: float, intersections: Dict[str, Intersection]) -> int:
        """
        Spawn vehicles at each external entry point using a Poisson process.
        Assigns realistic multi-hop routes (arterials and full rotations).
        Returns total number of vehicles spawned this tick.
        """
        if not self.enabled or self.lambda_rate <= 0:
            return 0

        total_spawned = 0
        per_entry_rate = self.lambda_rate / len(ENTRY_POINTS)

        for entry_name, (inter_id, approach_dir) in ENTRY_POINTS.items():
            intersection = intersections.get(inter_id)
            if intersection is None:
                continue

            num_to_spawn = int(self._rng.poisson(per_entry_rate * dt))
            for _ in range(num_to_spawn):
                routes = ROUTES_BY_ENTRY.get(entry_name, [["straight", "straight"]])
                route_idx = int(self._rng.choice(len(routes), p=[0.50, 0.25, 0.25]))
                selected_route = list(routes[route_idx])
                first_turn = selected_route[0]
                planned_turns = selected_route[1:]

                lane_key = f"{approach_dir}_{first_turn}"
                lane_queue = intersection.lanes.get(lane_key, [])

                if len(lane_queue) < MAX_QUEUE:
                    # Anti-overlap clearance: ensure tail vehicle has moved ahead before spawning new vehicle
                    if lane_queue and lane_queue[-1].position < 0.18:
                        continue

                    vehicle = Vehicle(
                        id=str(uuid4()),
                        lane=approach_dir,
                        turn=first_turn,
                        position=0.0,
                        wait_time=0.0,
                        speed=DEFAULT_SPEED,
                        state="waiting",
                        planned_turns=planned_turns,
                    )
                    lane_queue.append(vehicle)
                    intersection._spawned_this_interval += 1
                    total_spawned += 1

        return total_spawned
