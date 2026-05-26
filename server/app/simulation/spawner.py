from typing import Dict, List
from uuid import uuid4

import numpy as np

from .vehicle import DEFAULT_SPEED, Vehicle

MAX_QUEUE = 10


class PoissonSpawner:
    def __init__(self, lambda_rate: float = 0.3) -> None:
        self.lambda_rate = lambda_rate

    def set_rate(self, lambda_rate: float) -> None:
        self.lambda_rate = max(0.0, lambda_rate)

    def spawn(self, dt: float, lanes: Dict[str, List[Vehicle]]) -> List[Vehicle]:
        spawned: List[Vehicle] = []

        for lane_name, lane_queue in lanes.items():
            num_to_spawn = int(np.random.poisson(self.lambda_rate * dt))
            available_slots = max(0, MAX_QUEUE - len(lane_queue))
            for _ in range(min(num_to_spawn, available_slots)):
                vehicle = Vehicle(
                    id=str(uuid4()),
                    lane=lane_name,
                    position=0.0,
                    wait_time=0.0,
                    speed=DEFAULT_SPEED,
                    state="waiting",
                )
                lane_queue.append(vehicle)
                spawned.append(vehicle)

        return spawned
