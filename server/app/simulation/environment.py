from typing import Any, Dict, Tuple

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Discrete

from ..config import settings
from ..schemas.simulation_schema import SimulationFrame, build_frame
from .intersection import Intersection

MAX_STEPS_PER_EPISODE = 500


class TrafficEnv(gym.Env):
    def __init__(self) -> None:
        super().__init__()
        self.intersection = Intersection(red_duration=settings.signal_red_duration)
        # Observation bounds: queue_n, queue_s, queue_e, queue_w [0..10], phase [0..3], time [0..60], total_vehicles [0..40], pending_phase [0..3]
        low = np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        high = np.array([10, 10, 10, 10, 3, 60, 40, 3], dtype=np.float32)
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

    def compute_reward(
        self,
        prev_queues: Dict[str, int],
        curr_queues: Dict[str, int],
        vehicles_passed: int,
        phase_changed: bool,
    ) -> float:
        """
        Reward function for traffic signal DQN agent.

        Design goals:
        - Primary: minimize total wait time (queue reduction)
        - Secondary: maximize throughput (vehicles cleared)
        - Penalty: unnecessary phase switching
        - Hard penalty: queue overflow (triggers early at 6, not 8)
        - Bonus: balanced queues across all directions
        """
        total_curr_waiting = sum(curr_queues.values())
        total_prev_waiting = sum(prev_queues.values())

        # 1. Queue reduction reward — reward for reducing total queue
        queue_delta = total_prev_waiting - total_curr_waiting
        queue_reward = 0.3 * queue_delta  # positive if queue reduced

        # 2. Throughput bonus — reward each vehicle that clears
        throughput_reward = 0.8 * vehicles_passed

        # 3. Unnecessary switch penalty — only if no benefit
        #    Reduced from -0.5 to -0.3 to not over-discourage switching
        switch_penalty = -0.3 if phase_changed else 0.0

        # 4. Overflow penalty — triggers at 6 (was 8) for earlier intervention
        overflow_count = sum(1 for q in curr_queues.values() if q >= 6)
        overflow_penalty = -1.5 * overflow_count

        # 5. Balance bonus — small reward for keeping queues even
        if total_curr_waiting > 0:
            max_q = max(curr_queues.values())
            min_q = min(curr_queues.values())
            imbalance = max_q - min_q
            balance_bonus = 0.2 if imbalance <= 2 else 0.0
        else:
            balance_bonus = 0.5  # bonus for empty intersection

        reward = (
            queue_reward
            + throughput_reward
            + switch_penalty
            + overflow_penalty
            + balance_bonus
        )

        return float(reward)

    def step(
        self, action: int
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        prev_queues = self.intersection.get_queue_lengths()
        prev_passed = self.intersection.total_passed
        prev_phase = self.intersection.signal.current_phase

        self.intersection.tick(dt=0.1, action=action)

        curr_queues = self.intersection.get_queue_lengths()
        curr_passed = self.intersection.total_passed
        vehicles_passed_this_step = curr_passed - prev_passed
        
        # Only count switch penalty if light was green and a switch actually happened
        phase_changed = (action != prev_phase) and (self.intersection.signal.color.value == "green")

        reward = self.compute_reward(
            prev_queues=prev_queues,
            curr_queues=curr_queues,
            vehicles_passed=vehicles_passed_this_step,
            phase_changed=phase_changed,
        )
        self._last_reward = reward

        observation = self._get_obs()
        terminated = False
        truncated = self.intersection.timestep >= MAX_STEPS_PER_EPISODE

        info = {
            "queue_lengths": curr_queues,
            "vehicles_passed": vehicles_passed_this_step,
            "avg_wait_time": self.intersection.get_avg_wait_time(),
        }

        return observation, reward, terminated, truncated, info

    def _get_obs(self) -> np.ndarray:
        queues = self.intersection.get_queue_lengths()
        total_vehicles = self.intersection.get_total_waiting()

        # pending_phase: if transitioning, what phase comes next; else current phase
        pending_phase = (
            self.intersection.signal.pending_phase
            if self.intersection.signal.pending_phase is not None
            else self.intersection.signal.current_phase
        )

        observation = np.array(
            [
                float(queues.get("north", 0)),
                float(queues.get("south", 0)),
                float(queues.get("east", 0)),
                float(queues.get("west", 0)),
                float(self.intersection.signal.current_phase),
                float(self.intersection.signal.time_in_phase),
                float(total_vehicles),
                float(pending_phase),
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
