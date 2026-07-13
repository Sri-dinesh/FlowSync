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
        self._last_reward = 0.0
        return self._get_obs(), {}

    def compute_reward(
        self,
        prev_pressures: dict,
        curr_pressures: dict,
        vehicles_passed: int,
        phase_changed: bool,
        signal,
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
        if phase_changed:
            curr_green_dirs = PHASE_GREEN_LANES.get(signal.current_phase, [])
            curr_green_pressure = sum(
                curr_pressures.get(d, 0) for d in curr_green_dirs
            )
            # Only penalize if we left a direction that still had pressure
            switch_penalty = -0.3 if curr_green_pressure > 0.3 else 0.0
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
            pressure_values = list(curr_pressures.values())
            max_p = max(pressure_values)
            min_p = min(pressure_values)
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
        prev_pressures = self._compute_movement_pressures()
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

        curr_pressures = self._compute_movement_pressures()
        curr_passed = self.intersection.total_passed
        vehicles_passed_this_step = curr_passed - prev_passed
        phase_changed = (self.intersection.signal.current_phase != prev_phase)  # compare post-tick phase vs pre-tick

        reward = self.compute_reward(
            prev_pressures=prev_pressures,
            curr_pressures=curr_pressures,
            vehicles_passed=vehicles_passed_this_step,
            phase_changed=phase_changed,
            signal=self.intersection.signal,
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

    def _get_best_alternative_phase(self) -> int:
        """When max green exceeded, pick the phase with highest pressure."""
        pressures = self._compute_movement_pressures()
        current = self.intersection.signal.current_phase
        current_dirs = PHASE_GREEN_LANES.get(current, [])

        # Find phase whose lanes have highest pressure (excluding current)
        PHASE_GREEN_DIRS_MAP = {
            0: ["north", "south"],
            1: ["east", "west"],
            2: ["north", "south"],  # left-turn phase
            3: ["east", "west"],    # left-turn phase
        }

        best_phase = current
        best_pressure = -1
        for phase, dirs in PHASE_GREEN_DIRS_MAP.items():
            if phase == current:
                continue
            phase_pressure = sum(pressures.get(d, 0) for d in dirs)
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

    def _compute_movement_pressures(self) -> dict:
        """
        Compute traffic movement pressure per direction.
        Pressure(direction) = incoming_vehicles / capacity - outgoing_vehicles / capacity
        Based on PressLight / MPLight / PDLight formula.

        Higher pressure = more vehicles backed up = more urgent to serve this phase.
        """
        movement_queues = self.intersection.get_movement_queues()
        outgoing = self.intersection.get_outgoing_counts()
        MAX_CAP = 10.0

        pressures = {}
        for direction in ["north", "south", "east", "west"]:
            # Straight + left movements (right turns always move, excluded from pressure)
            incoming = (
                movement_queues.get(f"{direction}_straight", 0) +
                movement_queues.get(f"{direction}_left", 0)
            ) / MAX_CAP

            # Outgoing: vehicles in the outgoing lane of this direction's destination
            # (if outgoing is congested, agent should NOT serve this incoming even if queue is high)
            outgoing_opp = outgoing.get(direction, 0) / MAX_CAP

            pressures[direction] = max(0.0, incoming - outgoing_opp)

        return pressures

    def _get_obs(self) -> np.ndarray:
        movement_queues = self.intersection.get_movement_queues()
        signal = self.intersection.signal
        pressures = self._compute_movement_pressures()

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
