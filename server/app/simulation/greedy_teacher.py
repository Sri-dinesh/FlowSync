"""
greedy_teacher.py — Greedy Demonstration Collector for Warm-Start Buffer Seeding
==================================================================================
Collects pressure-heuristic transitions for the legacy application trainer.

Motivation:
  During early training (large epsilon), the RL agent explores randomly and generates
  varied transitions. Teacher seeding supplies an existing heuristic's decisions
  before online learning. Its effect requires a matched experiment.

Conceptual precedents are pressure control (Varaiya, 2013) and demonstration-
assisted learning (Hester et al., DQfD, 2018):
https://people.eecs.berkeley.edu/~varaiya/publications.html
https://research.google/pubs/deep-q-learning-from-demonstrations/
This collector is not a reproduction of the complete DQfD algorithm.

Usage:
    from server.app.simulation.greedy_teacher import GreedyTeacher

    teacher = GreedyTeacher(env=env)
    n_transitions = teacher.fill_buffer(agent.replay_buffer, n_steps=5000)
    logger.info(f"Seeded replay buffer with {n_transitions} Greedy demonstrations.")
"""
from __future__ import annotations

import logging
from typing import Callable, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..simulation.environment import TrafficEnv
    from ..rl.replay_buffer import PrioritizedReplayBuffer

logger = logging.getLogger(__name__)


class GreedyTeacher:
    """
    Privileged simulator-pressure teacher for demonstration replay collection.

    The selector reads simulator-derived movement pressure and uses scan order
    to break ties. The collector applies the action mask; the environment enforces
    physical signal transitions. No performance improvement is guaranteed.

    Args:
        env: TrafficEnv instance (used for generating transitions).
    """

    def __init__(self, env: "TrafficEnv") -> None:
        self.env = env

    def select_greedy_action(self, state: np.ndarray) -> int:
        """
        Select the phase with highest total movement pressure.

        Uses the environment's internal pressure computation. During
        yellow/all-red phases, returns the current phase.

        Args:
            state: Current observation (used only for API consistency).

        Returns:
            Pressure-maximizing phase index (0-3), or current phase in clearance.
        """
        signal = self.env.intersection.signal
        pressures = self.env._compute_movement_pressures(self.env.intersection)

        # During transitions, maintain current phase choice
        if signal.color.name in ("YELLOW", "RED"):
            return signal.current_phase

        # Find the phase with maximum total movement pressure
        from .traffic_math import compute_phase_pressure
        best_phase = signal.current_phase
        best_pressure = -1.0

        for phase in range(4):
            p = compute_phase_pressure(pressures, phase)
            if p > best_pressure:
                best_pressure = p
                best_phase = phase

        return best_phase

    def fill_buffer(
        self,
        replay_buffer: "PrioritizedReplayBuffer",
        n_steps: int = 5000,
        seed: int = 42,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Run the Greedy policy and populate the replay buffer with transitions.

        Runs the Greedy controller for n_steps and pushes (s, a, r, s', done)
        tuples into the PER replay buffer. The buffer will prioritize these
        by their actual TD error once training starts.

        Args:
            replay_buffer: The PrioritizedReplayBuffer to fill.
            n_steps: Number of transitions to collect.
            seed: Seed for reproducibility.

        Returns:
            Number of transitions successfully pushed.
        """
        state, reset_info = self.env.reset_to_decision(seed=seed)
        action_mask = reset_info["valid_action_mask"]
        transitions_pushed = 0

        logger.info(
            "GreedyTeacher: Seeding replay buffer with %d demonstration transitions...",
            n_steps,
        )

        while transitions_pushed < n_steps:
            action = self.select_greedy_action(state)
            if not action_mask[action]:
                valid = np.flatnonzero(action_mask)
                action = int(valid[0])
            next_state, reward, terminated, truncated, info = self.env.step_decision(action)
            done = terminated or truncated

            # Legacy replay labels this transition with the executed action.
            executed_action = info.get("executed_action", action)
            next_action_mask = info["valid_action_mask"]
            replay_buffer.push(
                state,
                executed_action,
                reward,
                next_state,
                float(terminated),
                valid_action_mask=action_mask,
                next_valid_action_mask=next_action_mask,
                bootstrap_discount=info["bootstrap_discount"],
                is_demo=True,
            )
            transitions_pushed += 1
            if progress_callback and (
                transitions_pushed == 1
                or transitions_pushed % 100 == 0
                or transitions_pushed == n_steps
            ):
                progress_callback(transitions_pushed, n_steps)

            state = next_state
            action_mask = next_action_mask
            if done:
                state, reset_info = self.env.reset_to_decision()
                action_mask = reset_info["valid_action_mask"]

        logger.info(
            "GreedyTeacher: Buffer seeded with %d causal Greedy transitions (%.1f%% of steps).",
            transitions_pushed,
            transitions_pushed / max(n_steps, 1) * 100.0,
        )
        return transitions_pushed
