from typing import Any, Dict, Tuple

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Discrete

from ..config import settings
from ..schemas.simulation_schema import SimulationFrame, build_frame
from .intersection import Intersection
from .traffic_signal import PHASE_GREEN_LANES
from ..rl.hyperparams import HyperParams

HP = HyperParams()


class TrafficEnv(gym.Env):
    def __init__(self) -> None:
        super().__init__()
        self.intersection = Intersection(spawn_lambda=HP.TRAINING_LAMBDA, red_duration=settings.signal_red_duration)
        self.observation_space = Box(
            low=np.zeros(20, dtype=np.float32),
            high=np.ones(20, dtype=np.float32),  # all values normalized 0-1
            dtype=np.float32
        )
        self.action_space = Discrete(4)
        self._last_reward = 0.0
        self._episode = 0

    def reset(
        self,
        seed: int | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.intersection.reset()
        self.intersection.spawner.set_enabled(True)
        self._last_reward = 0.0
        return self._get_obs(), {}

    def compute_reward(
        self,
        prev_pressures: dict,
        curr_pressures: dict,
        vehicles_passed: int,
        phase_changed: bool,
        signal,
        prev_phase: int = None,
    ) -> float:
        """
        Pressure-based reward function.
        Based on: PressLight, MPLight, Advanced-MPLight, FPA-DQN papers.

        Components:
        1. Negative total pressure (primary) — minimize intersection-wide congestion
        2. Throughput bonus — reward each vehicle cleared
        3. Switch penalty — mild penalty for unnecessary phase changes
        4. Starvation penalty — hard penalty when any direction is starved
        5. Max green violation — penalty if agent holds phase beyond MAX_GREEN_TIME
        """

        # 1. Pressure reward — negative total pressure (lower pressure = better)
        #    Uses CHANGE in pressure, not absolute value, for cleaner gradient signal
        total_prev = sum(prev_pressures.values())
        total_curr = sum(curr_pressures.values())
        pressure_reward = (total_prev - total_curr) * 1.5   # pressure reduction = positive

        # 2. Throughput bonus — only reward if vehicles actually cleared
        #    Scale conservatively: 0.2 per vehicle to avoid dominating pressure signal
        throughput_reward = vehicles_passed * 0.2

        # 3. Switch penalty — discourage unnecessary switching
        #    Only penalize if switching while current phase still has vehicles
        if phase_changed and prev_phase is not None:
            prev_green_dirs = PHASE_GREEN_LANES.get(prev_phase, [])
            prev_green_pressure = sum(
                prev_pressures.get(f"{d}_{turn}", 0) 
                for d in prev_green_dirs 
                for turn in ["straight", "left", "right"]
            )
            # Penalize if we prematurely abandoned a phase that still had traffic
            switch_penalty = -0.3 if prev_green_pressure > 0.3 else 0.0
        else:
            switch_penalty = 0.0

        # 4. Starvation penalty — hard penalty per starved direction
        starved = signal.get_starved_directions()
        starvation_penalty = -2.0 * len(starved)

        # 5. Max green violation penalty
        max_green_penalty = -1.0 if signal.is_max_green_exceeded else 0.0

        # 6. Balance bonus — ONLY reward balance when intersection actually has traffic
        #    Avoids the artificial 0.5/step reward during empty early steps
        if total_curr > 0.05:  # only when there are actually vehicles
            phase_pressures = [self._get_phase_pressure(curr_pressures, p) for p in range(4)]
            max_p = max(phase_pressures)
            min_p = min(phase_pressures)
            imbalance = max_p - min_p
            balance_bonus = 0.2 if imbalance < 0.2 else 0.0
        else:
            balance_bonus = 0.0  # no bonus for empty intersection

        return float(
            pressure_reward
            + throughput_reward
            + switch_penalty
            + starvation_penalty
            + max_green_penalty
            + balance_bonus
        )

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        prev_pressures = self._compute_movement_pressures(self.intersection)
        prev_passed = self.intersection.total_passed
        prev_phase = self.intersection.signal.current_phase  # capture BEFORE tick

        # Enforce constraints BEFORE applying agent action
        signal = self.intersection.signal

        # Hard constraint: if max green exceeded, force phase switch
        if signal.is_max_green_exceeded and action == signal.current_phase:
            # Force agent to switch — find best alternative
            action = self._get_best_alternative_phase()

        # Hard constraint: if direction is starved, bias toward serving it
        starved = signal.get_starved_directions()
        if starved:
            starved_phase = self._get_phase_for_direction(starved[0])
            if starved_phase != signal.current_phase:
                action = starved_phase  # override agent action to prevent starvation

        self.intersection.tick(dt=0.1, action=action)

        curr_pressures = self._compute_movement_pressures(self.intersection)
        curr_passed = self.intersection.total_passed
        vehicles_passed_this_step = curr_passed - prev_passed
        phase_changed = (action != prev_phase) and (self.intersection.signal.color.name == "GREEN")

        reward = self.compute_reward(
            prev_pressures=prev_pressures,
            curr_pressures=curr_pressures,
            vehicles_passed=vehicles_passed_this_step,
            phase_changed=phase_changed,
            signal=self.intersection.signal,
            prev_phase=prev_phase,
        )
        self._last_reward = reward

        obs = self._get_obs()
        terminated = False
        truncated = self.intersection.timestep >= HP.MAX_STEPS_PER_EPISODE
        info = {
            "pressures": curr_pressures,
            "vehicles_passed": vehicles_passed_this_step,
            "avg_wait_time": self.intersection.get_avg_wait_time(),
            "starved_directions": starved,
        }

        return obs, reward, terminated, truncated, info

    def _get_phase_pressure(self, pressures: dict, phase: int) -> float:
        if phase == 0:
            # NS_GREEN: north and south straight movements
            movements = ["north_straight", "south_straight"]
        elif phase == 1:
            # EW_GREEN: east and west straight movements
            movements = ["east_straight", "west_straight"]
        elif phase == 2:
            # NS_LEFT: north and south left-turn movements
            movements = ["north_left", "south_left"]
        elif phase == 3:
            # EW_LEFT: east and west left-turn movements
            movements = ["east_left", "west_left"]
        else:
            movements = []
        return sum(pressures.get(m, 0) for m in movements)

    def _get_best_alternative_phase(self) -> int:
        """When max green exceeded, pick the phase with highest pressure."""
        pressures = self._compute_movement_pressures(self.intersection)
        current = self.intersection.signal.current_phase

        best_phase = current
        best_pressure = -1
        for phase in range(4):
            if phase == current:
                continue
            phase_pressure = self._get_phase_pressure(pressures, phase)
            if phase_pressure > best_pressure:
                best_pressure = phase_pressure
                best_phase = phase

        return best_phase

    def _get_phase_for_direction(self, direction: str) -> int:
        """Returns the most appropriate phase for a starved direction."""
        DIRECTION_PHASES = {
            "north": 0, "south": 0,
            "east": 1,  "west": 1,
        }
        return DIRECTION_PHASES.get(direction, 0)

    def _compute_movement_pressures(self, intersection: Intersection) -> dict:
        """
        Compute traffic movement pressure per movement.
        Pressure(movement) = incoming_vehicles / capacity - outgoing_vehicles / capacity
        Based on PressLight / MPLight / PDLight formula.
        """
        movement_queues = intersection.get_movement_queues()
        outgoing = intersection.get_outgoing_counts()
        MAX_CAP = 10.0

        pressures = {}
        dest_map = {
            "north_straight": "south", "north_left": "east", "north_right": "west",
            "south_straight": "north", "south_left": "west", "south_right": "east",
            "east_straight": "west", "east_left": "south", "east_right": "north",
            "west_straight": "east", "west_left": "north", "west_right": "south",
        }

        for movement, dest in dest_map.items():
            incoming = movement_queues.get(movement, 0) / MAX_CAP
            out = outgoing.get(dest, 0) / MAX_CAP
            pressures[movement] = max(0.0, incoming - out)

        return pressures

    def _get_obs(self) -> np.ndarray:
        movement_queues = self.intersection.get_movement_queues()
        signal = self.intersection.signal
        pressures = self._compute_movement_pressures(self.intersection)

        # 12 movement queues (normalized by max capacity 10)
        movements = [
            movement_queues.get("north_straight", 0) / 10.0,
            movement_queues.get("north_left", 0) / 10.0,
            movement_queues.get("north_right", 0) / 10.0,
            movement_queues.get("south_straight", 0) / 10.0,
            movement_queues.get("south_left", 0) / 10.0,
            movement_queues.get("south_right", 0) / 10.0,
            movement_queues.get("east_straight", 0) / 10.0,
            movement_queues.get("east_left", 0) / 10.0,
            movement_queues.get("east_right", 0) / 10.0,
            movement_queues.get("west_straight", 0) / 10.0,
            movement_queues.get("west_left", 0) / 10.0,
            movement_queues.get("west_right", 0) / 10.0,
        ]

        # 4 one-hot phase encoding
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[signal.current_phase] = 1.0

        # Signal context
        time_norm = min(signal.time_in_phase / signal.MAX_GREEN_TIME, 1.0)
        is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0
        total_pressure = sum(pressures.values())
        pressure_norm = min(total_pressure / 20.0, 1.0)  # normalize

        # Starvation
        starv_timers = list(signal.starvation_timer.values())
        max_starv = max(starv_timers) / signal.STARVATION_THRESHOLD
        max_starv_norm = min(max_starv, 1.0)

        obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm]
        return np.array(obs, dtype=np.float32)

    def render(self) -> SimulationFrame:
        return build_frame(
            self.intersection,
            mode="ai",
            reward=self._last_reward,
            episode=self._episode,
        )
