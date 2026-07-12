"""
Supabase database service — all writes go through this module.

Write strategy:
  - All functions are synchronous (called via asyncio.to_thread from async context).
  - Bulk inserts use a single .insert([...]) call to reduce round-trips.
  - Logging is attached to every failure so nothing silently disappears.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from supabase import Client, create_client

from ..config import settings

logger = logging.getLogger(__name__)

supabase_client: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,
)


# ─── Simulations ─────────────────────────────────────────────────────────────

def create_simulation(mode: str) -> str:
    simulation_id = str(uuid4())
    payload = {
        "id": simulation_id,
        "mode": mode,
        "status": "running",
        "totalSteps": 0,
        "durationMs": 0,
    }
    try:
        result = supabase_client.table("simulations").insert(payload).execute()
        data = getattr(result, "data", [])
        return data[0]["id"] if data else simulation_id
    except Exception:
        logger.exception("create_simulation failed for mode=%s", mode)
        return simulation_id


def update_simulation(
    simulation_id: str,
    status: str,
    total_steps: int,
    duration_ms: int,
) -> None:
    try:
        supabase_client.table("simulations").update({
            "status": status,
            "totalSteps": total_steps,
            "durationMs": duration_ms,
        }).eq("id", simulation_id).execute()
    except Exception:
        logger.exception("update_simulation failed for id=%s", simulation_id)


# ─── Episodes ────────────────────────────────────────────────────────────────

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
    try:
        supabase_client.table("episodes").insert({
            "id": str(uuid4()),
            "simulationId": simulation_id,
            "episodeNumber": episode_num,
            "totalReward": total_reward,
            "avgWaitTime": avg_wait,
            "throughput": throughput,
            "epsilon": epsilon,
            "loss": loss,
            "steps": steps,
        }).execute()
    except Exception:
        logger.exception(
            "save_episode failed for simulation=%s episode=%d", simulation_id, episode_num
        )


# ─── Traffic logs (sampled) ───────────────────────────────────────────────────

def save_traffic_logs_bulk(rows: List[Dict[str, Any]]) -> None:
    """
    Insert multiple traffic log rows in one round-trip.
    Each row must have: simulationId, timestep, vehiclesSpawned,
    vehiclesPassed, avgWaitTime, maxQueueLength.
    """
    if not rows:
        return
    payloads = [{"id": str(uuid4()), **row} for row in rows]
    try:
        supabase_client.table("traffic_logs").insert(payloads).execute()
    except Exception:
        logger.exception("save_traffic_logs_bulk failed (%d rows)", len(rows))


def save_traffic_log(
    simulation_id: str,
    timestep: int,
    spawned: int,
    passed: int,
    avg_wait: float,
    max_queue: int,
) -> None:
    save_traffic_logs_bulk([{
        "simulationId": simulation_id,
        "timestep": timestep,
        "vehiclesSpawned": spawned,
        "vehiclesPassed": passed,
        "avgWaitTime": avg_wait,
        "maxQueueLength": max_queue,
    }])


# ─── Signal states (sampled) ──────────────────────────────────────────────────

def save_signal_states_bulk(rows: List[Dict[str, Any]]) -> None:
    """
    Insert multiple signal state rows in one round-trip.
    Each row must have: simulationId, timestep, phase, duration,
    queueNorth, queueSouth, queueEast, queueWest.
    """
    if not rows:
        return
    payloads = [{"id": str(uuid4()), **row} for row in rows]
    try:
        supabase_client.table("signal_states").insert(payloads).execute()
    except Exception:
        logger.exception("save_signal_states_bulk failed (%d rows)", len(rows))


def save_signal_state(
    simulation_id: str,
    timestep: int,
    phase: int,
    duration: int,
    queues: Dict[str, int],
) -> None:
    save_signal_states_bulk([{
        "simulationId": simulation_id,
        "timestep": timestep,
        "phase": phase,
        "duration": duration,
        "queueNorth": queues.get("north", 0),
        "queueSouth": queues.get("south", 0),
        "queueEast": queues.get("east", 0),
        "queueWest": queues.get("west", 0),
    }])


# ─── Performance metrics ──────────────────────────────────────────────────────

def save_performance_metric(
    simulation_id: str,
    mode: str,
    avg_wait: float,
    throughput: int,
    max_queue: int = 0,
    total_steps: int = 0,
) -> None:
    try:
        supabase_client.table("performance_metrics").insert({
            "id": str(uuid4()),
            "simulationId": simulation_id,
            "mode": mode,
            "avgWaitTime": avg_wait,
            "throughput": throughput,
            "maxQueueLength": max_queue,
            "totalSteps": total_steps,
        }).execute()
    except Exception:
        logger.exception(
            "save_performance_metric failed for simulation=%s mode=%s", simulation_id, mode
        )


# ─── RL model metadata ────────────────────────────────────────────────────────

import datetime

def _get_rating(avg_reward: float) -> str:
    if avg_reward > 10.0:
        return "Excellent"
    elif avg_reward > 0.0:
        return "Efficient"
    elif avg_reward > -10.0:
        return "Fair"
    elif avg_reward > -30.0:
        return "Poor"
    else:
        return "Failing"

def save_model_metadata(
    simulation_id: str,
    episode: int,
    avg_reward: float,
    epsilon: float,
    total_episodes: int,
) -> str:
    """
    Upsert a row in rl_models keyed on simulation_id.
    Updates the existing row if it already exists (checkpoint at episode 50, 100, …)
    so we don't accumulate duplicate rows per training run.
    """
    model_id = simulation_id  # reuse simulation UUID as model identifier
    storage_path = f"models/{simulation_id}/checkpoint_{episode}.pt"
    version = str(episode)
    rating = _get_rating(avg_reward)

    try:
        # Check if a row already exists for this simulation
        existing = (
            supabase_client.table("rl_models")
            .select("id, name")
            .eq("id", model_id)
            .execute()
        )
        if getattr(existing, "data", []):
            old_name = existing.data[0].get("name", "")
            # Preserve the date-time part if it exists
            if old_name.startswith("Model 20"):
                date_part = old_name.split(" - ")[0]
            else:
                date_part = f"Model {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            new_name = f"{date_part} - {episode}eps - {rating}"

            # Update in place
            supabase_client.table("rl_models").update({
                "name": new_name,
                "version": version,
                "storagePath": storage_path,
                "avgReward": avg_reward,
                "epsilon": epsilon,
                "totalEpisodes": total_episodes,
            }).eq("id", model_id).execute()
        else:
            date_part = f"Model {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            new_name = f"{date_part} - {episode}eps - {rating}"
            
            supabase_client.table("rl_models").insert({
                "id": model_id,
                "name": new_name,
                "version": version,
                "storagePath": storage_path,
                "avgReward": avg_reward,
                "epsilon": epsilon,
                "totalEpisodes": total_episodes,
                "isActive": False,
            }).execute()
        return model_id
    except Exception:
        logger.exception("save_model_metadata failed for simulation=%s", simulation_id)
        return model_id


def set_active_model(model_id: str) -> None:
    try:
        # Clear all active flags first, then set the target
        supabase_client.table("rl_models").update({"isActive": False}).neq("id", "").execute()
        supabase_client.table("rl_models").update({"isActive": True}).eq("id", model_id).execute()
    except Exception:
        logger.exception("set_active_model failed for id=%s", model_id)
