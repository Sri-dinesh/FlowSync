from typing import Any, Dict, Optional

from supabase import Client, create_client

from ..config import settings

supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
)


def create_simulation(mode: str) -> str:
    payload = {
        "mode": mode,
        "status": "running",
        "totalSteps": 0,
        "durationMs": 0,
    }
    result = supabase_client.table("simulations").insert(payload).execute()
    data = getattr(result, "data", [])
    return data[0]["id"] if data else ""


def update_simulation(
    simulation_id: str,
    status: str,
    total_steps: int,
    duration_ms: int,
) -> None:
    payload = {
        "status": status,
        "totalSteps": total_steps,
        "durationMs": duration_ms,
    }
    supabase_client.table("simulations").update(payload).eq("id", simulation_id).execute()


def save_episode(
    simulation_id: str,
    episode_num: int,
    total_reward: float,
    avg_wait: float,
    throughput: int,
    epsilon: float,
    loss: Optional[float],
    steps: int,
) -> None:
    payload = {
        "simulationId": simulation_id,
        "episodeNumber": episode_num,
        "totalReward": total_reward,
        "avgWaitTime": avg_wait,
        "throughput": throughput,
        "epsilon": epsilon,
        "loss": loss,
        "steps": steps,
    }
    supabase_client.table("episodes").insert(payload).execute()


def save_traffic_log(
    simulation_id: str,
    timestep: int,
    spawned: int,
    passed: int,
    avg_wait: float,
    max_queue: int,
) -> None:
    payload = {
        "simulationId": simulation_id,
        "timestep": timestep,
        "vehiclesSpawned": spawned,
        "vehiclesPassed": passed,
        "avgWaitTime": avg_wait,
        "maxQueueLength": max_queue,
    }
    supabase_client.table("traffic_logs").insert(payload).execute()


def save_signal_state(
    simulation_id: str,
    timestep: int,
    phase: int,
    duration: int,
    queues: Dict[str, int],
) -> None:
    payload = {
        "simulationId": simulation_id,
        "timestep": timestep,
        "phase": phase,
        "duration": duration,
        "queueNorth": queues.get("north", 0),
        "queueSouth": queues.get("south", 0),
        "queueEast": queues.get("east", 0),
        "queueWest": queues.get("west", 0),
    }
    supabase_client.table("signal_states").insert(payload).execute()


def save_performance_metric(
    simulation_id: str,
    mode: str,
    avg_wait: float,
    throughput: int,
) -> None:
    is_fixed = mode == "fixed"
    payload: Dict[str, Any] = {
        "simulationId": simulation_id,
        "mode": mode,
        "avgWaitTimeFixed": avg_wait if is_fixed else None,
        "avgWaitTimeAI": avg_wait if not is_fixed else None,
        "throughputFixed": throughput if is_fixed else None,
        "throughputAI": throughput if not is_fixed else None,
    }
    supabase_client.table("performance_metrics").insert(payload).execute()


def save_model_metadata(
    name: str,
    version: str,
    storage_path: str,
    avg_reward: float,
    epsilon: float,
    total_episodes: int,
    model_id: Optional[str] = None,
) -> str:
    payload: Dict[str, Any] = {
        "name": name,
        "version": version,
        "storagePath": storage_path,
        "avgReward": avg_reward,
        "epsilon": epsilon,
        "totalEpisodes": total_episodes,
    }
    if model_id:
        payload["id"] = model_id
    result = supabase_client.table("rl_models").insert(payload).execute()
    data = getattr(result, "data", [])
    return data[0]["id"] if data else ""


def set_active_model(model_id: str) -> None:
    supabase_client.table("rl_models").update({"isActive": False}).execute()
    supabase_client.table("rl_models").update({"isActive": True}).eq("id", model_id).execute()
