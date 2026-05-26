from dataclasses import dataclass


DEFAULT_SPEED = 0.12


@dataclass
class Vehicle:
    id: str
    lane: str
    position: float
    wait_time: float
    speed: float
    state: str

    def tick(self, dt: float, is_green: bool) -> None:
        if is_green and self.position < 1.0:
            self.speed = DEFAULT_SPEED
            self.position += self.speed * dt
            self.state = "moving"
        if not is_green:
            self.speed = 0.0
            self.state = "waiting"
            self.wait_time += dt
        if self.position >= 1.0:
            self.state = "passed"
