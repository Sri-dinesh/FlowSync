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
    SignalPhase.NS_GREEN.value: {"straight", "right"},
    SignalPhase.EW_GREEN.value: {"straight", "right"},
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

        self.starvation_timer: Dict[str, float] = {
            "north": 0.0,
            "south": 0.0,
            "east": 0.0,
            "west": 0.0,
        }
        self.STARVATION_THRESHOLD: float = 45.0  # seconds before starvation penalty
        self.MAX_GREEN_TIME: float = 40.0         # hard cap per phase
        self.MIN_GREEN_TIME: float = 8.0          # minimum before switching allowed

    def get_starved_directions(self) -> List[str]:
        """Returns directions that have been waiting longer than STARVATION_THRESHOLD."""
        return [
            d for d, t in self.starvation_timer.items()
            if t >= self.STARVATION_THRESHOLD
        ]

    @property
    def is_max_green_exceeded(self) -> bool:
        """True if current phase has been green longer than MAX_GREEN_TIME."""
        return (
            self.color == SignalColor.GREEN
            and self.time_in_phase >= self.MAX_GREEN_TIME
        )

    @property
    def can_switch_phase(self) -> bool:
        """Agent is only allowed to switch phase if minimum green time has passed."""
        return self.time_in_phase >= self.MIN_GREEN_TIME or self.color != SignalColor.GREEN

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

        # Update starvation timers
        green_dirs = (
            PHASE_GREEN_LANES.get(self.current_phase, [])
            if self.color == SignalColor.GREEN
            else []
        )
        
        pending_dirs = (
            PHASE_GREEN_LANES.get(self.pending_phase, [])
            if self.pending_phase is not None
            else []
        )
        
        for direction in ["north", "south", "east", "west"]:
            if direction in green_dirs or direction in pending_dirs:
                self.starvation_timer[direction] = 0.0
            else:
                self.starvation_timer[direction] += dt
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

        # Hard cap: if current phase has exceeded MAX_GREEN_TIME, force a switch
        # (applies in both fixed and AI mode — prevents starvation from operator error)
        if self.color == SignalColor.GREEN and self.time_in_phase >= self.MAX_GREEN_TIME:
            best_phase = self._pick_highest_queue_phase(self.current_phase, lanes)
            self.set_phase(best_phase)
            return

        # Normal fixed duration rollover
        if self.time_in_phase >= self.fixed_duration:
            best_phase = self._pick_highest_queue_phase(self.current_phase, lanes)
            self.set_phase(best_phase)

    def _pick_highest_queue_phase(self, current_phase: int, lanes: Optional[Dict[str, List]]) -> int:
        """
        Returns the phase (excluding current) with the highest total queue count.
        If lanes data is unavailable or all other phases are empty, falls back to
        the next sequential phase.
        """
        if lanes is None:
            return (current_phase + 1) % len(SignalPhase)

        best_phase = None
        best_count = -1

        for phase in range(len(SignalPhase)):
            if phase == current_phase:
                continue
            count = 0
            for lane_dir in PHASE_GREEN_LANES[phase]:
                for turn in ["straight", "left", "right"]:
                    count += len(lanes.get(f"{lane_dir}_{turn}", []))
            if count > best_count:
                best_count = count
                best_phase = phase

        # Fall back to sequential if all other phases are empty
        if best_phase is None or best_count == 0:
            return (current_phase + 1) % len(SignalPhase)

        return best_phase

    def is_green_for(self, lane: str, turn: Optional[str] = None) -> bool:
        """Note: right turns are handled at the intersection level, not signal level."""
        if self.color != SignalColor.GREEN:
            return False
        if lane not in PHASE_GREEN_LANES.get(self.current_phase, []):
            return False
        if turn is None:
            return True
        allowed = PHASE_ALLOWED_TURNS.get(self.current_phase, {"straight", "left", "right"})
        return turn in allowed
