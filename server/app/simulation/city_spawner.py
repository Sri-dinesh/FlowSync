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


class CitySpawner:
    """
    Poisson-process vehicle spawner for the 2×2 city grid.
    Spawns at all 8 external entry points independently.
    """

    def __init__(self, lambda_rate: float = 0.3) -> None:
        self.lambda_rate = lambda_rate
        self.enabled = False

    def set_rate(self, lambda_rate: float) -> None:
        self.lambda_rate = max(0.0, lambda_rate)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def spawn(self, dt: float, intersections: Dict[str, Intersection]) -> int:
        """
        Spawn vehicles at each external entry point using a Poisson process.
        Returns total number of vehicles spawned this tick.
        """
        if not self.enabled or self.lambda_rate <= 0:
            return 0

        total_spawned = 0
        entry_keys = list(ENTRY_POINTS.keys())

        num_to_spawn = int(np.random.poisson(self.lambda_rate * dt))
        for _ in range(num_to_spawn):
            entry_key = str(np.random.choice(entry_keys))
            inter_id, approach_dir = ENTRY_POINTS[entry_key]
            intersection = intersections.get(inter_id)
            if intersection is None:
                continue

            # 50% straight, 25% left, 25% right
            turn = str(np.random.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25]))
            lane_key = f"{approach_dir}_{turn}"
            lane_queue = intersection.lanes.get(lane_key, [])

            if len(lane_queue) < MAX_QUEUE:
                vehicle = Vehicle(
                    id=str(uuid4()),
                    lane=approach_dir,
                    turn=turn,
                    position=0.0,
                    wait_time=0.0,
                    speed=DEFAULT_SPEED,
                    state="waiting",
                )
                lane_queue.append(vehicle)
                intersection._spawned_this_interval += 1
                total_spawned += 1

        return total_spawned
