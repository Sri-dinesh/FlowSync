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

PHASE_DEMAND_MOVEMENTS: Dict[int, List[str]] = {
    0: ["north_straight", "south_straight"],
    1: ["east_straight", "west_straight"],
    2: ["north_left", "south_left"],
    3: ["east_left", "west_left"],
}


class TrafficSignal:
    def __init__(self, red_duration: float = 3.0) -> None:
        import math
        if isinstance(red_duration, bool) or not math.isfinite(red_duration) or red_duration < 0:
            raise ValueError("All-red duration must be finite and nonnegative")
        self.current_phase: int = SignalPhase.NS_GREEN.value
        self.color: SignalColor = SignalColor.GREEN
        self.time_in_phase: float = 0.0
        self.min_green_duration: float = 8.0
        self.fixed_duration: float = 8.0
        self.yellow_duration: float = 2.0
        self.red_duration: float = red_duration
        self.pending_phase: Optional[int] = None
        self._operator_request: Optional[int] = None
        self._priority_request: Optional[int] = None

        self.starvation_timer: Dict[str, float] = {
            "north": 0.0,
            "south": 0.0,
            "east": 0.0,
            "west": 0.0,
        }
        self.STARVATION_THRESHOLD: float = 45.0  # seconds before starvation penalty
        self.MAX_GREEN_TIME: float = 40.0         # hard cap per phase
        self.phase_starvation_timer: Dict[int, float] = {
            phase: 0.0 for phase in range(4)
        }

    def get_starved_directions(self) -> List[str]:
        """Returns directions that have been waiting longer than STARVATION_THRESHOLD."""
        return [
            d for d, t in self.starvation_timer.items()
            if t >= self.STARVATION_THRESHOLD
        ]

    def get_starved_phases(self) -> List[int]:
        return [
            phase for phase, elapsed in self.phase_starvation_timer.items()
            if elapsed >= self.STARVATION_THRESHOLD
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

    @property
    def MIN_GREEN_TIME(self) -> float:
        """Legacy attribute shares the actual minimum-green value."""
        return self.min_green_duration

    @MIN_GREEN_TIME.setter
    def MIN_GREEN_TIME(self, value: float) -> None:
        self.min_green_duration = value

    @staticmethod
    def _validate_phase(phase: int) -> int:
        from numbers import Integral
        if isinstance(phase, bool) or not isinstance(phase, Integral) or not 0 <= phase <= 3:
            raise ValueError("Signal phase must be an integer in [0,3]")
        return int(phase)

    def request_phase(self, phase: int, *, priority: bool = False) -> None:
        """Queue a request; tick alone changes the executed lamps.

        Priority requests precede operator requests. Neither replaces the
        pending target or shortens an active clearance interval.
        """
        phase = self._validate_phase(phase)
        if type(priority) is not bool:
            raise ValueError("Signal request priority must be boolean")
        if priority:
            self._priority_request = phase
        else:
            self._operator_request = phase

    def _begin_transition(self, phase: int) -> None:
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
        if requested_phase is not None:
            requested_phase = self._validate_phase(requested_phase)
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

        if lanes is not None:
            for phase, movements in PHASE_DEMAND_MOVEMENTS.items():
                has_demand = any(
                    any(v.state != "passed" for v in lanes.get(movement, []))
                    for movement in movements
                )
                is_served = self.color == SignalColor.GREEN and phase == self.current_phase
                if is_served or not has_demand:
                    self.phase_starvation_timer[phase] = 0.0
                else:
                    self.phase_starvation_timer[phase] += dt
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

        queued = self._priority_request if self._priority_request is not None else self._operator_request
        if queued is not None:
            if queued == self.current_phase or self.time_in_phase >= self.min_green_duration:
                if queued != self.current_phase:
                    self._begin_transition(queued)
                if self._priority_request is not None:
                    self._priority_request = None
                else:
                    self._operator_request = None
            return

        # Policy requests remain per-tick proposals, without persistent queuing.
        if requested_phase is not None:
            if (
                requested_phase != self.current_phase
                and self.time_in_phase >= self.min_green_duration
            ):
                self._begin_transition(requested_phase)
            return

        # Manual mode holds the current green phase indefinitely 
        # (until an operator request becomes physically admissible)
        if is_manual:
            return

        # Fixed Timer mode (classical pre-timed clock-based controller):
        # Operates strictly by clock timer. Holds green for exactly fixed_duration,
        # then transitions sequentially: Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 0.
        # It does NOT inspect lane queues, does NOT skip empty phases, and does NOT
        # prioritize lanes with more vehicles. It is purely pre-timed.
        if self.time_in_phase >= self.fixed_duration:
            next_phase = (self.current_phase + 1) % len(SignalPhase)
            self._begin_transition(next_phase)

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
