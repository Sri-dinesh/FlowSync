import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..schemas.metrics_schema import MetricsSnapshot
from ..services import supabase_service

router = APIRouter(prefix="/simulation", tags=["simulation"])


class ModeUpdate(BaseModel):
    mode: Literal["fixed", "ai", "manual"]


class ScenarioPayload(BaseModel):
    counts: dict[str, int]


class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    seed: int = Field(..., ge=0, le=10_000_000)
    spawn_lambda: float = Field(0.5, ge=0.1, le=3.0)
    duration_seconds: int = Field(60, ge=10, le=600)
    is_held_out: bool = Field(False)
    scenario_type: str = Field("standard")


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


class StartSimulationPayload(BaseModel):
    duration_seconds: Optional[float] = None


@router.post("/start")
async def start_simulation(request: Request, payload: Optional[StartSimulationPayload] = None) -> dict:
    app = request.app
    intersection = app.state.sim_intersection

    # Cancel any active benchmark task
    if getattr(app.state, "benchmark_task", None) is not None:
        app.state.benchmark_task.cancel()
        app.state.benchmark_task = None

    intersection.reset()
    intersection.spawner.set_enabled(True)
    try:
        intersection.spawner.seed_initial_vehicles(intersection.lanes)
    except Exception:
        pass

    app.state.run_start_step = 0
    if payload and payload.duration_seconds:
        try:
            app.state.target_duration = max(5.0, min(3600.0, float(payload.duration_seconds)))
        except (ValueError, TypeError):
            app.state.target_duration = None
    else:
        app.state.target_duration = None

    if not app.state.sim_running:
        app.state.sim_running = True

    simulation_id = await asyncio.to_thread(
        supabase_service.create_simulation, app.state.mode
    )
    app.state.current_simulation_id = simulation_id

    return {"simulation_id": simulation_id}


@router.post("/stop")
async def stop_simulation(request: Request) -> dict:
    from ..websockets.simulation_ws import manager

    app = request.app
    if getattr(app.state, "benchmark_task", None) is not None:
        app.state.benchmark_task.cancel()
        app.state.benchmark_task = None
    app.state.sim_running = False
    app.state.target_duration = None
    app.state.sim_intersection.spawner.set_enabled(False)

    simulation_id = app.state.current_simulation_id
    if simulation_id:
        intersection = app.state.sim_intersection
        total_steps = intersection.timestep
        duration_ms = int(total_steps * 0.1 * 1000)
        try:
            await asyncio.to_thread(
                supabase_service.update_simulation,
                simulation_id,
                "stopped",
                total_steps,
                duration_ms,
            )
        except Exception:
            pass

    try:
        await manager.broadcast({
            "type": "simulation_stopped",
            "simulation_id": simulation_id,
        })
    except Exception:
        pass

    return {"status": "stopped"}


@router.post("/reset")
async def reset_simulation(request: Request) -> dict:
    from ..websockets.simulation_ws import manager
    from ..schemas.simulation_schema import build_frame

    app = request.app
    if getattr(app.state, "benchmark_task", None) is not None:
        app.state.benchmark_task.cancel()
        app.state.benchmark_task = None
    app.state.sim_running = False
    app.state.target_duration = None

    app.state.sim_intersection.reset()
    for lane in app.state.sim_intersection.lanes.values():
        lane.clear()
    app.state.sim_intersection.spawner.set_enabled(False)

    try:
        empty_frame = build_frame(
            intersection=app.state.sim_intersection,
            mode=app.state.mode,
            episode=app.state.trainer.current_episode if getattr(app.state, "trainer", None) else 0,
            simulation_id=None,
            agent=getattr(app.state, "sim_agent", None),
            last_reward=0.0,
            cumulative_reward=0.0,
            epsilon=0.0,
            last_action=0,
            was_exploring=False,
            obs=None,
            target_duration=None,
        )
        await manager.broadcast(empty_frame.model_dump())
        await manager.broadcast({
            "type": "simulation_stopped",
            "reason": "reset",
            "simulation_id": None,
        })
    except Exception:
        pass

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


# ─── Scenario Builder Endpoints ───────────────────────────────────────────────

@router.get("/scenarios")
async def get_scenarios() -> list:
    """List all saved named scenarios. Automatically seeds defaults if empty."""
    scenarios = await asyncio.to_thread(supabase_service.list_scenarios)
    if not scenarios:
        scenarios = await asyncio.to_thread(supabase_service.seed_default_scenarios)
    return scenarios


@router.post("/scenarios/seed-defaults")
async def seed_defaults_endpoint() -> list:
    """Seed the default standard evaluation scenarios (Low, Moderate, High, Critical, Held-out)."""
    scenarios = await asyncio.to_thread(supabase_service.seed_default_scenarios)
    return scenarios


@router.post("/scenarios", status_code=201)
async def create_scenario_endpoint(payload: ScenarioCreate) -> dict:
    """Create a new named scenario and persist it to Supabase."""
    created = await asyncio.to_thread(
        supabase_service.create_scenario,
        payload.name,
        payload.seed,
        payload.spawn_lambda,
        payload.duration_seconds,
        payload.is_held_out,
        payload.scenario_type,
    )
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create scenario")
    return created


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario_endpoint(scenario_id: str) -> None:
    """Delete a scenario and all its historical runs."""
    ok = await asyncio.to_thread(supabase_service.delete_scenario, scenario_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete scenario")


@router.get("/scenarios/aggregate")
async def get_scenario_aggregate() -> dict:
    """Cross-scenario aggregate stats: win rate, mean/std per controller, DQN delta."""
    stats = await asyncio.to_thread(supabase_service.get_aggregate_stats)
    return stats


@router.get("/scenarios/{scenario_id}/runs")
async def get_scenario_runs(scenario_id: str) -> list:
    """Return all benchmark runs for a scenario (flat rows, sorted by model_episode)."""
    runs = await asyncio.to_thread(supabase_service.list_scenario_runs, scenario_id)
    return runs


@router.get("/scenarios/{scenario_id}/runs/grouped")
async def get_scenario_runs_grouped(scenario_id: str) -> list:
    """
    Return runs grouped by run_group_id.
    Each group = one full 3-controller execution (fixed + greedy + ai on same seed).
    """
    groups = await asyncio.to_thread(supabase_service.get_grouped_scenario_runs, scenario_id)
    return groups
