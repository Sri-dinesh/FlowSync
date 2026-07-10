from typing import Dict, List, Optional

from .spawner import PoissonSpawner
from .traffic_signal import TrafficSignal
from .vehicle import DEFAULT_SPEED, Vehicle


class Intersection:
    def __init__(self) -> None:
        self.lanes: Dict[str, List[Vehicle]] = {
            f"{dir}_{turn}": []
            for dir in ["north", "south", "east", "west"]
            for turn in ["straight", "left", "right"]
        }
        self.signal = TrafficSignal()
        self.timestep = 0
        self.total_passed = 0
        self.spawner = PoissonSpawner()
        # Set of vehicle IDs currently in the intersection
        self.vehicles_in_intersection = set()
        # The phase during which the intersection was locked
        self.intersection_reserved_phase: Optional[int] = None
        # Track active emergency override lane
        self.emergency_override_lane: Optional[str] = None
        self._spawned_this_interval = 0
        self._passed_this_interval = 0

    def trigger_emergency_override(self, lane: str) -> None:
        if lane not in ["north", "south", "east", "west"]:
            return
        # Prevent double spawning of emergency vehicles in the same direction
        if any(getattr(v, "is_emergency", False) for turn in ["straight", "left", "right"] for v in self.lanes.get(f"{lane}_{turn}", [])):
            return
            
        from uuid import uuid4
        emergency_vehicle = Vehicle(
            id=f"emergency-{uuid4().hex[:6]}",
            lane=lane,
            turn="straight",
            position=0.0,
            wait_time=0.0,
            speed=DEFAULT_SPEED,
            state="waiting",
            is_emergency=True,
        )
        self.lanes[f"{lane}_straight"].append(emergency_vehicle)
        self.emergency_override_lane = lane
        self._spawned_this_interval += 1

    def tick(self, dt: float, action: Optional[int] = None) -> None:
        # Resolve active emergency override: force signal phase
        if self.emergency_override_lane:
            has_active_emergency = any(
                getattr(v, "is_emergency", False)
                for queue in self.lanes.values()
                for v in queue
            )
            if has_active_emergency:
                # Force priority signal phase immediately (0 for North/South, 1 for East/West)
                priority_phase = 0 if self.emergency_override_lane in ("north", "south") else 1
                from .traffic_signal import SignalColor
                self.signal.current_phase = priority_phase
                self.signal.color = SignalColor.GREEN
                self.signal.time_in_phase = 0.0
                self.signal._pending_phase = None
                # Bypass normal action selection
                action = None
            else:
                self.emergency_override_lane = None

        # give the signal visibility into lane queues for smarter decisions and
        # make AI phase changes respect the same clearance timing as fixed mode
        self.signal.tick(dt, self.lanes, requested_phase=action)

        spawned_vehicles = self.spawner.spawn(dt, self.lanes)
        self._spawned_this_interval += len(spawned_vehicles)

        STOP_LINE = 0.42
        MIN_DIST = 0.08

        for lane_id, lane_queue in self.lanes.items():
            dir_name = lane_id.split("_")[0]
            
            for i, vehicle in enumerate(lane_queue):
                can_move = True
                
                # Check stop line collision and signal permission
                is_green_for_movement = self.signal.is_green_for(dir_name, getattr(vehicle, "turn", None))
                
                # Yield-on-left check:
                # If vehicle is at or before the stop line, wants to turn left, and the signal is a parallel green (0 or 1),
                # it must yield to oncoming straight traffic.
                if vehicle.position <= STOP_LINE and getattr(vehicle, "turn", None) == "left" and self.signal.current_phase in (0, 1):
                    oncoming_dir = {"north": "south", "south": "north", "east": "west", "west": "east"}[dir_name]
                    for oncoming_turn in ["straight", "right"]:
                        oncoming_queue = self.lanes.get(f"{oncoming_dir}_{oncoming_turn}", [])
                        for oncoming_veh in oncoming_queue:
                            if 0.15 <= oncoming_veh.position < 1.0:
                                is_green_for_movement = False
                                break
                        if not is_green_for_movement:
                            break

                # If vehicle is behind or at the stop line, process signal/intersection entrance
                if vehicle.position <= STOP_LINE:
                    if not is_green_for_movement:
                        # If light is red, vehicle stops at the stop line
                        if vehicle.position + (DEFAULT_SPEED * dt) >= STOP_LINE:
                            vehicle.position = STOP_LINE
                            can_move = False
                    else:
                        # Light is green, check if entering the intersection
                        entering = vehicle.position + (DEFAULT_SPEED * dt) >= STOP_LINE
                        if entering:
                            # Allow entering if intersection is empty or reserved by the same direction group
                            current_group = 0 if self.signal.current_phase in (0, 2) else 1
                            reserved_group = 0 if self.intersection_reserved_phase in (0, 2) else 1 if self.intersection_reserved_phase is not None else None
                            
                            if (self.intersection_reserved_phase is None or current_group == reserved_group):
                                self.vehicles_in_intersection.add(vehicle.id)
                                self.intersection_reserved_phase = self.signal.current_phase
                            else:
                                # Perpendicular traffic is still clearing the intersection
                                vehicle.position = STOP_LINE
                                can_move = False

                # Check vehicle ahead collision
                if i > 0:
                    vehicle_ahead = lane_queue[i - 1]
                    if vehicle_ahead.position < 1.0:
                        max_position = max(0.0, vehicle_ahead.position - MIN_DIST)
                        if vehicle.position + (DEFAULT_SPEED * dt) >= max_position:
                            vehicle.position = max_position
                            # Can only move if vehicle ahead is moving (keeps queue flowing smoothly)
                            can_move = can_move and (vehicle_ahead.speed > 0)

                vehicle.tick(dt, can_move)

                # Release the phase lock when the last vehicle exits
                if vehicle.state == "passed" and vehicle.id in self.vehicles_in_intersection:
                    self.vehicles_in_intersection.remove(vehicle.id)
                    if not self.vehicles_in_intersection:
                        self.intersection_reserved_phase = None

            passed_count = sum(1 for vehicle in lane_queue if vehicle.state == "passed")
            if passed_count:
                self.total_passed += passed_count
                self._passed_this_interval += passed_count
                self.lanes[lane_id] = [
                    vehicle for vehicle in lane_queue if vehicle.state != "passed"
                ]

        self.timestep += 1

    def get_queue_lengths(self) -> Dict[str, int]:
        agg = {"north": 0, "south": 0, "east": 0, "west": 0}
        for lane_id, queue in self.lanes.items():
            dir_name = lane_id.split("_")[0]
            if dir_name in agg:
                agg[dir_name] += sum(1 for v in queue if v.state == "waiting")
        return agg

    def get_total_waiting(self) -> int:
        return sum(len(queue) for queue in self.lanes.values())

    def get_total_wait_time(self) -> float:
        return sum(vehicle.wait_time for queue in self.lanes.values() for vehicle in queue)

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
        self.vehicles_in_intersection.clear()
        self.intersection_reserved_phase = None
        self.emergency_override_lane = None
        self._spawned_this_interval = 0
        self._passed_this_interval = 0
