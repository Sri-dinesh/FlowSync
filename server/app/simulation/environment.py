"""Gymnasium environment for traffic signal control simulation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Discrete

from ..config import settings
from ..schemas.simulation_schema import SimulationFrame, build_frame
from .intersection import Intersection
from .traffic_signal import SignalColor
from .traffic_math import (
    MAX_CAP,
    MOVEMENT_KEYS,
    compute_movement_pressures,
    compute_phase_pressure,
    compute_total_pressure,
    normalize_total_pressure,
)
from .demand_forecast import ArrivalForecaster
from ..rl.hyperparams import HyperParams

HP = HyperParams()

OBS_DIM = HP.STATE_DIM  # = 28


class TrafficEnv(gym.Env):
    """
    Single-intersection RL environment.

    Key behavioural properties:
    - 28-D observation: 12 queue dims + 4 phase + 4 signal-context + 8 EWMA forecast
    - Semi-MDP: `is_decision_step` is True only when the signal is GREEN and has
      passed MIN_GREEN_TIME. Trainer should only push transitions on decision steps.
    - Executed action: `step()` returns the actually-executed phase in info["executed_action"].
    - Reward decomposition: info["reward_components"] gives per-term breakdown.
    - Demand forecast: ArrivalForecaster provides 8 predictive features for anticipatory control.
    """

    def __init__(
        self,
        max_steps: Optional[int] = None,
        red_duration: Optional[float] = None,
    ) -> None:
        super().__init__()
        self.intersection = Intersection(
            spawn_lambda=HP.TRAINING_LAMBDA,
            red_duration=(
                settings.signal_red_duration if red_duration is None else red_duration
            ),
        )
        self.observation_space = Box(
            # Forecast growth/trend features are signed.
            low=-np.ones(OBS_DIM, dtype=np.float32),
            high=np.ones(OBS_DIM, dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = Discrete(4)
        self.max_steps = int(max_steps or HP.MAX_STEPS_PER_EPISODE)

        self._last_reward: float = 0.0
        self._episode: int = 0
        self._env_step_count: int = 0

        self.forecaster = ArrivalForecaster()

        self.reward_component_accumulators: Dict[str, float] = {
            "pressure":   0.0,
            "delay":      0.0,
            "throughput": 0.0,
            "switch":     0.0,
            "starvation": 0.0,
            "max_green":  0.0,
            "balance":    0.0,
        }
        self.watchdog_override_count: int = 0
        self.total_decision_steps: int = 0
        self.passed_vehicle_waits: List[float] = []

    def set_traffic_profile(self, profile: Any) -> None:
        """Forward traffic profile assignment to underlying intersection."""
        self.intersection.set_traffic_profile(profile)

    def reset(
        self,
        seed: int | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self._episode += 1
        self.intersection.reset()
        # Seed spawner RNG directly so episode generation is strictly repeatable.
        if seed is not None:
            self.intersection.spawner.set_seed(seed)
        self.intersection.spawner.set_enabled(True)
        self._last_reward = 0.0

        self.forecaster.reset()
        for k in self.reward_component_accumulators:
            self.reward_component_accumulators[k] = 0.0
        self.watchdog_override_count = 0
        self.total_decision_steps = 0
        self._env_step_count = 0
        self.passed_vehicle_waits = []

        return self._get_obs(), {}

    @property
    def is_decision_step(self) -> bool:
        """True only when signal is GREEN and has passed min_green clearance."""
        signal = self.intersection.signal
        return signal.color == SignalColor.GREEN and signal.can_switch_phase

    def compute_reward(
        self,
        prev_pressures: Dict[str, float],
        curr_pressures: Dict[str, float],
        vehicles_passed: int,
        phase_changed: bool,
        signal,
        prev_phase: int | None = None,
        delta_total_wait: float = 0.0,
        delay_incurred: Optional[float] = None,
        dt: float = 0.1,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Delay-anchored reward with pressure shaping and component decomposition.

        The primary term is delay incurred *during this tick*.  The previous
        reward used the change in wait stored on vehicles still in the scene;
        removing a long-waiting vehicle therefore created a large positive
        reward, even though that wait had already happened.

        Returns: (total_reward, components_dict)
        """
        # Backward-compatible fallback is retained for external callers, while
        # the environment always supplies the exact per-tick delay increment.
        if delay_incurred is None:
            delay_incurred = max(0.0, delta_total_wait)
        delay_reward = -float(delay_incurred) / 10.0

        total_curr = compute_total_pressure(curr_pressures)
        # Penalize the pressure level, not only a telescoping difference.  A
        # pure difference can be gamed at an arbitrary episode boundary.
        pressure_reward = -total_curr * 0.05 * dt

        throughput_reward = vehicles_passed * 0.10

        # Penalize phase switches when previous phase had high queue pressure.
        if phase_changed and prev_phase is not None:
            prev_phase_pressure = compute_phase_pressure(prev_pressures, prev_phase)
            switch_penalty = -0.10 if prev_phase_pressure > 0.5 else -0.03
        else:
            switch_penalty = 0.0

        starved = signal.get_starved_phases()
        starvation_penalty = -0.10 * len(starved) * dt

        max_green_penalty = -0.10 * dt if signal.is_max_green_exceeded else 0.0

        # Reserved in telemetry for backward compatibility. A positive balance
        # bonus can reward uniformly high congestion, so it stays disabled.
        balance_bonus = 0.0

        components = {
            "delay":      delay_reward,
            "pressure":   pressure_reward,
            "throughput": throughput_reward,
            "switch":     switch_penalty,
            "starvation": starvation_penalty,
            "max_green":  max_green_penalty,
            "balance":    balance_bonus,
        }
        return float(sum(components.values())), components

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Run one simulation tick (dt=0.1s).

        BUG-01: Returns executed_action in info; trainer must use this for replay buffer.
        Semi-MDP (Task 2.1): is_decision_step gates buffer pushes in trainer.
        Forecast (Task 4.1): ArrivalForecaster ticked here with spawn count.
        """
        signal = self.intersection.signal
        proposed_action = action
        self._env_step_count += 1

        is_decision_step = (
            signal.color == SignalColor.GREEN and signal.can_switch_phase
        )

        was_overridden = False
        override_reason: Optional[str] = None
        if (
            is_decision_step
            and signal.is_max_green_exceeded
            and action == signal.current_phase
        ):
            action = self._get_best_alternative_phase()
            was_overridden = True
            override_reason = "max_green_exceeded"
            self.watchdog_override_count += 1

        starved = signal.get_starved_phases()
        if is_decision_step and starved:
            starved_phase = max(
                starved, key=lambda phase: signal.phase_starvation_timer[phase]
            )
            if starved_phase != signal.current_phase:
                action = starved_phase
                was_overridden = True
                override_reason = f"starvation_phase_{starved_phase}"
                self.watchdog_override_count += 1

        requested_action = action

        prev_pressures = self._compute_movement_pressures(self.intersection)
        prev_passed = self.intersection.total_passed
        prev_phase = self.intersection.signal.current_phase
        prev_actual_phase = self.intersection.signal.current_phase
        prev_wait = self.intersection.get_total_wait_time()

        passed_vehicles = self.intersection.tick(dt=0.1, action=requested_action)
        for pv in passed_vehicles:
            self.passed_vehicle_waits.append(pv.wait_time)

        curr_pressures = self._compute_movement_pressures(self.intersection)
        curr_passed = self.intersection.total_passed
        vehicles_passed_this_step = curr_passed - prev_passed

        # Detect true physical phase transitions (committed yellow clearance or completed switch),
        # avoiding spurious penalties on proposals blocked by minimum green time.
        new_actual_phase = self.intersection.signal.current_phase
        executed_action = (
            self.intersection.signal.pending_phase
            if self.intersection.signal.pending_phase is not None
            else new_actual_phase
        )
        actually_switched = (new_actual_phase != prev_actual_phase)
        switch_just_initiated = (
            self.intersection.signal.pending_phase is not None
            and self.intersection.signal.color.name == "YELLOW"
            and self.intersection.signal.time_in_phase < 0.15  # just initiated
        )
        phase_changed = actually_switched or switch_just_initiated

        curr_wait = self.intersection.get_total_wait_time()
        delta_total_wait = curr_wait - prev_wait

        spawned_this_step = self.intersection._generated_last_tick
        self.forecaster.tick(dt=0.1, spawned_this_step=max(0, spawned_this_step))

        reward, components = self.compute_reward(
            prev_pressures=prev_pressures,
            curr_pressures=curr_pressures,
            vehicles_passed=vehicles_passed_this_step,
            phase_changed=phase_changed,
            signal=self.intersection.signal,
            prev_phase=prev_phase,
            delta_total_wait=delta_total_wait,
            delay_incurred=self.intersection._delay_this_tick,
            dt=0.1,
        )
        self._last_reward = reward

        for k, v in components.items():
            self.reward_component_accumulators[k] = (
                self.reward_component_accumulators.get(k, 0.0) + v
            )
        if is_decision_step:
            self.total_decision_steps += 1

        obs = self._get_obs()
        terminated = False
        truncated = self.intersection.timestep >= self.max_steps

        override_rate = (
            self.watchdog_override_count / max(self.total_decision_steps, 1) * 100.0
        )

        info: Dict[str, Any] = {
            "state_version":           "v1_28d",
            "reward_version":          "v4_incremental_delay",
            "executed_action":         executed_action,
            "proposed_action":         proposed_action,
            "was_overridden":          was_overridden,
            "override_reason":         override_reason,
            "is_decision_step":        is_decision_step,
            "reward_components":       components,
            "reward_accumulators":     dict(self.reward_component_accumulators),
            "pressures":               curr_pressures,
            "vehicles_passed":         vehicles_passed_this_step,
            "avg_wait_time":           self.intersection.get_avg_wait_time(),
            "starved_phases":          starved,
            "watchdog_override_count": self.watchdog_override_count,
            "total_decision_steps":    self.total_decision_steps,
            "watchdog_override_rate":  override_rate,
            "forecast":                self.forecaster.get_debug_info(),
        }

        return obs, reward, terminated, truncated, info

    def get_valid_action_mask(self) -> np.ndarray:
        """Return the action set shared by training, targets and inference.

        The current phase is always legal (holding green).  Other phases become
        legal when they have controllable demand.  Right turns are excluded
        because this simulator models them as signal-independent movements.
        """
        signal = self.intersection.signal
        mask = np.zeros(self.action_space.n, dtype=bool)
        mask[signal.current_phase] = True
        if signal.color != SignalColor.GREEN or not signal.can_switch_phase:
            return mask

        queues = self.intersection.get_movement_queues()
        phase_movements = {
            0: ("north_straight", "south_straight"),
            1: ("east_straight", "west_straight"),
            2: ("north_left", "south_left"),
            3: ("east_left", "west_left"),
        }
        for phase, movements in phase_movements.items():
            if sum(queues.get(m, 0) for m in movements) > 0:
                mask[phase] = True
        return mask

    def advance_to_decision_point(self) -> np.ndarray:
        """Warm the initial phase until a physically executable decision exists."""
        while not (
            self.intersection.signal.color == SignalColor.GREEN
            and self.intersection.signal.can_switch_phase
        ):
            _, _, _, truncated, _ = self.step(self.intersection.signal.current_phase)
            if truncated:
                break
        return self._get_obs()

    def reset_to_decision(
        self,
        seed: int | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        self.reset(seed=seed, options=options)
        return self.advance_to_decision_point(), {
            "valid_action_mask": self.get_valid_action_mask(),
        }

    def step_decision(
        self,
        action: int,
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Execute one causal, variable-duration signal-control decision.

        Holding a phase advances by DECISION_DT.  A phase change includes the
        yellow/all-red clearance and the new minimum green.  Rewards are summed
        across those micro-ticks and the returned discount captures the actual
        elapsed duration for a semi-Markov Bellman target.
        """
        if not (0 <= int(action) < self.action_space.n):
            raise ValueError(f"Invalid signal action: {action}")
        if not (
            self.intersection.signal.color == SignalColor.GREEN
            and self.intersection.signal.can_switch_phase
        ):
            self.advance_to_decision_point()

        action = int(action)
        start_phase = self.intersection.signal.current_phase
        elapsed = 0.0
        cumulative_reward = 0.0
        discount_weight = 1.0
        last_info: Dict[str, Any] = {}
        terminated = truncated = False
        committed_action = action
        first_tick = True

        while True:
            _, reward, terminated, truncated, last_info = self.step(committed_action)
            if first_tick:
                committed_action = int(last_info.get("executed_action", committed_action))
                first_tick = False
            cumulative_reward += discount_weight * reward
            elapsed += 0.1
            discount_weight *= HP.GAMMA ** (0.1 / HP.DECISION_DT)

            at_next_gate = (
                elapsed + 1e-9 >= HP.DECISION_DT
                and self.intersection.signal.color == SignalColor.GREEN
                and self.intersection.signal.can_switch_phase
            )
            if terminated or truncated or at_next_gate:
                break

        last_info = dict(last_info)
        last_info.update({
            "executed_action": committed_action,
            "decision_start_phase": start_phase,
            "decision_duration_seconds": elapsed,
            "bootstrap_discount": HP.GAMMA ** (elapsed / HP.DECISION_DT),
            "valid_action_mask": self.get_valid_action_mask(),
        })
        return self._get_obs(), cumulative_reward, terminated, truncated, last_info

    def _get_best_alternative_phase(self) -> int:
        """When max green exceeded, pick the phase with highest pressure."""
        pressures = self._compute_movement_pressures(self.intersection)
        current = self.intersection.signal.current_phase
        best_phase = current
        best_pressure = -1.0
        for phase in range(4):
            if phase == current:
                continue
            phase_pressure = compute_phase_pressure(pressures, phase)
            if phase_pressure > best_pressure:
                best_pressure = phase_pressure
                best_phase = phase
        return best_phase

    def _get_phase_for_direction(self, direction: str) -> int:
        """Returns the most appropriate phase for a starved direction."""
        DIRECTION_PHASES = {
            "north": 0, "south": 0,
            "east":  1, "west":  1,
        }
        return DIRECTION_PHASES.get(direction, 0)

    def _compute_movement_pressures(self, intersection: Intersection) -> Dict[str, float]:
        """
        Compute destination-aware movement pressure using shared DEST_MAP (BUG-04).
        Uses traffic_math.compute_movement_pressures for Sim-Real parity.
        """
        movement_queues = intersection.get_movement_queues()
        outgoing = intersection.get_outgoing_counts()
        return compute_movement_pressures(movement_queues, outgoing, MAX_CAP)

    def _get_obs(self) -> np.ndarray:
        """
        Build 28-dim observation vector (Task 4.2).

        Layout:
          Dims 0-11:  Normalized movement queue counts (MOVEMENT_KEYS canonical order)
          Dims 12-15: One-hot current signal phase
          Dim  16:    Time in phase / MAX_GREEN_TIME
          Dim  17:    Is transitioning (yellow/all-red = 1.0)
          Dim  18:    Destination-aware total pressure (shared DEST_MAP, BUG-04)
          Dim  19:    Max starvation timer / STARVATION_THRESHOLD
          Dims 20-27: Demand forecast features (EWMA 5s/10s/20s, growth, burst, etc.)
        """
        movement_queues = self.intersection.get_movement_queues()
        signal = self.intersection.signal
        pressures = self._compute_movement_pressures(self.intersection)

        movements = [
            float(np.tanh(movement_queues.get(k, 0) / 15.0))
            for k in MOVEMENT_KEYS
        ]

        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[signal.current_phase] = 1.0

        time_norm = min(1.0, signal.time_in_phase / signal.MAX_GREEN_TIME)

        is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0

        total_pressure = compute_total_pressure(pressures)
        pressure_norm = normalize_total_pressure(total_pressure)

        starv_timers = list(signal.phase_starvation_timer.values())
        max_starv_norm = min(max(starv_timers) / signal.STARVATION_THRESHOLD, 1.0)

        forecast_features = self.forecaster.get_forecast_features().tolist()

        obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm] + forecast_features
        assert len(obs) == OBS_DIM, f"Obs dim mismatch: got {len(obs)}, expected {OBS_DIM}"
        return np.array(obs, dtype=np.float32)

    def render(self) -> SimulationFrame:
        return build_frame(
            self.intersection,
            mode="ai",
            reward=self._last_reward,
            episode=self._episode,
        )

    def get_episode_telemetry(self) -> Dict[str, Any]:
        """Return full episode telemetry for broadcast to training WebSocket."""
        override_rate = (
            self.watchdog_override_count / max(self.total_decision_steps, 1) * 100.0
        )
        comp_dict = dict(self.reward_component_accumulators)
        steps = max(self.total_decision_steps, 1)
        comp_stats = {
            k: {
                "total": round(v, 3),
                "mean_per_decision": round(v / steps, 4),
            }
            for k, v in comp_dict.items()
        }
        return {
            "state_version":           "v1_28d",
            "reward_version":          "v4_incremental_delay",
            "reward_components":       comp_dict,
            "reward_component_stats":  comp_stats,
            "watchdog_override_count": self.watchdog_override_count,
            "watchdog_override_rate":  override_rate,
            "total_decision_steps":    self.total_decision_steps,
            "forecast_debug":          self.forecaster.get_debug_info(),
        }
