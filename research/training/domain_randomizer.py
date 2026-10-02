"""
domain_randomizer.py — Domain Randomization Engine for Robust RL Training
==========================================================================
Task G2: Exposes the RL policy to controlled traffic demand and perception
variability during training episodes to learn robust, generalized representations.

Randomization Parameters:
1. Demand Rate: lambda ~ Uniform(lambda_min, lambda_max) or rate_multiplier
2. Directional Weights: Random asymmetric weights Dirichlet or normalized ratios
3. Turn Ratios: Random variation in straight/left/right proportions
4. Observation Noise: Random miss rate p ~ Uniform(0.0, max_miss_rate)
5. Observation Latency: Random latency tau in {0, 100, 250} ms
6. False Positives: Random ghost injection lambda_fp ~ Uniform(0.0, max_fp)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import numpy as np

from server.app.simulation.environment import TrafficEnv
from server.app.simulation.spawner import TrafficProfile
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.scenarios.scenario_schema import DemandProfile, ScenarioConfig


@dataclass
class DomainRandomizerConfig:
    rate_multiplier_min: float = 0.8
    rate_multiplier_max: float = 1.2
    imbalance_max: float = 0.2
    miss_rate_max: float = 0.25
    latency_max_ms: int = 250
    latency_choices: Tuple[int, ...] = (0, 100, 250)
    max_false_positive_lambda: float = 0.30
    jitter_std: float = 0.02
    enable_bursts: bool = False


class DomainRandomizer:
    """
    Generates episode-specific randomized traffic demand and perception noise profiles.
    """

    def __init__(
        self,
        config: Optional[DomainRandomizerConfig] = None,
        seed: Optional[int] = None,
        lambda_range: Tuple[float, float] = (0.3, 1.1),
        max_miss_rate: float = 0.25,
        latency_choices: Tuple[int, ...] = (0, 100, 250),
        max_false_positive_lambda: float = 0.30,
    ) -> None:
        if config is not None:
            self.config = config
            self.seed = seed
            self.lambda_range = lambda_range
            self.max_miss_rate = config.miss_rate_max
            self.latency_choices = config.latency_choices
            self.max_false_positive_lambda = config.max_false_positive_lambda
        else:
            self.config = DomainRandomizerConfig(
                miss_rate_max=max_miss_rate,
                latency_choices=latency_choices,
                max_false_positive_lambda=max_false_positive_lambda,
            )
            self.seed = seed
            self.lambda_range = lambda_range
            self.max_miss_rate = max_miss_rate
            self.latency_choices = latency_choices
            self.max_false_positive_lambda = max_false_positive_lambda

        self._rng = np.random.default_rng(seed)

    def reset_seed(self, seed: int) -> None:
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def sample_episode_parameters(self, episode_idx: int) -> Tuple[TrafficProfile, FaultProfile]:
        """
        Sample a random domain configuration for one training episode.
        """
        # 1. Demand rate
        base_lambda = float(self._rng.uniform(self.lambda_range[0], self.lambda_range[1]))

        # 2. Directional weights (Dirichlet distribution)
        d_weights_raw = self._rng.dirichlet([2.0, 2.0, 2.0, 2.0]) * 4.0
        directional_weights = {
            "north": float(d_weights_raw[0]),
            "south": float(d_weights_raw[1]),
            "east":  float(d_weights_raw[2]),
            "west":  float(d_weights_raw[3]),
        }

        # 3. Turning splits: straight ~ 0.5-0.7, left ~ 0.15-0.35, right ~ 0.1-0.2
        turn_raw = self._rng.dirichlet([5.0, 2.5, 1.5])
        turn_probs = [float(turn_raw[0]), float(turn_raw[1]), float(turn_raw[2])]

        profile = TrafficProfile(
            id=f"dr_ep_{episode_idx}",
            name=f"Domain Randomized Episode {episode_idx}",
            description="Episode with randomized arrival rate and directional distribution",
            directional_weights=directional_weights,
            turn_probs=turn_probs,
            base_lambda=base_lambda,
            lambda_multiplier=1.0,
        )

        # 4. Perception disturbance profile
        miss_rate = float(self._rng.uniform(0.0, self.max_miss_rate))
        latency = int(self._rng.choice(self.latency_choices))
        fp_lambda = float(self._rng.uniform(0.0, self.max_false_positive_lambda))

        fault = FaultProfile(
            name=f"dr_fault_ep_{episode_idx}",
            miss_rate=miss_rate,
            latency_ms=latency,
            false_positive_lambda=fp_lambda,
            jitter_std=self.config.jitter_std,
        )

        return profile, fault

    def randomize(self, base_scenario: ScenarioConfig) -> Tuple[ScenarioConfig, FaultProfile]:
        """
        Randomizes a given ScenarioConfig according to DomainRandomizerConfig ranges.
        """
        mult = float(self._rng.uniform(
            self.config.rate_multiplier_min, self.config.rate_multiplier_max
        ))
        new_lambda = round(base_scenario.demand_profile.base_lambda * mult, 3)

        # Directional weights with imbalance
        dw = base_scenario.demand_profile.directional_weights
        dirs = ["north", "south", "east", "west"]
        weights = np.array([dw.get(d, 1.0) for d in dirs], dtype=float)
        perturbation = self._rng.uniform(
            -self.config.imbalance_max, self.config.imbalance_max, size=4
        )
        new_weights = np.maximum(0.1, weights + perturbation)
        new_weights = new_weights / np.mean(new_weights)  # normalize average weight to 1.0

        new_directional_weights = {
            d: round(float(w), 3) for d, w in zip(dirs, new_weights)
        }

        new_demand = DemandProfile(
            base_lambda=new_lambda,
            directional_weights=new_directional_weights,
            turn_ratios=base_scenario.demand_profile.turn_ratios,
            burst_events=base_scenario.demand_profile.burst_events,
            incident_events=base_scenario.demand_profile.incident_events,
        )

        new_scenario = ScenarioConfig(
            scenario_id=f"{base_scenario.scenario_id}_dr",
            split=base_scenario.split,
            name=f"{base_scenario.name} (Randomized)",
            description=base_scenario.description,
            demand_profile=new_demand,
            duration_steps=base_scenario.duration_steps,
        )

        miss_rate = float(self._rng.uniform(0.0, self.config.miss_rate_max))
        latency_ms = int(self._rng.uniform(0, self.config.latency_max_ms))
        fp_lambda = float(self._rng.uniform(0.0, self.config.max_false_positive_lambda))

        fault = FaultProfile(
            name=f"fault_dr_{new_scenario.scenario_id}",
            miss_rate=miss_rate,
            latency_ms=latency_ms,
            false_positive_lambda=fp_lambda,
            jitter_std=self.config.jitter_std,
        )

        return new_scenario, fault
