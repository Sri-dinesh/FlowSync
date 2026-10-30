"""Observed-cohort green extension, with explicitly attributed pressure references.

Advanced-MP: Zhang et al., https://arxiv.org/abs/2112.10107 (Algorithm 1).
The extension proxy is a research hypothesis, not a bound on full-run delay.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from server.app.controllers.max_pressure import PHASE_MOVEMENTS, MaxPressureController
from server.app.simulation.traffic_math import DEST_MAP
from server.app.simulation.traffic_signal import TrafficSignal

METHODS = (
    "mp_all_native", "mp_upstream_native", "mp_upstream_2s",
    "advanced_mp_w1", "advanced_mp_w2", "advanced_mp_w4", "age_gated_advanced_mp",
    "point_extension", "no_age_extension", "window_extension",
)
EXTENSION_SECONDS = 2.
MAX_PACKET_AGE = .5
PROXY_MARGIN_VEHICLE_SECONDS = 1.


@dataclass(frozen=True)
class Timing:
    min_green: float = 8.
    yellow: float = 2.
    all_red: float = 3.
    max_green: float = 40.
    starvation: float = 45.

    def __post_init__(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.min_green, self.yellow, self.all_red, self.max_green, self.starvation)):
            raise ValueError("Invalid declared signal timings")


@lru_cache(maxsize=16)
def earliest_return_seconds(timing):
    """Executable earliest switch-away/serve-minimum/switch-back, no traffic/RNG."""
    signal = TrafficSignal(red_duration=timing.all_red)
    signal.min_green_duration = signal.MIN_GREEN_TIME = timing.min_green
    signal.yellow_duration = timing.yellow
    signal.time_in_phase = timing.min_green
    visited_other = False
    limit = math.ceil((timing.min_green+2*(timing.yellow+timing.all_red)+2)/.1)
    for tick in range(limit):
        signal.tick(.1, requested_phase=0 if visited_other else 1, lanes=None)
        visited_other |= signal.current_phase == 1 and signal.color.name == "GREEN"
        if visited_other and signal.current_phase == 0 and signal.color.name == "GREEN":
            return (tick+1)*.1
    raise ValueError("Declared timing did not complete a physical return cycle")


def _argmax(scores, current):
    highest = max(scores.values())
    return current if scores[current] == highest else max(scores, key=lambda phase: (scores[phase], -phase))


def pressure_phase(state, current, *, subset="upstream"):
    controller = MaxPressureController()
    movement = controller.compute_movement_pressures(state.counts(subset), state.outgoing())
    return _argmax(controller.compute_phase_pressures(movement), current)


def advanced_phase(state, current, weight):
    """One-lane/movement adaptation: signed queued EP and effective running demand.

    Unknown motion counts as queued. Running support needs observed advancing
    positions and source distance <= declared vmax * action duration. The paper's
    strict demand comparison is preserved; ties prefer the current phase here.
    """
    queue, outgoing = state.counts("queued"), state.outgoing(queued=True)
    scores = {p: sum(queue[m]-outgoing[DEST_MAP[m]] for m in movements)
              for p, movements in PHASE_MOVEMENTS.items()}
    running = sum(m.kind == "moving" and m.track.movement in PHASE_MOVEMENTS[current]
                  and 0 <= state.calibration.stop_line-m.track.position <= state.calibration.max_speed*EXTENSION_SECONDS
                  for m in state.motions)
    return current if running*weight > max(scores.values()) else _argmax(scores, current)


def age_gated_reference(state, current):
    age = state.packet.age_s
    if age is None or age > MAX_PACKET_AGE+1e-9:
        return pressure_phase(state, current)
    return advanced_phase(state, current, 2.)


def choose_extension(state, context, timing, mode):
    reference = age_gated_reference(state, context.current_phase)
    diagnostics = dict(reference=reference, proposed=reference, reason="reference_hold", used_ids=[],
                       service_proxy=0., opposing_proxy=0., source_age_s=state.packet.age_s)
    if reference == context.current_phase:
        return reference, diagnostics
    age = state.packet.age_s
    if age is None or age > MAX_PACKET_AGE+1e-9:
        diagnostics["reason"] = "missing_or_stale_support"
        return reference, diagnostics
    if context.time_in_phase+EXTENSION_SECONDS > timing.max_green:
        diagnostics["reason"] = "maximum_green_guard"
        return reference, diagnostics
    if any(value+EXTENSION_SECONDS >= timing.starvation for phase, value in (context.phase_starvation_times or {}).items()
           if phase != context.current_phase):
        diagnostics["reason"] = "phase_service_guard"
        return reference, diagnostics
    age = 0. if mode == "no_age_extension" else age
    return_time = earliest_return_seconds(timing)
    calibration = state.calibration
    headway = calibration.spacing/calibration.max_speed
    benefit, used = 0., []
    for movement in PHASE_MOVEMENTS[context.current_phase]:
        lane = sorted((m for m in state.motions if m.track.movement == movement
                       and m.track.position <= calibration.stop_line), key=lambda m: -m.track.position)
        service_at = -headway
        for motion in lane:
            # A stopped/unknown or possibly already departed leader supplies no
            # evidence that a following vehicle can be served during this hold.
            if motion.kind != "moving":
                break
            distance = calibration.stop_line-motion.track.position
            low_speed, speed, high_speed = motion.speed
            earliest = max(0., distance-calibration.position_error)/high_speed-age
            latest = (distance+calibration.position_error)/low_speed-age
            if mode == "point_extension":
                earliest = latest = distance/speed-age
            if earliest <= 0:
                break
            service_at = max(latest, service_at+headway)
            if service_at > EXTENSION_SECONDS:
                break
            benefit += max(0., return_time-service_at)
            used.append(motion.track.track_id)
    upstream = state.counts("upstream")
    opposing = EXTENSION_SECONDS*sum(upstream[m] for p, movements in PHASE_MOVEMENTS.items()
                                     if p != context.current_phase for m in movements)
    proposed = context.current_phase if used and benefit > opposing+PROXY_MARGIN_VEHICLE_SECONDS else reference
    diagnostics.update(proposed=proposed, reason="supported_extension" if proposed != reference else "insufficient_proxy_gain",
                       service_proxy=benefit, opposing_proxy=opposing, used_ids=used, earliest_return_s=return_time)
    return proposed, diagnostics


class ArrivalExtension:
    """Small research interface: immutable delivered state + public signal context."""
    def __init__(self, method, timing):
        if method not in METHODS:
            raise ValueError("Unknown arrival-window method")
        self.method, self.timing = method, timing
        self.next_decision = self.held = 0
        self.diagnostics = {}

    def act(self, state, context):
        if not context.is_decision_step:
            self.diagnostics = dict(gate=False, reason="physical_lock", proposed=context.current_phase)
            return context.current_phase
        if context.timestep < self.next_decision:
            self.diagnostics = dict(gate=False, reason="cached", proposed=self.held)
            return self.held
        if self.method == "mp_all_native":
            proposed = pressure_phase(state, context.current_phase, subset="all")
        elif self.method.startswith("mp_upstream"):
            proposed = pressure_phase(state, context.current_phase)
        elif self.method.startswith("advanced_mp_w"):
            proposed = advanced_phase(state, context.current_phase, float(self.method.rsplit("w", 1)[1]))
        elif self.method == "age_gated_advanced_mp":
            proposed = age_gated_reference(state, context.current_phase)
        else:
            proposed, diagnostic = choose_extension(state, context, self.timing, self.method)
            self.diagnostics = {**diagnostic, "gate": True}
        if not self.method.endswith("extension"):
            self.diagnostics = dict(gate=True, reason="reference", proposed=proposed)
        self.held = proposed
        self.next_decision = context.timestep+(1 if self.method.endswith("native") else 20)
        return proposed
