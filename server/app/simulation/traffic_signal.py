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
        self.min_green_duration: float = 8.0
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

        # Fixed Timer mode (classical pre-timed clock-based controller):
        # Operates strictly by clock timer. Holds green for exactly fixed_duration,
        # then transitions sequentially: Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 0.
        # It does NOT inspect lane queues, does NOT skip empty phases, and does NOT
        # prioritize lanes with more vehicles. It is purely pre-timed.
        if self.time_in_phase >= self.fixed_duration:
            next_phase = (self.current_phase + 1) % len(SignalPhase)
            self.set_phase(next_phase)

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
