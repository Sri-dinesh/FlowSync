from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

from .vehicle import DEFAULT_SPEED, Vehicle

MAX_QUEUE = 15


@dataclass
class TrafficProfile:
    id: str
    name: str
    description: str
    directional_weights: Dict[str, float] = field(
        default_factory=lambda: {"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0}
    )
    turn_probs: List[float] = field(
        default_factory=lambda: [0.5, 0.25, 0.25]
    )  # [straight, left, right]
    base_lambda: float = 0.5
    lambda_multiplier: float = 1.0


SCENARIO_PROFILES: Dict[str, TrafficProfile] = {
    "uniform": TrafficProfile(
        id="uniform",
        name="Standard Balanced",
        description="Uniform distribution across all 4 approaches and standard turn ratios (50% straight, 25% left, 25% right).",
        directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        turn_probs=[0.50, 0.25, 0.25],
        base_lambda=0.5,
        lambda_multiplier=1.0,
    ),
    "rush_hour": TrafficProfile(
        id="rush_hour",
        name="Rush Hour Corridor",
        description="Extreme North-South commuter corridor surge (80% traffic on NS corridor, 20% on EW cross-streets).",
        directional_weights={"north": 1.8, "south": 1.8, "east": 0.4, "west": 0.4},
        turn_probs=[0.60, 0.20, 0.20],
        base_lambda=0.85,
        lambda_multiplier=1.2,
    ),
    "heavy_left": TrafficProfile(
        id="heavy_left",
        name="Heavy Left Turns",
        description="High turning conflict with 50% left turns, demanding optimal protected arrow phase allocations.",
        directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        turn_probs=[0.30, 0.50, 0.20],
        base_lambda=0.75,
        lambda_multiplier=1.0,
    ),
    "arterial_surge": TrafficProfile(
        id="arterial_surge",
        name="East-West Arterial",
        description="High-speed East-West main thoroughfare with subordinate North-South feeder streets.",
        directional_weights={"north": 0.35, "south": 0.35, "east": 1.9, "west": 1.9},
        turn_probs=[0.70, 0.15, 0.15],
        base_lambda=0.90,
        lambda_multiplier=1.15,
    ),
    "platoon_burst": TrafficProfile(
        id="platoon_burst",
        name="Platoon Congestion",
        description="Heavy platoons and dense arrival bursts across all approaches demanding quick queue clearance.",
        directional_weights={"north": 1.25, "south": 1.25, "east": 1.25, "west": 1.25},
        turn_probs=[0.50, 0.25, 0.25],
        base_lambda=1.25,
        lambda_multiplier=1.3,
    ),
}


class PoissonSpawner:
    def __init__(self, lambda_rate: float = 0.5) -> None:
        self.lambda_rate = lambda_rate
        self.enabled = True
        self._rng = np.random.default_rng()
        self.profile: Optional[TrafficProfile] = None

    def set_rate(self, lambda_rate: float) -> None:
        self.lambda_rate = max(0.0, lambda_rate)

    def set_profile(self, profile: Any) -> None:
        """Assign a traffic profile (either a TrafficProfile object, dict, or preset name key)."""
        if isinstance(profile, str):
            self.profile = SCENARIO_PROFILES.get(profile, SCENARIO_PROFILES["uniform"])
        elif isinstance(profile, TrafficProfile):
            self.profile = profile
        elif isinstance(profile, dict):
            d_weights = profile.get("directional_weights") or {"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0}
            t_probs = profile.get("turn_probs") or [0.5, 0.25, 0.25]
            # Ensure turn_probs sums to 1.0
            prob_sum = sum(t_probs)
            if prob_sum > 0:
                t_probs = [float(p) / prob_sum for p in t_probs]
            else:
                t_probs = [0.5, 0.25, 0.25]

            self.profile = TrafficProfile(
                id=str(profile.get("id", "custom")),
                name=str(profile.get("name", "Custom Profile")),
                description=str(profile.get("description", "Custom user-defined traffic distribution.")),
                directional_weights={
                    "north": float(d_weights.get("north", 1.0)),
                    "south": float(d_weights.get("south", 1.0)),
                    "east": float(d_weights.get("east", 1.0)),
                    "west": float(d_weights.get("west", 1.0)),
                },
                turn_probs=t_probs,
                base_lambda=float(profile.get("base_lambda", 0.6)),
                lambda_multiplier=float(profile.get("lambda_multiplier", 1.0)),
            )
        else:
            self.profile = None

        if self.profile and self.profile.base_lambda:
            self.set_rate(self.profile.base_lambda)

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

        # Profile parameters (directional asymmetry and turn probabilities)
        dir_weights = (
            self.profile.directional_weights
            if self.profile
            else {"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0}
        )
        turn_probs = self.profile.turn_probs if self.profile else [0.5, 0.25, 0.25]
        lambda_mult = self.profile.lambda_multiplier if self.profile else 1.0

        for dir_name in dir_names:
            weight = dir_weights.get(dir_name, 1.0)
            per_dir_rate = self.lambda_rate * weight * lambda_mult

            num_to_spawn = int(self._rng.poisson(per_dir_rate * dt))
            for _ in range(num_to_spawn):
                turn = str(self._rng.choice(["straight", "left", "right"], p=turn_probs))
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
