"""
curriculum.py — Multi-Regime Training Curriculum for FlowSync RL
=================================================================
Task 5.2: Implements a structured training curriculum that progressively
exposes the agent to increasingly challenging traffic scenarios.

Curriculum structure:
  Stage 0 (Episodes 0-100):    Low-demand warm-up (λ=0.3)
  Stage 1 (Episodes 100-300):  Medium demand — learn basic control (λ=0.5)
  Stage 2 (Episodes 300-600):  High demand — primary training regime (λ=0.8)
  Stage 3 (Episodes 600-800):  Burst/platoon — stress test (λ=1.2)
  Stage 4 (Episodes 800-1000): Mixed regime — adversarial generalization (random λ)

Benefits:
  - Prevents early-episode policy collapse from overwhelming traffic demand
  - Teaches the agent to handle sparse, moderate, heavy, and burst traffic
  - Mixed final stage builds generalization to arbitrary real-world conditions

Usage:
    curriculum = TrainingCurriculum(env=env)
    curriculum.apply(episode=episode_num)  # call before each episode reset
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..simulation.environment import TrafficEnv

logger = logging.getLogger(__name__)


@dataclass
class CurriculumStage:
    """Defines a single curriculum stage."""
    name: str
    start_episode: int
    end_episode: int
    lambda_min: float
    lambda_max: float
    description: str

    def get_lambda(self) -> float:
        """Sample λ uniformly from [lambda_min, lambda_max]."""
        if self.lambda_min == self.lambda_max:
            return self.lambda_min
        return random.uniform(self.lambda_min, self.lambda_max)


# Default curriculum schedule
DEFAULT_CURRICULUM: List[CurriculumStage] = [
    CurriculumStage(
        name="warmup",
        start_episode=0,
        end_episode=100,
        lambda_min=0.2,
        lambda_max=0.4,
        description="Low-demand warm-up: agent learns basic phase switching",
    ),
    CurriculumStage(
        name="basic",
        start_episode=100,
        end_episode=300,
        lambda_min=0.4,
        lambda_max=0.6,
        description="Medium demand: agent develops reliable phase selection",
    ),
    CurriculumStage(
        name="primary",
        start_episode=300,
        end_episode=600,
        lambda_min=0.7,
        lambda_max=0.9,
        description="High demand: primary training regime (matches eval lambda)",
    ),
    CurriculumStage(
        name="burst",
        start_episode=600,
        end_episode=800,
        lambda_min=1.0,
        lambda_max=1.5,
        description="Burst/platoon stress: tests predictive forecasting advantage",
    ),
    CurriculumStage(
        name="generalization",
        start_episode=800,
        end_episode=10_000,  # continues for all remaining episodes
        lambda_min=0.2,
        lambda_max=1.5,
        description="Mixed adversarial: random λ to prevent overfitting to single demand",
    ),
]


class TrainingCurriculum:
    """
    Multi-regime training curriculum that adjusts vehicle spawn rate per episode.

    The curriculum progressively increases traffic difficulty and introduces
    adversarial demand variation in later stages to build robust generalization.

    Args:
        env: TrafficEnv instance (its spawn lambda will be updated per episode).
        stages: List of CurriculumStage. Defaults to DEFAULT_CURRICULUM.
        total_episodes: Total number of training episodes.
    """

    def __init__(
        self,
        env: "TrafficEnv",
        stages: Optional[List[CurriculumStage]] = None,
        total_episodes: int = 1000,
    ) -> None:
        self.env = env
        self.stages = stages or DEFAULT_CURRICULUM
        self.total_episodes = total_episodes
        self._current_stage: Optional[CurriculumStage] = None
        self._current_lambda: float = 0.3

    def _get_stage(self, episode: int) -> CurriculumStage:
        """Find the applicable curriculum stage for the given episode number."""
        for stage in reversed(self.stages):
            if episode >= stage.start_episode:
                return stage
        return self.stages[0]

    def apply(self, episode: int) -> Tuple[str, float]:
        """
        Apply the curriculum to the environment for the given episode.

        Updates the intersection spawn lambda based on the current curriculum stage.
        Call this at the START of each episode, before env.reset().

        Args:
            episode: Current episode number (1-indexed).

        Returns:
            Tuple of (stage_name, applied_lambda) for logging.
        """
        stage = self._get_stage(episode)
        lambda_val = stage.get_lambda()
        self._current_stage = stage
        self._current_lambda = lambda_val

        # Apply to environment
        self.env.intersection.set_spawn_rate(lambda_val)

        # Log stage transitions
        if self._current_stage is None or stage.name != getattr(self._current_stage, "name", ""):
            logger.info(
                "Curriculum stage transition → [%s] at episode %d: λ=%.2f | %s",
                stage.name,
                episode,
                lambda_val,
                stage.description,
            )

        return stage.name, lambda_val

    def get_status(self) -> dict:
        """Return current curriculum status for telemetry."""
        return {
            "stage_name":      self._current_stage.name if self._current_stage else "unknown",
            "current_lambda":  self._current_lambda,
            "stage_description": self._current_stage.description if self._current_stage else "",
        }
