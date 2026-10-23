"""Pure observed-count controllers for the declared two-phase SUMO comparison."""
from dataclasses import dataclass
import math

DIRECTIONS = ("n", "s", "e", "w")
CONTROLLERS = ("halted", "fixed", "max_pressure")
FIXED_GREEN_TICKS = 300


@dataclass(frozen=True)
class Counts:
    incoming: tuple
    outgoing: tuple
    halted: tuple

    def __post_init__(self):
        for vector in (self.incoming, self.outgoing, self.halted):
            if not isinstance(vector, tuple) or len(vector) != 4 or any(type(v) is not int or v < 0 for v in vector):
                raise ValueError("Four nonnegative integer counts per vector are required")
        if any(h > q for h, q in zip(self.halted, self.incoming)):
            raise ValueError("Halted count exceeds incoming count")

    def to_dict(self):
        return {k: list(getattr(self, k)) for k in ("incoming", "outgoing", "halted")}

    @classmethod
    def from_dict(cls, values):
        if set(values) != {"incoming", "outgoing", "halted"}:
            raise ValueError("Malformed delivered count packet")
        return cls(*(tuple(values[k]) for k in ("incoming", "outgoing", "halted")))


@dataclass(frozen=True)
class Clock:
    phase: int
    stage: str
    age: int

    def __post_init__(self):
        if (type(self.phase) is not int or self.phase not in (0, 1) or self.stage not in ("green", "yellow", "red")
                or type(self.age) is not int or self.age < 0):
            raise ValueError("Invalid physical signal context")


def observe(vehicles):
    """Causal packet from a completed step; no IDs, backlog or future metadata."""
    incoming, outgoing, halted = [0]*4, [0]*4, [0]*4
    seen = set()
    for vid, edge, position, speed in vehicles:
        if (not isinstance(vid, str) or not vid or vid in seen or not isinstance(edge, str)
                or edge not in {d+suffix for d in DIRECTIONS for suffix in ("_in", "_out")} and not edge.startswith(":")
                or not all(type(v) in (float, int) and math.isfinite(v) and v >= 0 for v in (position, speed))):
            raise ValueError("Invalid/duplicate observed vehicle")
        seen.add(vid)
        if edge in {d+"_in" for d in DIRECTIONS}:
            index = DIRECTIONS.index(edge[0])
            incoming[index] += 1
            halted[index] += speed < .1
        elif edge in {d+"_out" for d in DIRECTIONS}:
            outgoing[DIRECTIONS.index(edge[0])] += 1
    return Counts(tuple(incoming), tuple(outgoing), tuple(halted))


def phase_pressures(packet):
    # Canonical destination pairing for straight-only movements: N->S, S->N,
    # E->W, W->E. Common equal normalization capacity cancels in the argmax.
    movements = [max(0, packet.incoming[i]-packet.outgoing[j]) for i, j in enumerate((1, 0, 3, 2))]
    return (sum(movements[:2]), sum(movements[2:]))


def choose_action(controller, packet, clock):
    if controller not in CONTROLLERS:
        raise ValueError("Unknown classical controller")
    if controller != "fixed" and not isinstance(packet, Counts):
        raise ValueError("Adaptive controllers require a delivered count packet")
    if clock.stage != "green" or clock.age < 80:
        return clock.phase
    if controller == "fixed":
        return 1-clock.phase if clock.age >= FIXED_GREEN_TICKS else clock.phase
    values = (sum(packet.halted[:2]), sum(packet.halted[2:])) if controller == "halted" else phase_pressures(packet)
    return clock.phase if values[clock.phase] == max(values) else int(values[1] > values[0])
