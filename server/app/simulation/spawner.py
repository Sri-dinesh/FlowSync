from typing import Dict, List
from uuid import uuid4

import numpy as np

from .vehicle import DEFAULT_SPEED, Vehicle

MAX_QUEUE = 10


class PoissonSpawner:
    def __init__(self, lambda_rate: float = 0.3) -> None:
        self.lambda_rate = lambda_rate
        self.enabled = False

    def set_rate(self, lambda_rate: float) -> None:
        self.lambda_rate = max(0.0, lambda_rate)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def spawn(self, dt: float, lanes: Dict[str, List[Vehicle]]) -> List[Vehicle]:
        spawned: List[Vehicle] = []

        # Do not spawn when disabled or lambda is zero
        if not self.enabled or self.lambda_rate <= 0:
            return spawned

        lane_names = list(lanes.keys())
        if not lane_names:
            return spawned

        # Only spawn into one approach lane per tick so the intersection reads more clearly.
        lane_name = str(np.random.choice(lane_names))
        lane_queue = lanes[lane_name]
        num_to_spawn = int(np.random.poisson(self.lambda_rate * dt))
        available_slots = max(0, MAX_QUEUE - len(lane_queue))
        for _ in range(min(num_to_spawn, available_slots)):
            # Decide turn: 50% straight, 25% left, 25% right
            turn = np.random.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25])
            vehicle = Vehicle(
                id=str(uuid4()),
                lane=lane_name,
                turn=turn,
                position=0.0,
                wait_time=0.0,
                speed=DEFAULT_SPEED,
                state="waiting",
            )
            lane_queue.append(vehicle)
            spawned.append(vehicle)

        return spawned
