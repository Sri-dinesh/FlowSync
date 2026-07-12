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

# Which turns are allowed during each phase
PHASE_ALLOWED_TURNS: Dict[int, set] = {
    SignalPhase.NS_GREEN.value: {"straight", "left", "right"},
    SignalPhase.EW_GREEN.value: {"straight", "left", "right"},
    SignalPhase.NS_LEFT.value: {"left"},
    SignalPhase.EW_LEFT.value: {"left"},
}


class TrafficSignal:
    def __init__(self, red_duration: float = 3.0) -> None:
        self.current_phase: int = SignalPhase.NS_GREEN.value
        self.color: SignalColor = SignalColor.GREEN
        self.time_in_phase: float = 0.0
        self.min_green_duration: float = 4.0
        self.fixed_duration: float = 8.0
        self.yellow_duration: float = 2.0
        self.red_duration: float = red_duration
        self.pending_phase: Optional[int] = None

    def set_phase(self, phase: int) -> None:
        if phase == self.current_phase and self.color == SignalColor.GREEN:
            return
        self.pending_phase = phase
        self.color = SignalColor.YELLOW
        self.time_in_phase = 0.0

    def tick(
        self,
        dt: float,
        lanes: Optional[Dict[str, List]] = None,
        requested_phase: Optional[int] = None,
        is_manual: bool = False,
    ) -> None:
        # lanes: mapping lane name -> list of vehicles (for dynamic phase decisions)
        self.time_in_phase += dt

        # Yellow handling
        if self.color == SignalColor.YELLOW:
            if self.time_in_phase >= self.yellow_duration:
                self.color = SignalColor.RED
                self.time_in_phase = 0.0
            return

        # Red -> resolve pending phase after red_duration
        if self.color == SignalColor.RED:
            if self.time_in_phase >= self.red_duration:
                if self.pending_phase is not None:
                    self.current_phase = self.pending_phase
                    self.pending_phase = None
                self.color = SignalColor.GREEN
                self.time_in_phase = 0.0
            return

        # In AI mode, phase requests still respect minimum green + yellow clearance.
        if requested_phase is not None:
            if (
                requested_phase != self.current_phase
                and self.time_in_phase >= self.min_green_duration
            ):
                self.set_phase(requested_phase)
            return

        # Manual mode holds the current green phase indefinitely 
        # (until manual_override explicitly sets a new phase)
        if is_manual:
            return

        # When green: allow a minimum green time and then pick next phase
        if lanes is not None:
            # compute waiting counts per phase
            phase_wait = {}
            for phase, lane_list in PHASE_GREEN_LANES.items():
                count = 0
                for ln in lane_list:
                    for turn in ["straight", "left", "right"]:
                        count += len(lanes.get(f"{ln}_{turn}", []))
                phase_wait[phase] = count

            # If current phase has no waiting vehicles and another phase does, switch early
            if self.time_in_phase >= self.min_green_duration:
                current_wait = phase_wait.get(self.current_phase, 0)
                max_phase = max(phase_wait.items(), key=lambda kv: kv[1])[0]
                if current_wait == 0 and phase_wait.get(max_phase, 0) > 0:
                    self.set_phase(max_phase)
                    return

        # Normal fixed duration rollover
        if self.time_in_phase >= self.fixed_duration:
            # Find the next phase in sequence that has vehicles waiting, or default to next sequential
            if lanes is not None:
                for offset in range(1, len(SignalPhase) + 1):
                    candidate_phase = (self.current_phase + offset) % len(SignalPhase)
                    candidate_lanes = PHASE_GREEN_LANES[candidate_phase]
                    has_vehicles = False
                    for ln in candidate_lanes:
                        for turn in ["straight", "left", "right"]:
                            if len(lanes.get(f"{ln}_{turn}", [])) > 0:
                                has_vehicles = True
                                break
                        if has_vehicles:
                            break
                    if has_vehicles:
                        self.set_phase(candidate_phase)
                        return

            next_phase = (self.current_phase + 1) % len(SignalPhase)
            self.set_phase(next_phase)

    def is_green_for(self, lane: str, turn: Optional[str] = None) -> bool:
        if self.color != SignalColor.GREEN:
            return False
        if lane not in PHASE_GREEN_LANES.get(self.current_phase, []):
            return False
        if turn is None:
            return True
        allowed = PHASE_ALLOWED_TURNS.get(self.current_phase, {"straight", "left", "right"})
        return turn in allowed
