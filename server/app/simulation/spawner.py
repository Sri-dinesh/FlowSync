from typing import Dict, List
from uuid import uuid4

import numpy as np

from .vehicle import DEFAULT_SPEED, Vehicle

MAX_QUEUE = 15


class PoissonSpawner:
    def __init__(self, lambda_rate: float = 0.5) -> None:
        self.lambda_rate = lambda_rate
        self.enabled = True
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

    def seed_initial_vehicles(self, lanes: Dict[str, List[Vehicle]], count_per_dir: int = 1) -> List[Vehicle]:
        """Seed initial vehicles at staggered approach positions so the intersection is populated immediately."""
        spawned: List[Vehicle] = []
        dir_names = ["north", "south", "east", "west"]
        for dir_name in dir_names:
            straight_queue = lanes.get(f"{dir_name}_straight", [])
            if not straight_queue:
                v = Vehicle(
                    id=str(uuid4()),
                    lane=dir_name,
                    turn="straight",
                    position=0.22,
                    wait_time=0.0,
                    speed=DEFAULT_SPEED,
                    state="waiting",
                )
                straight_queue.append(v)
                spawned.append(v)
            if count_per_dir > 1:
                left_queue = lanes.get(f"{dir_name}_left", [])
                if not left_queue:
                    v2 = Vehicle(
                        id=str(uuid4()),
                        lane=dir_name,
                        turn="left",
                        position=0.12,
                        wait_time=0.0,
                        speed=DEFAULT_SPEED,
                        state="waiting",
                    )
                    left_queue.append(v2)
                    spawned.append(v2)
        return spawned

    def spawn(self, dt: float, lanes: Dict[str, List[Vehicle]]) -> List[Vehicle]:
        spawned: List[Vehicle] = []

        # Do not spawn when disabled or lambda is zero
        if not self.enabled or self.lambda_rate <= 0:
            return spawned

        lane_names = list(lanes.keys())
        if not lane_names:
            return spawned

        dir_names = ["north", "south", "east", "west"]
        # Per approach arrival rate
        per_dir_rate = self.lambda_rate

        for dir_name in dir_names:
            num_to_spawn = int(self._rng.poisson(per_dir_rate * dt))
            for _ in range(num_to_spawn):
                # Decide turn: 50% straight, 25% left, 25% right
                turn = str(self._rng.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25]))
                lane_id = f"{dir_name}_{turn}"
                lane_queue = lanes.get(lane_id, [])

                if len(lane_queue) < MAX_QUEUE:
                    # Prevent vehicle overlapping at spawn point (clearance length)
                    if lane_queue and lane_queue[-1].position < 0.05:
                        continue
                    vehicle = Vehicle(
                        id=str(uuid4()),
                        lane=dir_name,
                        turn=turn,
                        position=0.0,
                        wait_time=0.0,
                        speed=DEFAULT_SPEED,
                        state="waiting",
                    )
                    lane_queue.append(vehicle)
                    spawned.append(vehicle)

        return spawned
