import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..schemas.metrics_schema import MetricsSnapshot
from ..services import supabase_service

router = APIRouter(prefix="/simulation", tags=["simulation"])


class ModeUpdate(BaseModel):
    mode: Literal["fixed", "ai"]


def _build_snapshot(app_state: dict) -> MetricsSnapshot:
    intersection = app_state["intersection"]
    queue_lengths = intersection.get_queue_lengths()
    max_queue = max(queue_lengths.values(), default=0)
    trainer = app_state.get("trainer")

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
    app_state = request.app.state.app_state
    intersection = app_state["intersection"]
    intersection.reset()

    if not app_state.get("sim_running"):
        app_state["sim_running"] = True

    simulation_id = await asyncio.to_thread(
        supabase_service.create_simulation, app_state["mode"]
    )
    app_state["current_simulation_id"] = simulation_id

    return {"simulation_id": simulation_id}


@router.post("/stop")
async def stop_simulation(request: Request) -> dict:
    app_state = request.app.state.app_state
    app_state["sim_running"] = False

    simulation_id = app_state.get("current_simulation_id")
    if simulation_id:
        intersection = app_state["intersection"]
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
    app_state = request.app.state.app_state
    app_state["intersection"].reset()
    app_state["sim_running"] = False
    return {"status": "reset"}


@router.put("/mode")
async def set_mode(payload: ModeUpdate, request: Request) -> dict:
    app_state = request.app.state.app_state
    app_state["mode"] = payload.mode
    return {"mode": payload.mode}


@router.get("/status", response_model=MetricsSnapshot)
async def get_status(request: Request) -> MetricsSnapshot:
    app_state = request.app.state.app_state
    return _build_snapshot(app_state)
