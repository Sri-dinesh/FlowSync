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
        # id of vehicle that currently occupies the intersection (between stop line and passed)
        self.intersection_reserved_by: Optional[str] = None

    def tick(self, dt: float, action: Optional[int] = None) -> None:
        # give the signal visibility into lane queues for smarter decisions and
        # make AI phase changes respect the same clearance timing as fixed mode
        self.signal.tick(dt, self.lanes, requested_phase=action)

        self.spawner.spawn(dt, self.lanes)

        STOP_LINE = 0.42
        MIN_DIST = 0.08

        for lane_name, lane_queue in self.lanes.items():
            # consult signal including vehicle turn intent
            # will allow/prohibit left turns depending on phase
            # Determine per-vehicle during loop below
            
            for i, vehicle in enumerate(lane_queue):
                can_move = True
                
                # Check stop line collision and signal permission
                is_green_for_movement = self.signal.is_green_for(lane_name, getattr(vehicle, "turn", None))
                # If signal disallows movement and vehicle is approaching stop line, stop at stop line
                if not is_green_for_movement and vehicle.position <= STOP_LINE:
                    if vehicle.position + (DEFAULT_SPEED * dt) >= STOP_LINE:
                        vehicle.position = STOP_LINE
                        can_move = False

                # If signal allows and vehicle would enter intersection, ensure reservation is free
                if is_green_for_movement and vehicle.position < STOP_LINE:
                    entering = vehicle.position + (DEFAULT_SPEED * dt) >= STOP_LINE
                    if entering:
                        # If intersection reserved by someone else, block entering
                        if self.intersection_reserved_by is None or self.intersection_reserved_by == vehicle.id:
                            # reserve intersection for this vehicle
                            self.intersection_reserved_by = vehicle.id
                        else:
                            # block at stop line
                            vehicle.position = STOP_LINE
                            can_move = False

                # Check vehicle ahead collision
                if i > 0:
                    vehicle_ahead = lane_queue[i - 1]
                    if vehicle_ahead.position < 1.0:
                        max_position = max(0.0, vehicle_ahead.position - MIN_DIST)
                        if vehicle.position + (DEFAULT_SPEED * dt) >= max_position:
                            vehicle.position = max_position
                            can_move = False
                # If this vehicle is marked passed after tick, release reservation
                # (release after tick below when vehicle.position >= 1.0 / state == 'passed')
                vehicle.tick(dt, can_move)

                # Release reservation when the reserved vehicle has left the intersection
                if self.intersection_reserved_by and vehicle.id == self.intersection_reserved_by and vehicle.state == "passed":
                    self.intersection_reserved_by = None

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
        self.intersection_reserved_by = None
