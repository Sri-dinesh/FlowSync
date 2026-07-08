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
        # Correct observations bounds: queue[0..100], phase[0..3], time[0..100], color[0..1], timestep[0..1]
        low = np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        high = np.array([100, 100, 100, 100, 3, 100, 1.0, 1.0], dtype=np.float32)
        self.observation_space = Box(low=low, high=high, dtype=np.float32)
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
        total_wait_time = self.intersection.get_total_wait_time()
        vehicles_passed = self.intersection.total_passed - prev_total_passed
        
        # Only count switch penalty if light was green and a switch actually happened
        phase_changed = (action != prev_phase) and (self.intersection.signal.color.value == "green")

        wait_penalty = -0.1 * total_wait_time
        throughput_bonus = 1.0 * vehicles_passed
        switch_penalty = -0.5 if phase_changed else 0.0
        overflow_penalty = -2.0 * sum(1 for q in queue_lengths.values() if q >= 8)

        reward = wait_penalty + throughput_bonus + switch_penalty + overflow_penalty
        self._last_reward = reward

        observation = self._get_obs()
        terminated = False
        truncated = self.intersection.timestep >= MAX_STEPS_PER_EPISODE

        return observation, reward, terminated, truncated, {}

    def _get_obs(self) -> np.ndarray:
        queue_lengths = self.intersection.get_queue_lengths()
        normalized_timestep = self.intersection.timestep / MAX_STEPS_PER_EPISODE
        
        # Normalize color: 1.0 for green, 0.5 for yellow, 0.0 for red
        color_val = 1.0 if self.intersection.signal.color.value == "green" else (
            0.5 if self.intersection.signal.color.value == "yellow" else 0.0
        )

        # Observe target/pending phase if signal is transitioning (yellow/red), otherwise current_phase
        obs_phase = self.intersection.signal._pending_phase if self.intersection.signal._pending_phase is not None else self.intersection.signal.current_phase

        observation = np.array(
            [
                queue_lengths.get("north", 0),
                queue_lengths.get("south", 0),
                queue_lengths.get("east", 0),
                queue_lengths.get("west", 0),
                obs_phase,
                self.intersection.signal.time_in_phase,
                color_val,
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
