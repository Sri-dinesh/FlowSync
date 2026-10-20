"""Shared research scenario execution and observation boundary.

The sensor model is a count-sensor surrogate, not a validated CCTV detector.
Ground truth stays on the metric side of the controller boundary.
"""
from __future__ import annotations

import numpy as np

from server.app.controllers.base import ControllerContext
from server.app.simulation.demand_forecast import ArrivalForecaster
from server.app.simulation.traffic_math import (
    MOVEMENT_KEYS, MAX_CAP, compute_movement_pressures,
    compute_total_pressure, normalize_total_pressure,
)
from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS
from server.app.simulation.environment import TrafficEnv
from server.app.simulation.spawner import TrafficProfile
from server.app.rl.observations import DeliveredHistory, TEMPORAL_KEY

RESEARCH_REWARD_VERSION = "v5_single_switch_delay"


def build_environment(scenario):
    """One environment configuration shared by research training and evaluation."""
    if scenario.topology != "single_intersection":
        raise ValueError(f"Unsupported headless topology: {scenario.topology}")
    dp = scenario.demand_profile
    profile = TrafficProfile(
        id=scenario.scenario_id, name=scenario.name, description=scenario.description,
        directional_weights=dict(dp.directional_weights),
        turn_probs=[dp.turn_ratios["north"][t] for t in ("straight", "left", "right")],
        base_lambda=dp.base_lambda, lambda_multiplier=1.0,
        directional_turn_probs={d: [r[t] for t in ("straight", "left", "right")]
                                for d, r in dp.turn_ratios.items()},
    )
    env = TrafficEnv(max_steps=scenario.duration_steps, red_duration=scenario.red_duration,
                     enable_watchdogs=False, reward_version=RESEARCH_REWARD_VERSION)
    env.set_traffic_profile(profile)
    return env, profile


def apply_scenario_step(intersection, profile, demand, step):
    """Intervals are [start, end); directional multipliers change approach rates."""
    weights = dict(demand.directional_weights)
    global_multiplier = 1.0
    for event in demand.burst_events:
        if event.get("start_step", 0) <= step < event.get("end_step", 0):
            if event.get("directions"):
                for direction in event["directions"]:
                    weights[direction] *= event.get("multiplier", 1.0)
            else:
                global_multiplier *= event.get("multiplier", 1.0)
    base_weight = sum(demand.directional_weights.values())
    profile.directional_weights = weights
    intersection.set_spawn_rate(
        demand.base_lambda * global_multiplier * sum(weights.values()) / base_weight
    )
    factors = {d: 1.0 for d in weights}
    for event in demand.incident_events:
        if event.get("start_step", 0) <= step < event.get("end_step", 0):
            factors[event["direction"]] *= event["capacity_factor"]
    intersection.downstream_capacity_factors = factors
    return {"arrival_rate": intersection.spawner.lambda_rate,
            "directional_weights": dict(weights), "downstream_capacity_factors": factors.copy()}


class ObservedState:
    """Recompute policy features/masks only from the delivered sensor packet."""

    def __init__(self):
        self.forecaster = ArrivalForecaster()
        self.phase_waits = {p: 0.0 for p in range(4)}
        self.delivered_history = DeliveredHistory()

    def build(self, env, clean_obs, step, injector=None):
        signal = env.intersection.signal
        can_switch = signal.color.name == "GREEN" and signal.can_switch_phase
        ctx = ControllerContext(
            timestep=step, dt=0.1, current_phase=signal.current_phase,
            time_in_phase=signal.time_in_phase, color=signal.color.name,
            can_switch_phase=can_switch, is_decision_step=can_switch,
            outgoing_counts=env.intersection.get_outgoing_counts(),
            extra_telemetry={"spawned_this_step": env.intersection._generated_last_tick,
                             "phase_wait_semantics": "continuous observed demand without phase green; not individual vehicle wait"},
        )
        obs = np.copy(clean_obs)
        if injector is not None:
            obs = injector.corrupt_observation(obs, step=step, context=ctx)
        else:
            ctx.extra_telemetry["observation_age_ms"] = 0.0
        ctx.extra_telemetry[TEMPORAL_KEY] = self.delivered_history.update(obs, ctx).tolist()
        # tanh(count/15) is the trained policy encoding, not count/MAX_CAP.
        counts = np.rint(15.0 * np.arctanh(np.clip(obs[:12], 0, 0.999999))).astype(int)
        ctx.movement_queues = dict(zip(MOVEMENT_KEYS, counts.tolist()))
        mask = np.zeros(4, dtype=bool)
        mask[signal.current_phase] = True
        for phase, movements in PHASE_DEMAND_MOVEMENTS.items():
            has_demand = sum(ctx.movement_queues[m] for m in movements) > 0
            served = signal.color.name == "GREEN" and signal.current_phase == phase
            self.phase_waits[phase] = (self.phase_waits[phase] + 0.1 if has_demand and not served else 0.0)
            if can_switch and has_demand:
                mask[phase] = True
        ctx.phase_starvation_times = self.phase_waits.copy()
        ctx.valid_action_mask = mask
        # Lamp feedback is current even when camera frames are stale.
        obs[12:18] = clean_obs[12:18]
        pressures = compute_movement_pressures(ctx.movement_queues, ctx.outgoing_counts, MAX_CAP)
        obs[18] = normalize_total_pressure(compute_total_pressure(pressures))
        obs[19] = min(1.0, max(self.phase_waits.values()) / signal.STARVATION_THRESHOLD)
        self.forecaster.tick(0.1, ctx.extra_telemetry["spawned_this_step"])
        obs[20:28] = self.forecaster.get_forecast_features()
        return obs, ctx


class SignalAudit:
    """Observe actual simulator lamps and transitions, independent of proposal filters.

    Counts signal-state violations, not physical crashes or pedestrian safety.
    """

    def __init__(self):
        self.conflicts = 0
        self.clearance_violations = 0
        self.samples = 0

    def observe(self, before, signal, dt=0.1):
        self.samples += 1
        active = {phase for phase, movements in PHASE_DEMAND_MOVEMENTS.items()
                  if any(signal.is_green_for(*m.split("_", 1)) for m in movements)}
        self.conflicts += int(len(active) > 1)
        old_phase, old_color, old_time = before
        color = signal.color.name
        violation = False
        if old_phase != signal.current_phase and not (old_color == "RED" and color == "GREEN"):
            violation = True
        if old_color == "GREEN" and color != "GREEN":
            violation |= color != "YELLOW" or old_time + dt + 1e-8 < signal.min_green_duration
        if old_color == "YELLOW" and color != "YELLOW":
            violation |= color != "RED" or old_time + dt + 1e-8 < signal.yellow_duration
        if old_color == "RED" and color != "RED":
            violation |= color != "GREEN" or old_time + dt + 1e-8 < signal.red_duration
        self.clearance_violations += int(violation)
