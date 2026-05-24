from typing import Dict, List, Optional

from .spawner import PoissonSpawner
from .traffic_signal import TrafficSignal
from .vehicle import Vehicle


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

        for lane_name, lane_queue in self.lanes.items():
            is_green = self.signal.is_green_for(lane_name)
            for vehicle in lane_queue:
                vehicle.tick(dt, is_green)

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

    def reset(self) -> None:
        for queue in self.lanes.values():
            queue.clear()
        self.signal = TrafficSignal()
        self.timestep = 0
        self.total_passed = 0
