from enum import Enum
from typing import Dict, List, Optional


class SignalPhase(Enum):
    NS_GREEN = 0
    EW_GREEN = 1
    NS_LEFT = 2
    EW_LEFT = 3


class SignalColor(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


PHASE_GREEN_LANES: Dict[int, List[str]] = {
    SignalPhase.NS_GREEN.value: ["north", "south"],
    SignalPhase.EW_GREEN.value: ["east", "west"],
    SignalPhase.NS_LEFT.value: ["north", "south"],
    SignalPhase.EW_LEFT.value: ["east", "west"],
}


class TrafficSignal:
    def __init__(self) -> None:
        self.current_phase: int = SignalPhase.NS_GREEN.value
        self.color: SignalColor = SignalColor.GREEN
        self.time_in_phase: float = 0.0
        self.fixed_duration: float = 30.0
        self.yellow_duration: float = 2.0
        self._pending_phase: Optional[int] = None

    def set_phase(self, phase: int) -> None:
        if phase == self.current_phase and self.color == SignalColor.GREEN:
            return
        self._pending_phase = phase
        self.color = SignalColor.YELLOW
        self.time_in_phase = 0.0

    def tick(self, dt: float) -> None:
        self.time_in_phase += dt

        if self.color == SignalColor.YELLOW:
            if self.time_in_phase >= self.yellow_duration:
                self.color = SignalColor.RED
                self.time_in_phase = 0.0
            return

        if self.color == SignalColor.RED:
            if self._pending_phase is not None:
                self.current_phase = self._pending_phase
                self._pending_phase = None
            self.color = SignalColor.GREEN
            self.time_in_phase = 0.0
            return

        if self.time_in_phase >= self.fixed_duration:
            next_phase = (self.current_phase + 1) % len(SignalPhase)
            self.set_phase(next_phase)

    def is_green_for(self, lane: str) -> bool:
        if self.color != SignalColor.GREEN:
            return False
        return lane in PHASE_GREEN_LANES.get(self.current_phase, [])
