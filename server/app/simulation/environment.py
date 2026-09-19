"""
environment.py — FlowSync TrafficEnv (RL Gymnasium Environment)
================================================================
All improvements integrated in this version:

  Phase 0:
  - Task 0.2:  Reward component decomposition + watchdog override telemetry

  Phase 1:
  - BUG-01:    Returns executed_action in info dict so trainer stores correct action
  - BUG-04:    Uses shared traffic_math.DEST_MAP (eliminates Sim-Real divergence)

  Phase 2:
  - Task 2.1:  Semi-MDP decision flag: is_decision_step tracks causal decision points

  Phase 3:
  - Task 3.1:  Delay-anchored reward function (R_delay + R_pressure + R_throughput
               − R_switch − R_starvation − R_max_green + R_balance)

  Phase 4:
  - Task 4.1:  Integrates ArrivalForecaster into intersection tick loop
  - Task 4.2:  Observation vector expanded to 28-D (dims 20-27 = forecast features)
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Discrete

from ..config import settings
from ..schemas.simulation_schema import SimulationFrame, build_frame
from .intersection import Intersection
from .traffic_signal import PHASE_GREEN_LANES, SignalColor
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

# ── Observation layout ──────────────────────────────────────────────────────
#   Dims 0-11:  Movement queue counts (12)
#   Dims 12-15: Phase one-hot encoding (4)
#   Dims 16-19: Signal context [time_norm, is_trans, pressure_norm, starv_norm] (4)
#   Dims 20-27: Demand forecast features (8)  ← Task 4.2 addition
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

    def __init__(self) -> None:
        super().__init__()
        self.intersection = Intersection(
            spawn_lambda=HP.TRAINING_LAMBDA,
            red_duration=settings.signal_red_duration,
        )
        self.observation_space = Box(
            low=np.zeros(OBS_DIM, dtype=np.float32),
            high=np.ones(OBS_DIM, dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = Discrete(4)

        self._last_reward: float = 0.0
        self._episode: int = 0
        self._env_step_count: int = 0  # BUG-E: per-episode step counter

        # ── Task 4.1: Demand forecaster ─────────────────────────────────────
        self.forecaster = ArrivalForecaster()

        # ── Task 0.2: Reward component telemetry ────────────────────────────
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

    # ────────────────────────────────────────────────────────────────────────
    # Reset
    # ────────────────────────────────────────────────────────────────────────
    def reset(
        self,
        seed: int | None = None,
        options: Dict[str, Any] | None = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self._episode += 1
        self.intersection.reset()
        self.intersection.spawner.set_enabled(True)
        self._last_reward = 0.0

        # Reset forecaster and telemetry
        self.forecaster.reset()
        for k in self.reward_component_accumulators:
            self.reward_component_accumulators[k] = 0.0
        self.watchdog_override_count = 0
        self.total_decision_steps = 0
        self._env_step_count = 0  # BUG-E: reset per-episode counter

        return self._get_obs(), {}

    # ────────────────────────────────────────────────────────────────────────
    # Reward: Delay-Anchored (Task 3.1)
    # ────────────────────────────────────────────────────────────────────────
    def compute_reward(
        self,
        prev_pressures: Dict[str, float],
        curr_pressures: Dict[str, float],
        vehicles_passed: int,
        phase_changed: bool,
        signal,
        prev_phase: int | None = None,
        delta_total_wait: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Delay-anchored reward with pressure shaping and component decomposition.

        Components:
          R_delay     = −Δ(total_wait_time) / 10.0    (BUG-D: amplified from /20 to /10)
          R_pressure  = (Σprev_p − Σcurr_p) × 0.8    (secondary: pressure reduction)
          R_throughput= vehicles_passed × 0.25        (BUG-D: raised from 0.15 to 0.25)
          R_switch    = −0.2 if actual switch AND pressure > 0.5 (BUG-D: threshold 0.3→0.5)
          R_starvation= −1.5 × n_starved              (penalise queue neglect)
          R_max_green = −0.8 if max-green exceeded     (penalise phase hogging)
          R_balance   = +0.15 if balanced              (encourage fairness)

        Returns: (total_reward, components_dict)
        """
        # 1. Delay (primary) — BUG-D: /10.0 makes this the dominant signal
        delay_reward = -delta_total_wait / 10.0

        # 2. Pressure differential
        total_prev = compute_total_pressure(prev_pressures)
        total_curr = compute_total_pressure(curr_pressures)
        pressure_reward = (total_prev - total_curr) * 0.8

        # 3. Throughput — BUG-D: raised coefficient for clearer signal
        throughput_reward = vehicles_passed * 0.25

        # 4. Switch penalty — BUG-D: threshold 0.5 (was 0.3) — only penalize high-pressure switches
        if phase_changed and prev_phase is not None:
            prev_phase_pressure = compute_phase_pressure(prev_pressures, prev_phase)
            switch_penalty = -0.2 if prev_phase_pressure > 0.5 else 0.0
        else:
            switch_penalty = 0.0

        # 5. Starvation penalty
        starved = signal.get_starved_directions()
        starvation_penalty = -1.5 * len(starved)

        # 6. Max-green violation
        max_green_penalty = -0.8 if signal.is_max_green_exceeded else 0.0

        # 7. Balance bonus
        if total_curr > 0.05:
            phase_pressures = [compute_phase_pressure(curr_pressures, p) for p in range(4)]
            imbalance = max(phase_pressures) - min(phase_pressures)
            balance_bonus = 0.15 if imbalance < 0.2 else 0.0
        else:
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

    # ────────────────────────────────────────────────────────────────────────
    # Step
    # ────────────────────────────────────────────────────────────────────────
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Run one simulation tick (dt=0.1s).

        BUG-01: Returns executed_action in info; trainer must use this for replay buffer.
        Semi-MDP (Task 2.1): is_decision_step gates buffer pushes in trainer.
        Forecast (Task 4.1): ArrivalForecaster ticked here with spawn count.
        """
        signal = self.intersection.signal
        proposed_action = action
        self._env_step_count += 1  # BUG-E: increment per-episode counter

        # ── Semi-MDP: is this a causal decision step? ────────────────────────
        # True whenever the signal is GREEN (trainer/teacher may further subsample).
        # Yellow and all-red intervals are non-causal and always excluded.
        is_decision_step = (signal.color == SignalColor.GREEN)

        # ── Watchdog override: max-green ─────────────────────────────────────
        was_overridden = False
        if signal.is_max_green_exceeded and action == signal.current_phase:
            action = self._get_best_alternative_phase()
            was_overridden = True

        # ── Watchdog override: starvation ────────────────────────────────────
        starved = signal.get_starved_directions()
        if starved:
            starved_phase = self._get_phase_for_direction(starved[0])
            if starved_phase != signal.current_phase:
                action = starved_phase
                was_overridden = True
                self.watchdog_override_count += 1

        executed_action = action  # BUG-01: actual applied action

        # ── Pre-step snapshots ──────────────────────────────────────────────
        prev_pressures = self._compute_movement_pressures(self.intersection)
        prev_passed = self.intersection.total_passed
        prev_phase = self.intersection.signal.current_phase
        prev_actual_phase = self.intersection.signal.current_phase  # BUG-A: track real phase
        prev_wait = self.intersection.get_total_wait_time()
        prev_spawned = self.intersection._spawned_this_interval

        # ── Tick environment ─────────────────────────────────────────────────
        self.intersection.tick(dt=0.1, action=executed_action)

        # ── Post-step snapshots ──────────────────────────────────────────────
        curr_pressures = self._compute_movement_pressures(self.intersection)
        curr_passed = self.intersection.total_passed
        vehicles_passed_this_step = curr_passed - prev_passed

        # BUG-A FIX: phase_changed should detect REAL phase transitions, not blocked attempts.
        # Old logic: (executed_action != prev_phase AND color==GREEN) was backwards:
        #   - Real switch: color goes YELLOW -> GREEN check fails -> penalty NEVER fired
        #   - Blocked switch (min-green): color stays GREEN -> penalty DID fire spuriously
        # Fix: check if signal.current_phase actually changed after the tick, OR if
        # a yellow transition was just initiated (pending_phase set for first time).
        new_actual_phase = self.intersection.signal.current_phase
        actually_switched = (new_actual_phase != prev_actual_phase)
        switch_just_initiated = (
            self.intersection.signal.pending_phase is not None
            and self.intersection.signal.color.name == "YELLOW"
            and self.intersection.signal.time_in_phase < 0.15  # just started
        )
        phase_changed = actually_switched or switch_just_initiated

        curr_wait = self.intersection.get_total_wait_time()
        delta_total_wait = curr_wait - prev_wait

        # ── Task 4.1: Update arrival forecaster ──────────────────────────────
        spawned_this_step = self.intersection._spawned_this_interval - prev_spawned
        self.forecaster.tick(dt=0.1, spawned_this_step=max(0, spawned_this_step))

        # ── Compute reward ───────────────────────────────────────────────────
        reward, components = self.compute_reward(
            prev_pressures=prev_pressures,
            curr_pressures=curr_pressures,
            vehicles_passed=vehicles_passed_this_step,
            phase_changed=phase_changed,
            signal=self.intersection.signal,
            prev_phase=prev_phase,
            delta_total_wait=delta_total_wait,
        )
        self._last_reward = reward

        # ── Accumulate component telemetry ───────────────────────────────────
        for k, v in components.items():
            self.reward_component_accumulators[k] = (
                self.reward_component_accumulators.get(k, 0.0) + v
            )
        if is_decision_step:
            self.total_decision_steps += 1

        obs = self._get_obs()
        terminated = False
        truncated = self.intersection.timestep >= HP.MAX_STEPS_PER_EPISODE

        override_rate = (
            self.watchdog_override_count / max(self.total_decision_steps, 1) * 100.0
        )

        info: Dict[str, Any] = {
            # BUG-01: expose executed action for correct replay buffer push
            "executed_action":    executed_action,
            "proposed_action":    proposed_action,
            "was_overridden":     was_overridden,
            "is_decision_step":   is_decision_step,
            # reward telemetry
            "reward_components":  components,
            "reward_accumulators": dict(self.reward_component_accumulators),
            # standard telemetry
            "pressures":          curr_pressures,
            "vehicles_passed":    vehicles_passed_this_step,
            "avg_wait_time":      self.intersection.get_avg_wait_time(),
            "starved_directions": starved,
            # watchdog telemetry
            "watchdog_override_count": self.watchdog_override_count,
            "total_decision_steps":    self.total_decision_steps,
            "watchdog_override_rate":  override_rate,
            # Task 4.1: forecast debug
            "forecast": self.forecaster.get_debug_info(),
        }

        return obs, reward, terminated, truncated, info

    # ────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────────
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

        # Dims 0-11: queue values in canonical MOVEMENT_KEYS order
        movements = [
            min(1.0, movement_queues.get(k, 0) / MAX_CAP)
            for k in MOVEMENT_KEYS
        ]

        # Dims 12-15: one-hot phase
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[signal.current_phase] = 1.0

        # Dim 16: time in phase
        time_norm = min(1.0, signal.time_in_phase / signal.MAX_GREEN_TIME)

        # Dim 17: is transitioning
        is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0

        # Dim 18: destination-aware total pressure
        total_pressure = compute_total_pressure(pressures)
        pressure_norm = normalize_total_pressure(total_pressure)

        # Dim 19: max starvation timer
        starv_timers = list(signal.starvation_timer.values())
        max_starv_norm = min(max(starv_timers) / signal.STARVATION_THRESHOLD, 1.0)

        # Dims 20-27: demand forecast features (Task 4.2)
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
        return {
            "reward_components":       dict(self.reward_component_accumulators),
            "watchdog_override_count": self.watchdog_override_count,
            "watchdog_override_rate":  override_rate,
            "total_decision_steps":    self.total_decision_steps,
            "forecast_debug":          self.forecaster.get_debug_info(),
        }
