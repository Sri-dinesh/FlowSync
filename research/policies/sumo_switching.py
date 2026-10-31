"""A fixed pressure-advantage margin; established hysteresis, not a learned method."""
from dataclasses import dataclass

from research.policies.sumo_classical import choose_action, phase_pressures


@dataclass(frozen=True)
class Method:
    name: str
    controller: str
    fault: str
    margin: int

    def __post_init__(self):
        if (self.controller not in ("max_pressure", "fixed") or type(self.margin) is not int
                or self.margin < 0 or self.controller == "fixed" and self.margin != 0):
            raise ValueError("A nonnegative integer pressure margin is required; Fixed has zero margin")


def propose(method, packet, clock):
    raw = choose_action(method.controller, packet, clock)
    values = None if method.controller == "fixed" else phase_pressures(packet)
    held = (raw != clock.phase and method.margin > 0 and values[clock.phase] > 0
            and values[raw] - values[clock.phase] <= method.margin)
    return dict(proposal=clock.phase if held else raw, raw_proposal=raw,
                phase_pressures=None if values is None else list(values), margin=method.margin, margin_held=held)
