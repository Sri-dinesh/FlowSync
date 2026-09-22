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
import datetime
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
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "id": simulation_id,
        "mode": mode,
        "status": "running",
        "totalSteps": 0,
        "durationMs": 0,
        "updatedAt": now_iso,
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
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        supabase_client.table("simulations").update({
            "status": status,
            "totalSteps": total_steps,
            "durationMs": duration_ms,
            "updatedAt": now_iso,
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


# ─── Scenarios ───────────────────────────────────────────────────────────────

def list_scenarios() -> List[Dict[str, Any]]:
    """Return all saved scenarios ordered by creation time (newest first)."""
    try:
        result = (
            supabase_client.table("scenarios")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return list(getattr(result, "data", []) or [])
    except Exception:
        logger.exception("list_scenarios failed")
        return []


def create_scenario(name: str, seed: int, spawn_lambda: float, duration_seconds: int,
                    is_held_out: bool = False, scenario_type: str = "standard") -> Dict[str, Any]:
    """Insert a new named scenario and return the created row."""
    try:
        result = supabase_client.table("scenarios").insert({
            "name": name,
            "seed": seed,
            "spawn_lambda": spawn_lambda,
            "duration_seconds": duration_seconds,
            "is_held_out": is_held_out,
            "scenario_type": scenario_type,
        }).execute()
        rows = getattr(result, "data", []) or []
        return rows[0] if rows else {}
    except Exception:
        logger.exception("create_scenario failed for name=%s", name)
        return {}


def delete_scenario(scenario_id: str) -> bool:
    """Delete a scenario and all its runs (cascades via FK). Returns True on success."""
    try:
        supabase_client.table("scenarios").delete().eq("id", scenario_id).execute()
        return True
    except Exception:
        logger.exception("delete_scenario failed for id=%s", scenario_id)
        return False


# ─── Scenario Runs ────────────────────────────────────────────────────────────

def list_scenario_runs(scenario_id: str) -> List[Dict[str, Any]]:
    """Return all runs for a scenario ordered by model_episode ascending."""
    try:
        result = (
            supabase_client.table("scenario_runs")
            .select("*")
            .eq("scenario_id", scenario_id)
            .order("model_episode", desc=False)
            .execute()
        )
        return list(getattr(result, "data", []) or [])
    except Exception:
        logger.exception("list_scenario_runs failed for scenario_id=%s", scenario_id)
        return []


def save_scenario_run(
    scenario_id: str,
    model_id: str,
    model_episode: int,
    controller: str,
    scenario_hash: str,
    avg_wait_time: float,
    total_passed: int,
    max_queue: int,
    override_rate: float,
    # Extended metrics
    run_group_id: str = "",
    median_delay: float = 0.0,
    p95_delay: float = 0.0,
    std_delay: float = 0.0,
    queue_area: float = 0.0,
    starvation_count: int = 0,
) -> Dict[str, Any]:
    """Insert a benchmark run result for a scenario. Returns the created row."""
    try:
        payload: Dict[str, Any] = {
            "scenario_id":    scenario_id,
            "model_id":       model_id,
            "model_episode":  model_episode,
            "controller":     controller,
            "scenario_hash":  scenario_hash,
            "avg_wait_time":  avg_wait_time,
            "total_passed":   total_passed,
            "max_queue":      max_queue,
            "override_rate":  override_rate,
            "median_delay":   median_delay,
            "p95_delay":      p95_delay,
            "std_delay":      std_delay,
            "queue_area":     queue_area,
            "starvation_count": starvation_count,
        }
        if run_group_id:
            payload["run_group_id"] = run_group_id
        result = supabase_client.table("scenario_runs").insert(payload).execute()
        rows = getattr(result, "data", []) or []
        return rows[0] if rows else {}
    except Exception:
        logger.exception(
            "save_scenario_run failed for scenario_id=%s model=%s ep=%s",
            scenario_id, model_id, model_episode,
        )
        return {}


# ─── Grouped + Aggregate reads ────────────────────────────────────────────────

def get_grouped_scenario_runs(scenario_id: str) -> List[Dict[str, Any]]:
    """
    Return runs grouped by run_group_id — each group represents one full
    execution (Fixed + Greedy + AI on the same seed).

    Returns a list of dicts:
      { run_group_id, ran_at, model_episode, fixed:{...}, greedy:{...}, ai:{...} }
    """
    try:
        result = (
            supabase_client.table("scenario_runs")
            .select("*")
            .eq("scenario_id", scenario_id)
            .order("ran_at", desc=False)
            .execute()
        )
        rows: List[Dict[str, Any]] = list(getattr(result, "data", []) or [])
    except Exception:
        logger.exception("get_grouped_scenario_runs failed for scenario_id=%s", scenario_id)
        return []

    # Group by run_group_id
    from collections import defaultdict
    groups: dict = defaultdict(lambda: {"controllers": {}, "ran_at": "", "model_episode": 0, "run_group_id": ""})
    for row in rows:
        gid = row.get("run_group_id") or row["id"]  # fallback: ungrouped row
        groups[gid]["run_group_id"]  = gid
        groups[gid]["ran_at"]        = row.get("ran_at", "")
        groups[gid]["model_episode"] = row.get("model_episode", 0)
        ctrl = row.get("controller", "ai")
        groups[gid]["controllers"][ctrl] = {
            "avg_wait_time":    row.get("avg_wait_time"),
            "total_passed":     row.get("total_passed"),
            "max_queue":        row.get("max_queue"),
            "override_rate":    row.get("override_rate"),
            "median_delay":     row.get("median_delay"),
            "p95_delay":        row.get("p95_delay"),
            "std_delay":        row.get("std_delay"),
            "queue_area":       row.get("queue_area"),
            "starvation_count": row.get("starvation_count", 0),
            "scenario_hash":    row.get("scenario_hash", ""),
        }

    # Flatten to list, sorted by model_episode
    out = []
    for gid, g in groups.items():
        entry: Dict[str, Any] = {
            "run_group_id":  g["run_group_id"],
            "ran_at":        g["ran_at"],
            "model_episode": g["model_episode"],
        }
        for ctrl in ("fixed", "greedy", "ai"):
            if ctrl in g["controllers"]:
                entry[ctrl] = g["controllers"][ctrl]
        out.append(entry)
    out.sort(key=lambda x: (x["model_episode"], x["ran_at"]))
    return out


def get_aggregate_stats() -> Dict[str, Any]:
    """
    Cross-scenario aggregate statistics.
    Returns per-controller mean/std wait + throughput, DQN win rate,
    and delta vs baselines.
    """
    try:
        runs_result = (
            supabase_client.table("scenario_runs")
            .select("controller,avg_wait_time,total_passed,starvation_count,run_group_id")
            .execute()
        )
        rows = list(getattr(runs_result, "data", []) or [])
        scenarios_result = supabase_client.table("scenarios").select("id").execute()
        total_scenarios = len(list(getattr(scenarios_result, "data", []) or []))
    except Exception:
        logger.exception("get_aggregate_stats failed")
        return {}

    if not rows:
        return {"total_scenarios": total_scenarios, "total_runs": 0}

    # Per-controller stats
    from collections import defaultdict
    ctrl_waits: dict = defaultdict(list)
    ctrl_throughput: dict = defaultdict(list)
    ctrl_starvation: dict = defaultdict(list)
    for r in rows:
        ctrl = r.get("controller", "ai")
        if r.get("avg_wait_time") is not None:
            ctrl_waits[ctrl].append(float(r["avg_wait_time"]))
        if r.get("total_passed") is not None:
            ctrl_throughput[ctrl].append(int(r["total_passed"]))
        if r.get("starvation_count") is not None:
            ctrl_starvation[ctrl].append(int(r["starvation_count"]))

    per_controller: Dict[str, Any] = {}
    for ctrl in ("fixed", "greedy", "ai"):
        waits = ctrl_waits.get(ctrl, [])
        thru  = ctrl_throughput.get(ctrl, [])
        starv = ctrl_starvation.get(ctrl, [])
        per_controller[ctrl] = {
            "mean_wait":         round(float(np.mean(waits)), 3) if waits else None,
            "std_wait":          round(float(np.std(waits)), 3) if waits else None,
            "mean_throughput":   round(float(np.mean(thru)), 1) if thru else None,
            "mean_starvation":   round(float(np.mean(starv)), 2) if starv else None,
        }

    # DQN win rate: fraction of run_groups where DQN has lowest avg_wait
    from collections import defaultdict as dd2
    group_controllers: dict = dd2(dict)
    for r in rows:
        gid = r.get("run_group_id")
        if gid and r.get("avg_wait_time") is not None:
            group_controllers[gid][r["controller"]] = float(r["avg_wait_time"])

    wins = 0
    total_groups = 0
    for gid, ctrlmap in group_controllers.items():
        if "ai" in ctrlmap and len(ctrlmap) >= 2:
            total_groups += 1
            if ctrlmap["ai"] == min(ctrlmap.values()):
                wins += 1

    dqn_win_rate = round(wins / total_groups, 3) if total_groups else 0.0

    # Delta vs baselines (positive = DQN is WORSE)
    ai_mean   = per_controller.get("ai", {}).get("mean_wait")
    gr_mean   = per_controller.get("greedy", {}).get("mean_wait")
    fx_mean   = per_controller.get("fixed", {}).get("mean_wait")

    return {
        "total_scenarios": total_scenarios,
        "total_runs":      len(rows),
        "total_groups":    total_groups,
        "per_controller":  per_controller,
        "dqn_win_rate":    dqn_win_rate,
        "dqn_vs_greedy_delta": round(ai_mean - gr_mean, 3) if (ai_mean and gr_mean) else None,
        "dqn_vs_fixed_delta":  round(ai_mean - fx_mean, 3) if (ai_mean and fx_mean) else None,
    }

