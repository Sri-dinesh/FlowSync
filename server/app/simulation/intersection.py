from typing import Dict, List, Optional

from .spawner import PoissonSpawner
from .traffic_signal import TrafficSignal
from .vehicle import DEFAULT_SPEED, Vehicle


class Intersection:
    def __init__(self) -> None:
        self.lanes: Dict[str, List[Vehicle]] = {
            "north": [],
            "south": [],
            "east": [],
            "west": [],
        }
        self.signal = TrafficSignal()
        self.timestep = 0
        self.total_passed = 0
        self.spawner = PoissonSpawner()

    def tick(self, dt: float, action: Optional[int] = None) -> None:
        if action is not None:
            self.signal.set_phase(action)
        else:
            self.signal.tick(dt)

        self.spawner.spawn(dt, self.lanes)

        STOP_LINE = 0.42
        MIN_DIST = 0.055

        for lane_name, lane_queue in self.lanes.items():
            is_green = self.signal.is_green_for(lane_name)
            
            for i, vehicle in enumerate(lane_queue):
                can_move = True
                
                # Check stop line collision
                if not is_green and vehicle.position <= STOP_LINE:
                    if vehicle.position + (DEFAULT_SPEED * dt) >= STOP_LINE:
                        vehicle.position = STOP_LINE
                        can_move = False

                # Check vehicle ahead collision
                if i > 0:
                    vehicle_ahead = lane_queue[i-1]
                    if vehicle_ahead.position < 1.0:
                        if vehicle.position + (DEFAULT_SPEED * dt) >= vehicle_ahead.position - MIN_DIST:
                            vehicle.position = vehicle_ahead.position - MIN_DIST
                            can_move = False

                vehicle.tick(dt, can_move)

            passed_count = sum(1 for vehicle in lane_queue if vehicle.state == "passed")
            if passed_count:
                self.total_passed += passed_count
                self.lanes[lane_name] = [
                    vehicle for vehicle in lane_queue if vehicle.state != "passed"
                ]

        self.timestep += 1

    def get_queue_lengths(self) -> Dict[str, int]:
        return {lane: len(queue) for lane, queue in self.lanes.items()}

    def get_total_waiting(self) -> int:
        return sum(len(queue) for queue in self.lanes.values())

    def get_avg_wait_time(self) -> float:
        vehicles = [vehicle for queue in self.lanes.values() for vehicle in queue]
        if not vehicles:
            return 0.0
        total_wait = sum(vehicle.wait_time for vehicle in vehicles)
        return total_wait / len(vehicles)

    def set_spawn_rate(self, lambda_rate: float) -> None:
        self.spawner.set_rate(lambda_rate)

    def reset(self) -> None:
        for queue in self.lanes.values():
            queue.clear()
        self.signal = TrafficSignal()
        self.timestep = 0
        self.total_passed = 0
