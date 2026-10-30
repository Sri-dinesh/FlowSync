"""Coherent synthetic count misses and constant transport delay for SUMO.

Raw snapshots belong to capture, not the controller. Existing policies receive
only immutable Counts; source clocks describe measurement delivery for auditing.
"""
from collections import deque
from dataclasses import dataclass
import hashlib
import math

from research.policies.sumo_classical import Counts, observe

VERSION = "sumo_sensing_v1"
EMPTY = Counts((0,)*4, (0,)*4, (0,)*4)


@dataclass(frozen=True)
class Fault:
    name: str
    delay_ticks: int
    miss_probability: float

    def __post_init__(self):
        if (not isinstance(self.name, str) or not self.name or type(self.delay_ticks) is not int or self.delay_ticks < 0
                or type(self.miss_probability) not in (int, float) or not math.isfinite(self.miss_probability)
                or not 0 <= self.miss_probability <= 1):
            raise ValueError("Invalid synthetic sensing preset")


PRESETS = (Fault("clean", 0, 0.), Fault("delay2s", 20, 0.),
           Fault("miss30", 0, .3), Fault("delay2s_miss30", 20, .3))


@dataclass(frozen=True)
class Delivery:
    control_tick: int
    source_tick: int | None
    counts: Counts

    def __post_init__(self):
        if type(self.control_tick) is not int or self.control_tick < 0 or not isinstance(self.counts, Counts):
            raise ValueError("Invalid delivered count frame")
        if self.source_tick is None:
            if self.counts != EMPTY:
                raise ValueError("Missing delivery must contain zero counts")
        elif type(self.source_tick) is not int or not 0 <= self.source_tick <= self.control_tick:
            raise ValueError("Future or malformed source clock")

    def to_dict(self):
        return dict(control_tick=self.control_tick, source_tick=self.source_tick,
                    age_ticks=None if self.source_tick is None else self.control_tick-self.source_tick,
                    counts=self.counts.to_dict())


class CountSensor:
    def __init__(self, fault: Fault, seed: int):
        if not isinstance(fault, Fault) or type(seed) is not int or seed < 0:
            raise ValueError("A sensing preset and nonnegative seed are required")
        self.fault, self.seed, self.next_tick = fault, seed, 0
        self._frames = deque(maxlen=fault.delay_ticks+1)

    def step(self, vehicles, tick: int) -> Delivery:
        if type(tick) is not int or tick != self.next_tick:
            raise ValueError("Capture ticks must be consecutive from zero")
        clean = observe(vehicles)  # Validate the whole snapshot before thinning.
        if not self.fault.miss_probability:
            corrupted = clean
        else:
            threshold = int(self.fault.miss_probability*(1 << 64))
            retained = [v for v in vehicles if int.from_bytes(hashlib.sha256(
                f"{VERSION}|{self.seed}|{tick}|{v[0]}".encode()).digest()[:8], "big") >= threshold]
            corrupted = observe(retained)
        self._frames.append((tick, corrupted))
        source, counts = self._frames[0] if len(self._frames) == self._frames.maxlen else (None, EMPTY)
        self.next_tick += 1
        return Delivery(tick, source, counts)
