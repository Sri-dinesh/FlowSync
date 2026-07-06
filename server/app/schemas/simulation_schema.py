from typing import Dict, List

from pydantic import BaseModel

from ..simulation.intersection import Intersection


class VehicleState(BaseModel):
    id: str
    lane: str
    turn: str
    position: float
    state: str
    wait_time: float
    is_emergency: bool = False


class SimulationFrame(BaseModel):
    timestep: int
    mode: str
    signal_phase: int
    signal_color: str
    vehicles: List[VehicleState]
    queue_lengths: Dict[str, int]
    avg_wait_time: float
    throughput: int
    reward: float
    episode: int


def build_frame(
    intersection: Intersection,
    mode: str,
    reward: float,
    episode: int,
) -> SimulationFrame:
    vehicles = [
        VehicleState(
            id=vehicle.id,
            lane=vehicle.lane,
            turn=getattr(vehicle, "turn", "straight"),
            position=vehicle.position,
            state=vehicle.state,
            wait_time=vehicle.wait_time,
            is_emergency=getattr(vehicle, "is_emergency", False),
        )
        for lane in intersection.lanes.values()
        for vehicle in lane
    ]

    return SimulationFrame(
        timestep=intersection.timestep,
        mode=mode,
        signal_phase=intersection.signal.current_phase,
        signal_color=intersection.signal.color.value,
        vehicles=vehicles,
        queue_lengths=intersection.get_queue_lengths(),
        avg_wait_time=intersection.get_avg_wait_time(),
        throughput=intersection.total_passed,
        reward=reward,
        episode=episode,
    )
