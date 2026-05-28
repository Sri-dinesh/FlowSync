from dataclasses import dataclass


DEFAULT_SPEED = 0.12


@dataclass
class Vehicle:
    id: str
    lane: str
    turn: str
    position: float
    wait_time: float
    speed: float
    state: str

    def tick(self, dt: float, can_move: bool) -> None:
        if can_move and self.position < 1.0:
            self.speed = DEFAULT_SPEED
            self.position += self.speed * dt
            self.state = "moving"
        else:
            self.speed = 0.0
            self.state = "waiting"
            self.wait_time += dt
            
        if self.position >= 1.0:
            self.state = "passed"
