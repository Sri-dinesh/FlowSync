from typing import Any, Dict, Tuple

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Discrete

from ..schemas.simulation_schema import SimulationFrame, build_frame
from .intersection import Intersection

MAX_STEPS_PER_EPISODE = 500


class TrafficEnv(gym.Env):
    def __init__(self) -> None:
        super().__init__()
        self.intersection = Intersection()
        self.observation_space = Box(low=0, high=10, shape=(8,), dtype=np.float32)
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

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        prev_phase = self.intersection.signal.current_phase
        prev_total_passed = self.intersection.total_passed

        self.intersection.tick(dt=0.1, action=action)

        queue_lengths = self.intersection.get_queue_lengths()
        total_waiting = self.intersection.get_total_waiting()
        vehicles_passed = self.intersection.total_passed - prev_total_passed
        phase_changed = action != prev_phase

        wait_penalty = -0.1 * total_waiting
        throughput_bonus = 1.0 * vehicles_passed
        switch_penalty = -0.5 if phase_changed else 0.0
        overflow_penalty = -2.0 * sum(1 for q in queue_lengths.values() if q >= 8)

        reward = wait_penalty + throughput_bonus + switch_penalty + overflow_penalty
        self._last_reward = reward

        observation = self._get_obs()
        terminated = self.intersection.timestep >= MAX_STEPS_PER_EPISODE
        truncated = False

        return observation, reward, terminated, truncated, {}

    def _get_obs(self) -> np.ndarray:
        queue_lengths = self.intersection.get_queue_lengths()
        total_waiting = self.intersection.get_total_waiting()
        normalized_timestep = self.intersection.timestep / MAX_STEPS_PER_EPISODE

        observation = np.array(
            [
                queue_lengths.get("north", 0),
                queue_lengths.get("south", 0),
                queue_lengths.get("east", 0),
                queue_lengths.get("west", 0),
                self.intersection.signal.current_phase,
                self.intersection.signal.time_in_phase,
                total_waiting,
                normalized_timestep,
            ],
            dtype=np.float32,
        )
        return observation

    def render(self) -> SimulationFrame:
        return build_frame(
            self.intersection,
            mode="ai",
            reward=self._last_reward,
            episode=self._episode,
        )
