import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..schemas.metrics_schema import MetricsSnapshot
from ..services import supabase_service

router = APIRouter(prefix="/simulation", tags=["simulation"])


class ModeUpdate(BaseModel):
    mode: Literal["fixed", "ai", "manual"]


class ScenarioPayload(BaseModel):
    counts: dict[str, int]


def _build_snapshot(app) -> MetricsSnapshot:
    intersection = app.state.sim_intersection
    queue_lengths = intersection.get_queue_lengths()
    max_queue = max(queue_lengths.values(), default=0)
    trainer = app.state.trainer

    return MetricsSnapshot(
        avg_wait_time=intersection.get_avg_wait_time(),
        throughput=intersection.total_passed,
        max_queue=max_queue,
        current_phase=intersection.signal.current_phase,
        is_training=trainer.is_training if trainer else False,
        current_episode=trainer.current_episode if trainer else 0,
        epsilon=trainer.epsilon if trainer else 0.0,
    )


@router.post("/start")
async def start_simulation(request: Request) -> dict:
    app = request.app
    intersection = app.state.sim_intersection
    intersection.reset()
    intersection.spawner.set_enabled(True)

    if not app.state.sim_running:
        app.state.sim_running = True

    simulation_id = await asyncio.to_thread(
        supabase_service.create_simulation, app.state.mode
    )
    app.state.current_simulation_id = simulation_id

    return {"simulation_id": simulation_id}


@router.post("/stop")
async def stop_simulation(request: Request) -> dict:
    app = request.app
    app.state.sim_running = False
    app.state.sim_intersection.spawner.set_enabled(False)

    simulation_id = app.state.current_simulation_id
    if simulation_id:
        intersection = app.state.sim_intersection
        total_steps = intersection.timestep
        duration_ms = int(total_steps * 0.1 * 1000)
        await asyncio.to_thread(
            supabase_service.update_simulation,
            simulation_id,
            "stopped",
            total_steps,
            duration_ms,
        )

    return {"status": "stopped"}


@router.post("/reset")
async def reset_simulation(request: Request) -> dict:
    app = request.app
    app.state.sim_intersection.reset()
    app.state.sim_running = False
    app.state.sim_intersection.spawner.set_enabled(False)
    return {"status": "reset"}


@router.post("/scenario")
async def inject_scenario(payload: ScenarioPayload, request: Request) -> dict:
    from ..websockets.simulation_ws import manager
    from ..schemas.simulation_schema import build_frame

    app = request.app
    # Reset and inject exact counts
    app.state.sim_intersection.inject_scenario(payload.counts)
    app.state.sim_running = False

    # Broadcast static frame to update frontend immediately
    frame = build_frame(
        intersection=app.state.sim_intersection,
        mode=app.state.mode,
        episode=app.state.trainer.current_episode if app.state.trainer else 0,
        simulation_id=app.state.current_simulation_id,
        agent=app.state.sim_agent,
        last_reward=0.0,
        cumulative_reward=0.0,
        epsilon=0.0,
        last_action=None,
        was_exploring=False,
        obs=[],
    )
    await manager.broadcast(frame.model_dump())

    return {"status": "scenario_loaded"}


@router.put("/mode")
async def set_mode(payload: ModeUpdate, request: Request) -> dict:
    app = request.app
    app.state.mode = payload.mode
    return {"mode": payload.mode}


@router.get("/status", response_model=MetricsSnapshot)
async def get_status(request: Request) -> MetricsSnapshot:
    app = request.app
    return _build_snapshot(app)
