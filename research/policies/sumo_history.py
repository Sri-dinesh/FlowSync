"""Causal pressure means and lag controls; established filtering, no fitting."""
from collections import deque
from dataclasses import dataclass
import re

from research.observation.sumo_sensing import Delivery, PRESETS
from research.policies.sumo_classical import phase_pressures


@dataclass(frozen=True)
class Method:
    name: str
    fault: str
    estimator: str

    def __post_init__(self):
        if (not isinstance(self.name, str) or not re.fullmatch(r"[a-z0-9_]+", self.name)
                or self.fault not in {f.name for f in PRESETS} or self.estimator not in ("current", "lag", "mean")):
            raise ValueError("Unknown history method, sensor preset or estimator")


class PressureHistory:
    def __init__(self, window_ticks):
        if type(window_ticks) is not int or window_ticks < 0:
            raise ValueError("History span must be a nonnegative integer number of ticks")
        self.window_ticks, self.next_tick = window_ticks, 0
        self.frames, self.total = deque(), [0, 0]

    def push(self, delivered):
        if not isinstance(delivered, Delivery) or delivered.control_tick != self.next_tick:
            raise ValueError("History requires consecutive delivered frames from tick zero")
        pressure = phase_pressures(delivered.counts)
        if len(self.frames) == self.window_ticks+1:
            _, old = self.frames.popleft()
            for phase in (0, 1): self.total[phase] -= old[phase]
        self.frames.append((delivered, pressure))
        for phase in (0, 1): self.total[phase] += pressure[phase]
        self.next_tick += 1

    def state(self, estimator):
        if not self.frames or estimator not in ("current", "lag", "mean"):
            raise ValueError("A known estimator and at least one delivered frame are required")
        ready = len(self.frames) == self.window_ticks+1
        lag = self.frames[0][1] if ready else (0, 0)
        scores = self.frames[-1][1] if estimator == "current" else lag if estimator == "lag" else tuple(self.total)
        sources = [d.source_tick for d, _ in self.frames if d.source_tick is not None]
        return dict(score_numerators=list(scores), score_divisor=len(self.frames) if estimator == "mean" else 1,
            current_pressures=list(self.frames[-1][1]), lag_pressures=list(lag), lag_ready=ready,
            buffered_frames=len(self.frames), missing_frames=len(self.frames)-len(sources),
            oldest_control_tick=self.frames[0][0].control_tick, newest_control_tick=self.frames[-1][0].control_tick,
            oldest_source_tick=min(sources) if sources else None, newest_source_tick=max(sources) if sources else None)


def propose(method, history, clock):
    state = history.state(method.estimator)
    def select(scores):
        return (1-clock.phase if clock.stage == "green" and clock.age >= 80
                and scores[1-clock.phase] > scores[clock.phase] else clock.phase)
    return dict(proposal=select(state["score_numerators"]), current_proposal=select(state["current_pressures"]),
                estimator=method.estimator, history=state)
