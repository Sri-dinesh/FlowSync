"""
Simulation WebSocket handler.

Persistence strategy for traffic_logs and signal_states:
  - Sampled every LOG_SAMPLE_INTERVAL ticks (default 50 = every 5 s at 10 Hz)
    to avoid flooding the DB at 10 rows/second.
  - Rows are flushed in bulk every FLUSH_INTERVAL ticks to reduce round-trips.
  - Neither table is written on every tick — that would produce ~36 000 rows/hour.
"""

import asyncio
import datetime
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
try:
    import ujson as json
except ImportError:
    import json

from fastapi import WebSocket, WebSocketDisconnect

from ..realworld.models.config import SESSION_DIR
from ..schemas.simulation_schema import build_frame
from ..services import supabase_service
from ..simulation.demand_forecast import ArrivalForecaster
from ..simulation.traffic_math import MAX_CAP, compute_movement_pressures

logger = logging.getLogger(__name__)

# Sample one row every N simulation ticks (1 tick = 0.1 s → 50 ticks = 5 s)
LOG_SAMPLE_INTERVAL = 50
# Flush buffered rows to DB every N samples (50 samples × 5 s = ~4 min between flushes)
# Keep low so data isn't lost if the server restarts: flush every 10 samples = ~50 s
FLUSH_EVERY_N_SAMPLES = 10


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict) -> None:
        payload = json.dumps(data)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


# ─── Per-simulation buffer for bulk writes ────────────────────────────────────

class _SimBuffer:
    """Accumulates sampled rows and flushes them in bulk."""

    def __init__(self) -> None:
        self.traffic_rows: List[Dict[str, Any]] = []
        self.signal_rows: List[Dict[str, Any]] = []
        self.sample_count = 0

    def add(
        self,
        simulation_id: str,
        timestep: int,
        intersection: Any,
    ) -> bool:
        """Returns True when the buffer should be flushed."""
        queues = intersection.get_queue_lengths()
        signal = intersection.signal

        self.traffic_rows.append({
            "simulationId": simulation_id,
            "timestep": timestep,
            "vehiclesSpawned": getattr(intersection, "_spawned_this_interval", 0),
            "vehiclesPassed": getattr(intersection, "_passed_this_interval", 0),
            "avgWaitTime": intersection.get_avg_wait_time(),
            "maxQueueLength": max(queues.values(), default=0),
        })
        self.signal_rows.append({
            "simulationId": simulation_id,
            "timestep": timestep,
            "phase": signal.current_phase,
            "duration": int(signal.time_in_phase),
            "queueNorth": queues.get("north", 0),
            "queueSouth": queues.get("south", 0),
            "queueEast": queues.get("east", 0),
            "queueWest": queues.get("west", 0),
        })
        intersection._spawned_this_interval = 0
        intersection._passed_this_interval = 0
        self.sample_count += 1
        return self.sample_count % FLUSH_EVERY_N_SAMPLES == 0

    def flush(self) -> tuple[List[Dict], List[Dict]]:
        traffic, signal = self.traffic_rows[:], self.signal_rows[:]
        self.traffic_rows.clear()
        self.signal_rows.clear()
        return traffic, signal


_buffer = _SimBuffer()


async def _flush_buffer() -> None:
    traffic_rows, signal_rows = _buffer.flush()
    if traffic_rows:
        await asyncio.to_thread(supabase_service.save_traffic_logs_bulk, traffic_rows)
    if signal_rows:
        await asyncio.to_thread(supabase_service.save_signal_states_bulk, signal_rows)


# ─── Observation & AI Action Helpers ─────────────────────────────────────────

def _build_obs_from_intersection(intersection, forecaster: Optional[ArrivalForecaster] = None) -> np.ndarray:
    movement_queues = intersection.get_movement_queues()
    signal = intersection.signal
    # S-03b: Smooth tanh queue normalization to match environment.py exactly
    movements = [
        float(np.tanh(movement_queues.get(k, 0) / 15.0))
        for k in [
            "north_straight", "north_left", "north_right",
            "south_straight", "south_left", "south_right",
            "east_straight",  "east_left",  "east_right",
            "west_straight",  "west_left",  "west_right",
        ]
    ]

    phase_onehot = [0.0, 0.0, 0.0, 0.0]
    phase_onehot[signal.current_phase] = 1.0

    time_norm = min(signal.time_in_phase / signal.MAX_GREEN_TIME, 1.0)
    is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0

    # Compute pressure identically to TrafficEnv._get_obs() — must match training exactly
    dest_map = {
        "north_straight": "south", "north_left": "east",   "north_right": "west",
        "south_straight": "north", "south_left": "west",   "south_right": "east",
        "east_straight":  "west",  "east_left":  "south",  "east_right":  "north",
        "west_straight":  "east",  "west_left":  "north",  "west_right":  "south",
    }
    outgoing = intersection.get_outgoing_counts()
    total_pressure = 0.0
    for movement, dest in dest_map.items():
        incoming = movement_queues.get(movement, 0) / MAX_CAP
        out = outgoing.get(dest, 0) / MAX_CAP
        total_pressure += max(0.0, incoming - out)
    pressure_norm = min(total_pressure / 20.0, 1.0)

    max_starv_norm = min(
        max(signal.starvation_timer.values()) / signal.STARVATION_THRESHOLD, 1.0
    )

    if forecaster is not None:
        forecast_features = forecaster.get_forecast_features().tolist()
    else:
        forecast_features = [0.0] * 8

    obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm] + forecast_features
    return np.array(obs, dtype=np.float32)


def _select_ai_phase_action(
    signal,
    intersection,
    agent,
    obs: np.ndarray,
    phase_starvation: Dict[int, float],
    dt: float = 0.1,
) -> tuple[int, bool]:
    """
    Selects AI signal phase action with:
      1. Dynamic 4-Phase Demand Calculation (0: NS_THRU, 1: EW_THRU, 2: NS_LEFT, 3: EW_LEFT).
      2. Starvation Watchdog: tracks wait time per phase; if any phase with waiting vehicles
         has been starved >= 25s, it is guaranteed service (prevents left-turn lockup).
      3. Max-Green Ceiling: forces switch if current phase exceeds MAX_GREEN_TIME.
      4. DQN Q-Value Policy with Demand Action Masking over all valid phases.
    Returns: (action, was_watchdog_override)
    """
    PHASE_DIRS  = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
    PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}

    queues = intersection.get_movement_queues()
    phase_demands = {
        ph: sum(queues.get(f"{d}_{t}", 0) for d in PHASE_DIRS[ph] for t in PHASE_TURNS[ph])
        for ph in range(4)
    }

    # Update starvation timers per phase
    for ph in range(4):
        if ph == signal.current_phase and signal.color.name == "GREEN":
            phase_starvation[ph] = 0.0
        elif phase_demands[ph] > 0:
            phase_starvation[ph] = phase_starvation.get(ph, 0.0) + dt
        else:
            phase_starvation[ph] = 0.0

    if not (signal.can_switch_phase and signal.color.name == "GREEN"):
        return signal.current_phase, False

    # 1. Starvation Watchdog Guard: any phase with queued vehicles starved >= 12.0s
    starved_phases = [ph for ph, t in phase_starvation.items() if t >= 12.0 and phase_demands[ph] > 0]
    if starved_phases:
        action = max(starved_phases, key=lambda p: phase_starvation[p])
        return action, True

    # 2. Max Green Ceiling: prevent lingering on green when other directions are queued
    other_phase_counts = {
        ph: phase_demands[ph] for ph in range(4) if ph != signal.current_phase
    }
    if (signal.is_max_green_exceeded or signal.time_in_phase >= 18.0) and any(other_phase_counts.values()):
        action = max(other_phase_counts, key=lambda p: other_phase_counts[p])
        return action, True

    # 3. DQN Policy with Demand Action Masking
    valid_phases = [p for p, d in phase_demands.items() if d > 0]
    if valid_phases:
        if agent is not None:
            try:
                q_values = agent.get_q_values(obs)
                action = max(valid_phases, key=lambda p: q_values[p])
            except Exception:
                action = max(valid_phases, key=lambda p: phase_demands[p])
        else:
            action = max(valid_phases, key=lambda p: phase_demands[p])
        return action, False

    # Fallback when all queues are 0: let agent explore/choose or hold phase
    if agent is not None:
        try:
            action = agent.select_action(obs, epsilon=0.0)
            return action, False
        except Exception:
            pass
    return signal.current_phase, False


# ─── Model Checkpoint Loader Helper ──────────────────────────────────────────

def _parse_checkpoint_ep(path: str) -> int | None:
    import re
    match = re.search(r"checkpoint_(\d+)\.pt$", path)
    return int(match.group(1)) if match else None


def _detect_finetune_info(model_identifier: str | None) -> tuple[bool, str | None]:
    """Detect whether a model checkpoint is fine-tuned and extract its scenario slug."""
    if not model_identifier:
        return False, None
    raw = str(model_identifier)
    if "-ft-" in raw:
        try:
            scenario = raw.split("-ft-")[1].split(":")[0].strip()
            return True, scenario
        except Exception:
            return True, "specialized"
    return False, None


async def _load_agent_checkpoint(app, model_id: str | None, model_episode: int | None = None) -> tuple[str, int]:
    """Load a specific model checkpoint into app.state.sim_agent and return (model_name, episode)."""
    active_m = getattr(app.state, "active_model_id", None) or "FlowSync DQN"
    active_e = getattr(app.state, "active_model_episode", None) or 1000
    if not model_id:
        return active_m, active_e

    try:
        from app.services import model_service
        raw_id = str(model_id).strip()
        target_ep = model_episode
        if ":" in raw_id:
            base_id, ep_str = raw_id.split(":", 1)
            ep_clean = ep_str.replace("checkpoint_", "").replace(".pt", "")
            if ep_clean.isdigit():
                target_ep = int(ep_clean)
            model_id_clean = base_id
        else:
            model_id_clean = raw_id

        checkpoints = await asyncio.to_thread(model_service.list_checkpoints, model_id_clean)
        if not checkpoints:
            return model_id_clean, target_ep or active_e

        episodes = [ep for p in checkpoints if (ep := _parse_checkpoint_ep(p))]
        if not episodes:
            return model_id_clean, target_ep or active_e

        if target_ep is not None and target_ep in episodes:
            chosen_ep = target_ep
        elif target_ep is not None:
            chosen_ep = min(episodes, key=lambda e: abs(e - target_ep))
        else:
            chosen_ep = max(episodes)

        checkpoint_data = await asyncio.to_thread(model_service.load_checkpoint, model_id_clean, chosen_ep)
        sim_agent = getattr(app.state, "sim_agent", None)
        if sim_agent and "online_net" in checkpoint_data:
            sim_agent.online_net.load_state_dict(checkpoint_data["online_net"])
            if "target_net" in checkpoint_data:
                sim_agent.target_net.load_state_dict(checkpoint_data["target_net"])
            else:
                sim_agent.sync_target_network()
            sim_agent.target_net.eval()

        app.state.active_model_id = model_id_clean
        app.state.active_model_episode = chosen_ep
        logger.info("Successfully loaded agent checkpoint %s at episode %d", model_id_clean, chosen_ep)
        return model_id_clean, chosen_ep
    except Exception as e:
        logger.warning("Could not load agent checkpoint %s: %s", model_id, e)
        return str(model_id), model_episode or active_e


# ─── Timed Benchmark ─────────────────────────────────────────────────────────

async def _run_timed_benchmark(
    app,
    websocket: WebSocket,
    duration_seconds: int,
    scenario_counts: dict | None,
    modes: list[str],
    arrivals: list[dict] | None = None,
    model_id: str | None = None,
    model_episode: int | None = None,
) -> None:
    """
    Runs all requested modes sequentially for comparison.

    Two execution modes:
    1. REAL-WORLD DIGITAL TWIN REPLAY (when arrivals list is provided):
       - Chronologically injects real-world vehicle arrivals at their exact recorded video timestamps (time_s).
       - Runs each mode until 100% of vehicles have cleared the intersection (total_passed >= total_vehicles).
       - Measures clearance_time (seconds to clear all vehicles) and avg_wait_time.
    2. STANDARD MULTI-MODE BENCHMARK (when arrivals is None):
       - Uses Common Random Numbers (CRN) with a synchronized seed.
       - Runs each mode for duration_seconds of simulation time.
       - Broadcasts real-time 10Hz frames driving the 3-D canvas.
    """
    TICK_DT = 0.1          # simulation seconds per tick (matches normal loop)
    TICK_SLEEP = 0.10      # wall-clock seconds between ticks (normal 1.0x real-time speed)
    PHASE_DIRS  = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
    PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}

    results: dict = {}
    prev_mode    = getattr(app.state, "mode", "fixed")
    prev_running = getattr(app.state, "sim_running", False)

    # Pause normal simulation loop so both don't fight over the intersection
    app.state.sim_running = False
    app.state.benchmark_running = True
    app.state.benchmark_cancelled = False
    if getattr(app.state, "sim_task", None) is not None:
        app.state.sim_task.cancel()
        try:
            await app.state.sim_task
        except Exception:
            pass
    await asyncio.sleep(0.2)

    # Resolve active model id and episode
    clean_model_id = str(model_id).strip() if model_id else (getattr(app.state, "active_model_id", None) or "FlowSync DQN")
    clean_model_ep = int(model_episode) if model_episode else (getattr(app.state, "active_model_episode", None) or 1000)

    # Generate a synchronized CRN seed for this benchmark session
    import random
    benchmark_seed = random.randint(1, 1_000_000)
    is_realworld = bool(arrivals and len(arrivals) > 0)
    total_vehicles_to_clear = len(arrivals) if is_realworld else 0
    sorted_arrivals = sorted(arrivals, key=lambda a: a.get("time_s", 0.0)) if is_realworld else []

    try:
        for mode_idx, mode in enumerate(modes):
            intersection = app.state.sim_intersection

            # Load selected checkpoint if entering AI mode
            if mode == "ai" and (model_id or model_episode):
                clean_model_id, clean_model_ep = await _load_agent_checkpoint(app, model_id, model_episode)

            agent = app.state.sim_agent if mode == "ai" else None

            # ── Setup ──────────────────────────────────────────────────────
            intersection.reset()
            phase_starvation = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
            benchmark_forecaster = ArrivalForecaster()
            vat_controller = None
            if mode in ("vat", "actuated"):
                from app.simulation.vat_controller import VATController
                vat_controller = VATController(intersection)
            if is_realworld:
                # Digital Twin Real-World Replay
                intersection.spawner.set_enabled(False)
                pending_arrivals = [dict(a) for a in sorted_arrivals]
                spawned_count = 0
            elif scenario_counts:
                intersection.inject_scenario(scenario_counts)
                try:
                    intersection.spawner.set_enabled(False)
                except Exception:
                    pass
                pending_arrivals = []
                spawned_count = sum(scenario_counts.values())
            else:
                # Standard Benchmark with Common Random Numbers (CRN)
                try:
                    intersection.spawner.set_seed(benchmark_seed)
                    intersection.spawner.set_enabled(True)
                except Exception:
                    pass
                pending_arrivals = []
                spawned_count = 0

            app.state.mode = mode

            # Notify frontend that this mode is starting
            try:
                await websocket.send_json({
                    "type": "benchmark_progress",
                    "current_mode": mode,
                    "mode_index": mode_idx,
                    "modes_total": len(modes),
                    "modes_done": list(results.keys()),
                    "elapsed": 0.0,
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": benchmark_seed,
                    "is_realworld": is_realworld,
                    "total_vehicles": total_vehicles_to_clear,
                    "spawned_count": 0,
                    "passed_count": 0,
                })
            except Exception:
                pass

            # ── Real-time simulation loop ──────────────────────────────────
            cumulative_reward = 0.0
            last_reward       = 0.0
            last_action       = 0
            was_exploring     = False
            obs               = np.zeros(20, dtype=np.float32)
            episode           = 0
            sim_time          = 0.0
            tick_count        = 0

            if is_realworld:
                # Real-world mode runs until all vehicles clear (safety timeout max 180s)
                max_timeout = max(60.0, total_vehicles_to_clear * 3.0)
                safety_deadline = asyncio.get_event_loop().time() + max_timeout
            else:
                # Generous safety deadline in case loop hangs
                safety_deadline = asyncio.get_event_loop().time() + max(duration_seconds * 3.0, 120.0)

            while True:
                if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                    break

                # Check exit condition
                now = asyncio.get_event_loop().time()

                # Standard benchmark: terminate mode when sim_time reaches duration_seconds
                if not is_realworld and sim_time >= float(duration_seconds):
                    break

                # Safety fallback timeout
                if now >= safety_deadline:
                    break

                # Count active vehicles currently on roads/queues
                total_active_vehicles = sum(len(q) for q in intersection.lanes.values())

                if is_realworld and len(pending_arrivals) == 0:
                    # Clean completion: All video vehicles have entered AND either:
                    # 1. Total passed reached the recorded count, OR
                    # 2. All vehicles on the road have fully crossed the intersection
                    if intersection.total_passed >= total_vehicles_to_clear or total_active_vehicles == 0:
                        break

                tick_start = now
                tick_count += 1
                sim_time += TICK_DT

                # ── Chronological vehicle arrivals (Real-World Replay) ───────
                if is_realworld:
                    while pending_arrivals and pending_arrivals[0].get("time_s", 0.0) <= sim_time:
                        next_arr = pending_arrivals[0]
                        dir_name = str(next_arr.get("lane", "north")).lower().replace("_bound", "").strip()
                        if dir_name not in ("north", "south", "east", "west"):
                            dir_name = "north"
                        turn = str(next_arr.get("turn", "straight")).lower().strip()
                        if turn not in ("straight", "left", "right"):
                            turn = "straight"
                        lane_key = f"{dir_name}_{turn}"
                        if lane_key not in intersection.lanes:
                            lane_key = f"{dir_name}_straight"

                        # If lane is excessively congested (>= 16 vehicles), wait for next tick to spawn
                        if len(intersection.lanes[lane_key]) >= 16:
                            break

                        arr = pending_arrivals.pop(0)
                        from app.simulation.vehicle import Vehicle, DEFAULT_SPEED
                        from uuid import uuid4
                        v = Vehicle(
                            id=arr.get("vehicle_id", f"cctv_{uuid4().hex[:6]}"),
                            lane=dir_name,
                            turn=turn,
                            position=0.0,
                            wait_time=0.0,
                            speed=DEFAULT_SPEED,
                            state="waiting",
                        )
                        intersection.lanes[lane_key].append(v)
                        spawned_count += 1
                        intersection._spawned_this_interval += 1

                # ── Compute action ─────────────────────────────────────────
                if mode in ("fixed", "manual"):
                    action = None
                    intersection.tick(dt=TICK_DT, action=None)
                elif mode in ("vat", "actuated"):
                    if vat_controller is None:
                        from app.simulation.vat_controller import VATController
                        vat_controller = VATController(intersection)
                    action = vat_controller.select_action()
                    last_action = action
                    intersection.tick(dt=TICK_DT, action=action)
                    vat_controller.update(
                        dt=TICK_DT,
                        spawned_this_step=max(0, getattr(intersection, "_spawned_this_interval", 0)),
                    )
                elif mode == "greedy":
                    signal = intersection.signal
                    queues = intersection.get_movement_queues()
                    phase_counts = {
                        ph: sum(
                            queues.get(f"{d}_{t}", 0)
                            for d in PHASE_DIRS[ph]
                            for t in PHASE_TURNS[ph]
                        )
                        for ph in range(4)
                    }
                    current_count = phase_counts.get(signal.current_phase, 0)
                    max_count = max(phase_counts.values()) if phase_counts else 0

                    # Pure greedy: prioritize phase with most vehicles.
                    # Maintain current green if it is tied for maximum, or if all queues are empty.
                    if (current_count >= max_count and current_count > 0) or max_count == 0:
                        best_phase = signal.current_phase
                    else:
                        best_phase = max(phase_counts, key=lambda p: phase_counts[p])

                    action       = best_phase if signal.can_switch_phase else signal.current_phase
                    last_action  = action
                    intersection.tick(dt=TICK_DT, action=action)
                elif mode == "ai" and agent is not None:
                    signal = intersection.signal
                    benchmark_forecaster.tick(dt=TICK_DT, spawned_this_step=max(0, getattr(intersection, "_spawned_this_interval", 0)))
                    obs = _build_obs_from_intersection(intersection, benchmark_forecaster)

                    action, _ = _select_ai_phase_action(
                        signal=signal,
                        intersection=intersection,
                        agent=agent,
                        obs=obs,
                        phase_starvation=phase_starvation,
                        dt=TICK_DT,
                    )

                    last_action = action
                    was_exploring = False
                    intersection.tick(dt=TICK_DT, action=action)
                else:
                    action = None
                    intersection.tick(dt=TICK_DT, action=None)

                # ── Build & broadcast frame (drives 3-D canvas) ────────────
                simulation_id = app.state.current_simulation_id or "benchmark"
                frame = build_frame(
                    intersection=intersection,
                    mode=mode,
                    episode=episode,
                    simulation_id=simulation_id,
                    agent=agent,
                    last_reward=last_reward,
                    cumulative_reward=cumulative_reward,
                    epsilon=0.0,
                    last_action=last_action,
                    was_exploring=was_exploring,
                    obs=obs,
                )
                await manager.broadcast(frame.model_dump())

                # Send progress updates every 5 ticks (~0.5s)
                if tick_count % 5 == 0:
                    mode_elapsed = min(float(duration_seconds), round(sim_time, 1)) if not is_realworld else round(sim_time, 1)
                    curr_active = sum(len(q) for q in intersection.lanes.values())
                    current_passed = (
                        total_vehicles_to_clear
                        if is_realworld and len(pending_arrivals) == 0 and curr_active == 0
                        else min(total_vehicles_to_clear, intersection.total_passed) if is_realworld else intersection.total_passed
                    )
                    try:
                        await websocket.send_json({
                            "type": "benchmark_progress",
                            "current_mode": mode,
                            "mode_index": mode_idx,
                            "modes_total": len(modes),
                            "modes_done": list(results.keys()),
                            "elapsed": mode_elapsed,
                            "duration_seconds": duration_seconds if not is_realworld else mode_elapsed,
                            "benchmark_seed": benchmark_seed,
                            "is_realworld": is_realworld,
                            "total_vehicles": total_vehicles_to_clear,
                            "spawned_count": spawned_count,
                            "passed_count": current_passed,
                        })
                    except Exception:
                        pass

                # ── Real-time pacing ───────────────────────────────────────
                elapsed = asyncio.get_event_loop().time() - tick_start
                sleep_t = max(0.0, TICK_SLEEP - elapsed)
                await asyncio.sleep(sleep_t)

            # ── Collect results ────────────────────────────────────────────
            queue_lengths = intersection.get_queue_lengths()
            final_time = float(duration_seconds) if not is_realworld else round(sim_time, 1)
            final_active = sum(len(q) for q in intersection.lanes.values())
            final_passed = (
                total_vehicles_to_clear
                if is_realworld and len(pending_arrivals) == 0 and final_active == 0
                else intersection.total_passed
            )
            results[mode] = {
                "total_passed":    final_passed,
                "total_vehicles":  total_vehicles_to_clear if is_realworld else final_passed,
                "avg_wait_time":   round(intersection.get_avg_wait_time(), 2),
                "max_queue":       max(queue_lengths.values(), default=0),
                "duration_seconds": duration_seconds,
                "clearance_time":  final_time,
            }

            # Broadcast intermediate results after each mode completes
            try:
                await websocket.send_json({
                    "type":           "benchmark_progress",
                    "current_mode":   mode,
                    "mode_index":     mode_idx,
                    "completed_mode": mode,
                    "result":         results[mode],
                    "modes_done":     list(results.keys()),
                    "modes_total":    len(modes),
                    "elapsed":        final_time if is_realworld else float(duration_seconds),
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": benchmark_seed,
                    "is_realworld":   is_realworld,
                    "total_vehicles": total_vehicles_to_clear,
                    "spawned_count":  spawned_count,
                    "passed_count":   final_passed,
                })
            except Exception:
                pass

        # ── Winner & Improvements Calculation ──────────────────────────────
        fixed_res = results.get("fixed")
        improvements = {}
        if fixed_res:
            f_wait = fixed_res.get("avg_wait_time", 0.0)
            f_clear = fixed_res.get("clearance_time", 0.0)
            if "ai" in results:
                if f_wait > 0:
                    improvements["ai_wait_pct"] = round(((f_wait - results["ai"]["avg_wait_time"]) / f_wait) * 100, 1)
                if f_clear > 0:
                    improvements["ai_clearance_pct"] = round(((f_clear - results["ai"]["clearance_time"]) / f_clear) * 100, 1)
            if "greedy" in results:
                if f_wait > 0:
                    improvements["greedy_wait_pct"] = round(((f_wait - results["greedy"]["avg_wait_time"]) / f_wait) * 100, 1)
                if f_clear > 0:
                    improvements["greedy_clearance_pct"] = round(((f_clear - results["greedy"]["clearance_time"]) / f_clear) * 100, 1)
            if "vat" in results:
                if f_wait > 0:
                    improvements["vat_wait_pct"] = round(((f_wait - results["vat"]["avg_wait_time"]) / f_wait) * 100, 1)
                if f_clear > 0:
                    improvements["vat_clearance_pct"] = round(((f_clear - results["vat"]["clearance_time"]) / f_clear) * 100, 1)

        # Winner: lowest avg wait time, fastest clearance time as tiebreaker
        def _score_mode(m):
            r = results[m]
            return (-r.get("avg_wait_time", 0.0), -r.get("clearance_time", 0.0), r.get("total_passed", 0))

        winner = max(results.keys(), key=_score_mode) if results else None

        # Auto-persist benchmark mode telemetry to session files for dashboard analytics & replay
        # E-01/F-04: Include benchmark metadata for scenario identification and population separation
        try:
            import hashlib as _hashlib
            sessions_dir = Path(SESSION_DIR)
            sessions_dir.mkdir(parents=True, exist_ok=True)
            active_model = clean_model_id
            active_eps = clean_model_ep

            # E-01: Compute scenario hash for CRN verification
            scenario_input = json.dumps({
                "seed": benchmark_seed,
                "duration": duration_seconds,
                "modes": sorted(modes),
                "is_realworld": is_realworld,
                "total_vehicles": total_vehicles_to_clear,
            }, sort_keys=True)
            scenario_hash = _hashlib.sha256(scenario_input.encode()).hexdigest()[:16]

            # Shared benchmark_id groups all modes from this run together
            benchmark_id = f"bm_{benchmark_seed}_{int(time.time())}"

            for m_key, r_data in results.items():
                m_passed = int(r_data.get("vehicles_passed", r_data.get("total_passed", 0)))
                m_wait = float(r_data.get("avg_wait_time", 0.0))
                m_q = int(r_data.get("max_queue", 0))
                m_dur = float(r_data.get("clearance_time", duration_seconds))
                m_vehs = total_vehicles_to_clear if is_realworld else max(m_passed, int(m_passed * 1.05))

                sess_key = f"bench_{m_key}_{int(time.time())}_{benchmark_seed % 1000}"
                file_p = sessions_dir / f"{sess_key}.json"

                is_ft, ft_scen = _detect_finetune_info(active_model) if m_key == "ai" else (False, None)

                payload = {
                    "session_id": sess_key,
                    "mode": m_key,
                    "model_name": active_model if m_key == "ai" else None,
                    "model_episodes": active_eps if m_key == "ai" else None,
                    "is_finetuned": is_ft,
                    "finetune_scenario": ft_scen,
                    "throughput": m_passed,
                    # F-04/E-01: Benchmark metadata for paired comparison & population separation
                    "run_type": "benchmark",
                    "benchmark_id": benchmark_id,
                    "benchmark_seed": benchmark_seed,
                    "scenario_hash": scenario_hash,
                    "controller_type": m_key,
                    "duration_seconds": duration_seconds,
                    "is_realworld": is_realworld,
                    "winner": winner,
                    "improvements": improvements,
                    "benchmark_modes": modes,
                    "benchmark_results": results,
                    "stats": {
                        "session_id": sess_key,
                        "mode": m_key,
                        "model_name": active_model if m_key == "ai" else None,
                        "model_episodes": active_eps if m_key == "ai" else None,
                        "is_finetuned": is_ft,
                        "finetune_scenario": ft_scen,
                        "frame_count": int(m_dur * 10),
                        "duration_s": m_dur,
                        "avg_fps": 10.0,
                        "total_detections": m_vehs,
                        "throughput": m_passed,
                        "avg_wait_s": m_wait,
                        "peak_queue": m_q,
                    },
                    "twin_data": {
                        "session_id": sess_key,
                        "total_frames_processed": int(m_dur * 10),
                        "total_vehicles_detected": m_vehs,
                        "video_duration_s": m_dur,
                        "total_passed": m_passed,
                        "arrivals": arrivals if arrivals else [],
                    },
                    "frames": [],
                }
                with open(file_p, "w", encoding="utf-8") as bf:
                    json.dump(payload, bf, indent=2)
        except Exception as be:
            logger.warning("Failed to auto-persist benchmark session: %s", be)

        # Final broadcast
        try:
            await websocket.send_json({
                "type":             "benchmark_results",
                "duration_seconds": results.get(winner, {}).get("clearance_time", duration_seconds) if is_realworld else duration_seconds,
                "results":          results,
                "winner":           winner,
                "modes":            modes,
                "improvements":     improvements,
                "benchmark_seed":   benchmark_seed,
                "benchmark_id":     benchmark_id,
                "model_name":       active_model,
                "model_episodes":   active_eps,
                "is_realworld":     is_realworld,
                "total_vehicles":   total_vehicles_to_clear,
                # D-02: Version metadata
                "environment_version": "v1.2",
                "state_version":       "v1_28d",
                "reward_version":      "v3_delay_anchored",
                "controller_version":  "v2.1",
                # RW-01: Benchmark type labeling
                "benchmark_type":      "cctv_digital_twin_replay" if is_realworld else "simulation_crn_paired",
                "scenario_hash":       scenario_hash,
            })
        except Exception as e:
            logger.warning("Failed to send benchmark_results: %s", e)

    except asyncio.CancelledError:
        logger.info("Benchmark cancelled by user")
    except Exception as e:
        logger.exception("Benchmark error: %s", e)
        try:
            await websocket.send_json({"type": "error", "code": "BENCHMARK_FAILED", "message": str(e)})
        except Exception:
            pass
    finally:
        # Restore previous state — restore spawner back to natural stochastic randomness for manual simulation
        app.state.mode = prev_mode
        app.state.sim_running = False
        app.state.sim_intersection.reset()
        try:
            app.state.sim_intersection.spawner.set_seed(None)
        except Exception:
            pass


async def _run_model_benchmark(
    app,
    websocket: WebSocket,
    duration_seconds: int,
    models_to_test: list[dict],
    scenario_counts: dict | None = None,
    seed: int | None = None,
) -> None:
    """
    Runs an automated multi-checkpoint simulation benchmark exclusively in DQN AI mode.
    Evaluates each requested model checkpoint under identical Common Random Numbers (CRN)
    traffic conditions to measure policy evolution across training episodes.
    """
    TICK_DT = 0.1
    TICK_SLEEP = 0.10

    if not models_to_test or len(models_to_test) < 2:
        try:
            await websocket.send_json({
                "type": "error",
                "code": "INVALID_MODELS",
                "message": "At least 2 model checkpoints are required for a multi-model benchmark."
            })
        except Exception:
            pass
        return

    results: dict = {}
    prev_mode = getattr(app.state, "mode", "ai")

    # Pause normal simulation loop
    app.state.sim_running = False
    app.state.benchmark_running = True
    app.state.benchmark_cancelled = False
    if getattr(app.state, "sim_task", None) is not None:
        app.state.sim_task.cancel()
        try:
            await app.state.sim_task
        except Exception:
            pass
    await asyncio.sleep(0.2)

    import random
    benchmark_seed = seed if seed is not None else random.randint(1, 1_000_000)
    benchmark_id = f"bm_model_{benchmark_seed}_{int(time.time())}"

    # Build unique keys and metadata for each model in sequence
    resolved_models = []
    for idx, m_spec in enumerate(models_to_test):
        raw_id = str(m_spec.get("id") or f"model_{idx+1}")
        ep_val = m_spec.get("episodes") or m_spec.get("version")
        ep_num = int(ep_val) if ep_val and str(ep_val).isdigit() else 0
        name = m_spec.get("name") or f"Model {ep_num}eps"
        key = f"model_{ep_num}" if ep_num > 0 else f"model_{idx+1}"
        if any(rm["key"] == key for rm in resolved_models):
            key = f"{key}_{idx+1}"
        resolved_models.append({
            "key": key,
            "raw_id": raw_id,
            "episodes": ep_num,
            "name": name,
        })

    try:
        for model_idx, m_info in enumerate(resolved_models):
            if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                break

            m_key = m_info["key"]
            m_raw_id = m_info["raw_id"]
            m_target_ep = m_info["episodes"]
            m_name = m_info["name"]

            # Load selected agent checkpoint into sim_agent
            clean_id, chosen_ep = await _load_agent_checkpoint(app, m_raw_id, m_target_ep)
            app.state.active_model_id = clean_id
            app.state.active_model_episode = chosen_ep
            app.state.mode = "ai"

            intersection = app.state.sim_intersection
            intersection.reset()
            phase_starvation = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
            benchmark_forecaster = ArrivalForecaster()
            agent = app.state.sim_agent

            if scenario_counts:
                intersection.inject_scenario(scenario_counts)
                try:
                    intersection.spawner.set_enabled(False)
                except Exception:
                    pass
                spawned_count = sum(scenario_counts.values())
            else:
                try:
                    intersection.spawner.set_seed(benchmark_seed)
                    intersection.spawner.set_enabled(True)
                except Exception:
                    pass
                spawned_count = 0

            # Notify frontend that this model checkpoint is starting
            try:
                await websocket.send_json({
                    "type": "benchmark_progress",
                    "benchmark_type": "model_comparison",
                    "current_mode": m_key,
                    "current_model": m_name,
                    "current_model_id": clean_id,
                    "current_episode": chosen_ep,
                    "mode_index": model_idx,
                    "modes_total": len(resolved_models),
                    "modes_done": list(results.keys()),
                    "elapsed": 0.0,
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": benchmark_seed,
                    "spawned_count": 0,
                    "passed_count": 0,
                })
            except Exception:
                pass

            sim_time = 0.0
            tick_count = 0
            safety_deadline = asyncio.get_event_loop().time() + max(duration_seconds * 3.0, 120.0)

            while True:
                if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                    break

                now = asyncio.get_event_loop().time()
                if sim_time >= float(duration_seconds) or now >= safety_deadline:
                    break

                tick_start = now
                tick_count += 1
                sim_time += TICK_DT

                # DQN AI decision logic
                signal = intersection.signal
                benchmark_forecaster.tick(dt=TICK_DT, spawned_this_step=max(0, getattr(intersection, "_spawned_this_interval", 0)))
                obs = _build_obs_from_intersection(intersection, benchmark_forecaster)

                action, _ = _select_ai_phase_action(
                    signal=signal,
                    intersection=intersection,
                    agent=agent,
                    obs=obs,
                    phase_starvation=phase_starvation,
                    dt=TICK_DT,
                )
                intersection.tick(dt=TICK_DT, action=action)

                # Broadcast 3D simulation frame
                frame = build_frame(
                    intersection=intersection,
                    mode="ai",
                    episode=chosen_ep,
                    simulation_id=f"bm-model-{chosen_ep}",
                    agent=agent,
                    last_reward=0.0,
                    cumulative_reward=0.0,
                    epsilon=0.0,
                    last_action=action,
                    was_exploring=False,
                    obs=obs,
                )
                await manager.broadcast(frame.model_dump())

                # Send progress updates every 5 ticks (~0.5s)
                if tick_count % 5 == 0:
                    mode_elapsed = min(float(duration_seconds), round(sim_time, 1))
                    try:
                        await websocket.send_json({
                            "type": "benchmark_progress",
                            "benchmark_type": "model_comparison",
                            "current_mode": m_key,
                            "current_model": m_name,
                            "current_model_id": clean_id,
                            "current_episode": chosen_ep,
                            "mode_index": model_idx,
                            "modes_total": len(resolved_models),
                            "modes_done": list(results.keys()),
                            "elapsed": mode_elapsed,
                            "duration_seconds": duration_seconds,
                            "benchmark_seed": benchmark_seed,
                            "spawned_count": getattr(intersection, "_spawned_this_interval", 0),
                            "passed_count": intersection.total_passed,
                            "avg_wait": round(intersection.get_avg_wait_time(), 2),
                        })
                    except Exception:
                        pass

                elapsed = asyncio.get_event_loop().time() - tick_start
                await asyncio.sleep(max(0.0, TICK_SLEEP - elapsed))

            # Collect results for this model checkpoint
            queue_lengths = intersection.get_queue_lengths()
            final_time = float(duration_seconds)
            results[m_key] = {
                "key": m_key,
                "label": m_name,
                "model_id": clean_id,
                "model_episode": chosen_ep,
                "total_passed": intersection.total_passed,
                "avg_wait_time": round(intersection.get_avg_wait_time(), 2),
                "max_queue": max(queue_lengths.values(), default=0),
                "duration_seconds": duration_seconds,
                "clearance_time": final_time,
            }

            # Intermediate progress broadcast
            try:
                await websocket.send_json({
                    "type": "benchmark_progress",
                    "benchmark_type": "model_comparison",
                    "current_mode": m_key,
                    "current_model": m_name,
                    "mode_index": model_idx,
                    "completed_mode": m_key,
                    "result": results[m_key],
                    "modes_done": list(results.keys()),
                    "modes_total": len(resolved_models),
                    "elapsed": final_time,
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": benchmark_seed,
                    "spawned_count": getattr(intersection, "_spawned_this_interval", 0),
                    "passed_count": intersection.total_passed,
                })
            except Exception:
                pass

        if not results:
            return

        # ── Winner Determination & Improvements vs Baseline ───────────────────
        # Baseline model: lowest episode count
        baseline_key = min(results.keys(), key=lambda k: results[k].get("model_episode", 0))
        baseline_wait = results[baseline_key].get("avg_wait_time", 0.0)

        improvements: dict = {}
        for k, r in results.items():
            if baseline_wait > 0:
                imp = round(((baseline_wait - r["avg_wait_time"]) / baseline_wait) * 100.0, 1)
                improvements[f"{k}_wait_pct"] = imp

        # Winner: lowest avg wait time, highest throughput as tiebreaker
        def _score_model_res(k):
            r = results[k]
            return (-r.get("avg_wait_time", 0.0), r.get("total_passed", 0))

        winner_key = max(results.keys(), key=_score_model_res)
        winner_data = results.get(winner_key, {})
        winner_label = winner_data.get("label", winner_key)
        winner_ep = winner_data.get("model_episode", 0)

        # ── Auto-persist sessions for history and analytics ───────────────────
        try:
            sessions_dir = Path(SESSION_DIR)
            sessions_dir.mkdir(parents=True, exist_ok=True)
            for m_key, r_data in results.items():
                sess_key = f"bench_model_{r_data.get('model_episode', 0)}_{int(time.time())}_{benchmark_seed % 1000}"
                file_p = sessions_dir / f"{sess_key}.json"

                m_label = r_data.get("label") or r_data.get("model_id") or ""
                is_ft, ft_scen = _detect_finetune_info(m_label)

                payload = {
                    "session_id": sess_key,
                    "mode": "ai",
                    "controller_type": f"DQN ({r_data.get('model_episode', 0)} eps)",
                    "model_name": r_data.get("label"),
                    "model_episodes": r_data.get("model_episode", 0),
                    "is_finetuned": is_ft,
                    "finetune_scenario": ft_scen,
                    "throughput": r_data.get("total_passed", 0),
                    "run_type": "benchmark",
                    "benchmark_type": "model_comparison",
                    "benchmark_id": benchmark_id,
                    "benchmark_seed": benchmark_seed,
                    "duration_seconds": duration_seconds,
                    "winner": winner_key,
                    "winner_label": winner_label,
                    "winner_episode": winner_ep,
                    "improvements": improvements,
                    "benchmark_modes": list(results.keys()),
                    "benchmark_results": results,
                    "stats": {
                        "session_id": sess_key,
                        "mode": "ai",
                        "model_name": r_data.get("label"),
                        "model_episodes": r_data.get("model_episode", 0),
                        "is_finetuned": is_ft,
                        "finetune_scenario": ft_scen,
                        "frame_count": int(duration_seconds * 10),
                        "duration_s": float(duration_seconds),
                        "avg_fps": 10.0,
                        "total_detections": r_data.get("total_passed", 0),
                        "throughput": r_data.get("total_passed", 0),
                        "avg_wait_s": r_data.get("avg_wait_time", 0.0),
                        "peak_queue": r_data.get("max_queue", 0),
                    },
                    "twin_data": {
                        "session_id": sess_key,
                        "total_frames_processed": int(duration_seconds * 10),
                        "total_vehicles_detected": r_data.get("total_passed", 0),
                        "video_duration_s": float(duration_seconds),
                        "total_passed": r_data.get("total_passed", 0),
                        "arrivals": [],
                    },
                    "frames": [],
                }
                with open(file_p, "w", encoding="utf-8") as bf:
                    json.dump(payload, bf, indent=2)
        except Exception as be:
            logger.warning("Failed to auto-persist model benchmark session: %s", be)

        # ── Final Broadcast ──────────────────────────────────────────────────
        try:
            await websocket.send_json({
                "type": "benchmark_results",
                "benchmark_type": "model_comparison",
                "duration_seconds": duration_seconds,
                "results": results,
                "winner": winner_key,
                "winner_label": winner_label,
                "winner_episode": winner_ep,
                "modes": list(results.keys()),
                "improvements": improvements,
                "benchmark_seed": benchmark_seed,
                "benchmark_id": benchmark_id,
                "models": resolved_models,
            })
        except Exception as e:
            logger.warning("Failed to send model benchmark_results: %s", e)

    except asyncio.CancelledError:
        logger.info("Model benchmark cancelled by user")
    except Exception as e:
        logger.exception("Model benchmark error: %s", e)
        try:
            await websocket.send_json({"type": "error", "code": "MODEL_BENCHMARK_FAILED", "message": str(e)})
        except Exception:
            pass
    finally:
        app.state.mode = prev_mode
        app.state.sim_running = False
        app.state.benchmark_running = False
        app.state.sim_intersection.reset()
        try:
            app.state.sim_intersection.spawner.set_seed(None)
        except Exception:
            pass


# ─── Scenario Benchmark (Fixed + Greedy + AI) with Real-Time 3D Simulation ────

def _generate_scenario_traffic(
    seed: int,
    spawn_lambda: float,
    duration_seconds: int,
    dt: float = 0.1,
) -> List[Dict[str, Any]]:
    """
    Pre-generate a deterministic vehicle arrival schedule for the entire scenario duration.
    Guarantees 100% mathematical identicality across Fixed, Greedy, and DQN:
      - Exact same total vehicle count
      - Exact same arrival timestamps (time_s)
      - Exact same lanes and turns
      - Exact same initial speed (DEFAULT_SPEED) and zero wait time
    """
    rng = np.random.default_rng(int(seed))
    arrivals: List[Dict[str, Any]] = []
    dir_names = ["north", "south", "east", "west"]
    total_ticks = int(duration_seconds / dt)

    v_counter = 0
    for tick in range(total_ticks):
        time_s = round(tick * dt, 2)
        for dir_name in dir_names:
            num_arrivals = int(rng.poisson(spawn_lambda * dt))
            for _ in range(num_arrivals):
                turn = str(rng.choice(["straight", "left", "right"], p=[0.5, 0.25, 0.25]))
                arrivals.append({
                    "vehicle_id": f"sc_{seed}_{v_counter}",
                    "time_s": time_s,
                    "lane": dir_name,
                    "turn": turn,
                })
                v_counter += 1

    return arrivals


async def _run_scenario_benchmark(
    app,
    websocket: WebSocket,
    scenario_id: str,
    seed: int,
    spawn_lambda: float,
    duration_seconds: int,
    model_id: str,
    model_episode: int,
) -> None:
    """
    Real-time 3D multi-controller scenario evaluation.
    Runs DQN (AI) → Fixed → Greedy sequentially in real-time, driving the 3D Canvas.
    All controllers receive the identical pre-generated vehicle arrivals under Common Random Numbers (CRN).
    """
    import hashlib as _hashlib
    from ..simulation.vehicle import DEFAULT_SPEED, Vehicle

    PHASE_DIRS  = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
    PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}
    TICK_DT     = 0.1

    prev_mode    = getattr(app.state, "mode", "fixed")
    prev_running = getattr(app.state, "sim_running", False)

    # Pause any running background simulation loop
    app.state.sim_running = False
    if getattr(app.state, "sim_task", None) is not None:
        app.state.sim_task.cancel()
        try:
            await app.state.sim_task
        except Exception:
            pass
    await asyncio.sleep(0.15)

    # Resolve active model id and episode
    active_m = getattr(app.state, "active_model_id", None) or "FlowSync DQN"
    active_e = getattr(app.state, "active_model_episode", None) or 1000
    clean_model_id = str(model_id).strip() if model_id else active_m
    clean_model_ep = int(model_episode) if model_episode else active_e

    # Unique run group identifier
    run_group_id = f"rg_{scenario_id[:8]}_{seed}_{int(time.time())}"

    # Compute scenario hash
    num_steps = duration_seconds * 10
    scenario_spec = json.dumps({
        "seed": seed,
        "num_steps": num_steps,
        "spawn_lambda": spawn_lambda,
        "red_duration": 3.0,
        "topology": "single_intersection",
    }, sort_keys=True)
    scenario_hash = _hashlib.sha256(scenario_spec.encode()).hexdigest()[:16]

    # Pre-generate 100% identical vehicle arrival schedule
    scenario_arrivals = _generate_scenario_traffic(seed, spawn_lambda, duration_seconds, dt=TICK_DT)
    total_scheduled_vehicles = len(scenario_arrivals)
    logger.info(
        "Generated %d deterministic vehicle arrivals for scenario %s (seed=%d, λ=%.1f, dur=%ds)",
        total_scheduled_vehicles, scenario_id, seed, spawn_lambda, duration_seconds,
    )

    controllers = ["ai", "fixed", "greedy"]
    results: dict = {}

    prev_mode = getattr(app.state, "mode", "fixed")
    app.state.sim_running = False
    app.state.benchmark_running = True
    app.state.benchmark_cancelled = False

    try:
        intersection = app.state.sim_intersection

        for i, controller in enumerate(controllers):
            if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                break

            # Reset intersection to clean state
            intersection.reset()
            intersection.spawner.set_enabled(False)  # Pre-scheduled arrivals drive all spawning
            if controller == "ai":
                if model_id or model_episode:
                    clean_model_id, clean_model_ep = await _load_agent_checkpoint(app, model_id, model_episode)
                agent = app.state.sim_agent
            else:
                agent = None
            forecaster = ArrivalForecaster()
            phase_starvation = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

            # Local copy of identical arrivals schedule for this mode
            pending_arrivals = [dict(a) for a in scenario_arrivals]
            spawned_count = 0

            # Metric collectors
            per_dir_no_green = {d: 0 for d in ["north", "south", "east", "west"]}
            starvation_count = 0
            max_queue_seen = 0
            queue_area = 0.0
            delays: List[float] = []
            watchdog_overrides = 0

            sim_time = 0.0
            tick_count = 0

            # Normal 1.0x real-time pacing (0.1s simulation tick = 0.1s wall-clock time)
            tick_sleep = 0.10

            # Notify frontend: mode starting
            try:
                await websocket.send_json({
                    "type": "benchmark_progress",
                    "current_mode": controller,
                    "mode_index": i,
                    "modes_total": len(controllers),
                    "modes_done": controllers[:i],
                    "elapsed": 0.0,
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": seed,
                    "scenario_id": scenario_id,
                    "scenario_hash": scenario_hash,
                    "run_group_id": run_group_id,
                    "spawned_count": 0,
                    "passed_count": 0,
                })
            except Exception:
                pass

            while sim_time < float(duration_seconds):
                if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                    logger.info("Scenario benchmark cancelled during mode %s", controller)
                    break
                tick_start = asyncio.get_event_loop().time()
                tick_count += 1
                sim_time += TICK_DT

                # 1. Inject scheduled vehicle arrivals whose time has arrived
                while pending_arrivals and pending_arrivals[0]["time_s"] <= sim_time:
                    next_arr = pending_arrivals[0]
                    dir_name = next_arr["lane"]
                    turn = next_arr["turn"]
                    lane_key = f"{dir_name}_{turn}"
                    lane_queue = intersection.lanes.get(lane_key, [])

                    # Prevent overlap at entrance
                    if len(lane_queue) >= 16:
                        break
                    if lane_queue and lane_queue[-1].position < 0.05:
                        break

                    arr = pending_arrivals.pop(0)
                    v = Vehicle(
                        id=arr["vehicle_id"],
                        lane=dir_name,
                        turn=turn,
                        position=0.0,
                        wait_time=0.0,
                        speed=DEFAULT_SPEED,
                        state="waiting",
                    )
                    intersection.lanes[lane_key].append(v)
                    spawned_count += 1
                    intersection._spawned_this_interval += 1

                # 2. Action selection per controller
                last_action = 0
                obs = np.zeros(20, dtype=np.float32)

                if controller == "fixed":
                    action = None
                    last_action = intersection.signal.current_phase
                    passed = intersection.tick(dt=TICK_DT, action=None)

                elif controller == "greedy":
                    signal = intersection.signal
                    queues = intersection.get_movement_queues()
                    phase_counts = {
                        ph: sum(queues.get(f"{d}_{t}", 0) for d in PHASE_DIRS[ph] for t in PHASE_TURNS[ph])
                        for ph in range(4)
                    }
                    current_count = phase_counts.get(signal.current_phase, 0)
                    max_count = max(phase_counts.values()) if phase_counts else 0

                    # Pure greedy: prioritize phase with most vehicles.
                    # Maintain current green if it is tied for maximum, or if all queues are empty.
                    if (current_count >= max_count and current_count > 0) or max_count == 0:
                        best_phase = signal.current_phase
                    else:
                        best_phase = max(phase_counts, key=lambda p: phase_counts[p])

                    action = best_phase if signal.can_switch_phase else signal.current_phase
                    last_action = action
                    passed = intersection.tick(dt=TICK_DT, action=action)

                elif controller == "ai":
                    signal = intersection.signal
                    forecaster.tick(dt=TICK_DT, spawned_this_step=max(0, getattr(intersection, "_spawned_this_interval", 0)))
                    obs = _build_obs_from_intersection(intersection, forecaster)

                    action, was_override = _select_ai_phase_action(
                        signal=signal,
                        intersection=intersection,
                        agent=agent,
                        obs=obs,
                        phase_starvation=phase_starvation,
                        dt=TICK_DT,
                    )
                    if was_override:
                        watchdog_overrides += 1

                    last_action = action
                    passed = intersection.tick(dt=TICK_DT, action=action)
                else:
                    passed = intersection.tick(dt=TICK_DT, action=None)

                # 3. Accumulate vehicle delays
                for v in passed:
                    delays.append(v.wait_time)

                # 4. Starvation detection (direction denied green >= 30 steps)
                active_dirs = PHASE_DIRS.get(intersection.signal.current_phase, [])
                for d in ["north", "south", "east", "west"]:
                    if d not in active_dirs:
                        per_dir_no_green[d] += 1
                        if per_dir_no_green[d] >= 30:
                            starvation_count += 1
                            per_dir_no_green[d] = 0
                    else:
                        per_dir_no_green[d] = 0

                # 5. Track queue metrics
                q_lens = intersection.get_queue_lengths()
                current_max_q = max(q_lens.values(), default=0)
                if current_max_q > max_queue_seen:
                    max_queue_seen = current_max_q
                queue_area += sum(q_lens.values()) * TICK_DT

                # 6. Real-time 3D Canvas broadcast
                sim_id = getattr(app.state, "current_simulation_id", "scenario") or "scenario"
                frame = build_frame(
                    intersection=intersection,
                    mode=controller,
                    episode=clean_model_ep,
                    simulation_id=sim_id,
                    agent=agent if controller == "ai" else None,
                    last_reward=0.0,
                    cumulative_reward=0.0,
                    epsilon=0.0,
                    last_action=last_action,
                    was_exploring=False,
                    obs=obs,
                )
                await manager.broadcast(frame.model_dump())

                # 7. Progress broadcast every 5 ticks (~0.5s)
                if tick_count % 5 == 0:
                    try:
                        await websocket.send_json({
                            "type": "benchmark_progress",
                            "current_mode": controller,
                            "mode_index": i,
                            "modes_total": len(controllers),
                            "modes_done": controllers[:i],
                            "elapsed": min(float(duration_seconds), round(sim_time, 1)),
                            "duration_seconds": duration_seconds,
                            "benchmark_seed": seed,
                            "scenario_id": scenario_id,
                            "scenario_hash": scenario_hash,
                            "run_group_id": run_group_id,
                            "spawned_count": spawned_count,
                            "passed_count": intersection.total_passed,
                        })
                    except Exception:
                        pass

                # 8. Real-time pacing sleep (normal 1.0x real-time speed)
                elapsed = asyncio.get_event_loop().time() - tick_start
                sleep_t = max(0.001, tick_sleep - elapsed)
                await asyncio.sleep(sleep_t)

            if getattr(app.state, "benchmark_cancelled", False) or not getattr(app.state, "benchmark_running", True):
                break

            # ── Collect metrics for this controller ────────────────────────────
            avg_wait = round(intersection.get_avg_wait_time(), 3)
            tot_passed = int(intersection.total_passed)
            med_delay = round(float(np.median(delays)), 3) if delays else avg_wait
            p95_d = round(float(np.percentile(delays, 95)), 3) if delays else avg_wait
            std_d = round(float(np.std(delays)), 3) if delays else 0.0
            q_area = round(float(queue_area), 2)
            starv = int(starvation_count)
            ovr_rate = round(float(watchdog_overrides / max(1, tick_count)), 4)

            ctrl_result = {
                "avg_wait_time": avg_wait,
                "total_passed": tot_passed,
                "max_queue": max_queue_seen,
                "median_delay": med_delay,
                "p95_delay": p95_d,
                "std_delay": std_d,
                "queue_area": q_area,
                "starvation_count": starv,
                "override_rate": ovr_rate,
                "duration_seconds": duration_seconds,
            }
            results[controller] = ctrl_result

            logger.info(
                "Scenario [%s] Mode %s completed: wait=%.2fs passed=%d queue=%d starv=%d",
                run_group_id, controller, avg_wait, tot_passed, max_queue_seen, starv,
            )

            # ── Persist row to Supabase ─────────────────────────────────────────
            try:
                await asyncio.to_thread(
                    supabase_service.save_scenario_run,
                    scenario_id,
                    clean_model_id,
                    clean_model_ep,
                    controller,
                    scenario_hash,
                    avg_wait,
                    tot_passed,
                    max_queue_seen,
                    ovr_rate,
                    run_group_id,
                    med_delay,
                    p95_d,
                    std_d,
                    q_area,
                    starv,
                )
            except Exception as e:
                logger.warning("save_scenario_run failed for controller=%s: %s", controller, e)

            # ── Send completion update for this controller ─────────────────────
            try:
                await websocket.send_json({
                    "type": "benchmark_progress",
                    "current_mode": controller,
                    "completed_mode": controller,
                    "mode_index": i + 1,
                    "modes_total": len(controllers),
                    "modes_done": controllers[:i + 1],
                    "elapsed": float(duration_seconds),
                    "duration_seconds": duration_seconds,
                    "benchmark_seed": seed,
                    "scenario_id": scenario_id,
                    "scenario_hash": scenario_hash,
                    "run_group_id": run_group_id,
                    "result": ctrl_result,
                })
            except Exception:
                pass

            # Pause briefly between controllers for clear visual transition and clean environment reset
            if i < len(controllers) - 1:
                next_ctrl = controllers[i + 1]
                intersection.reset()
                empty_frame = build_frame(
                    intersection=intersection,
                    mode=next_ctrl,
                    episode=clean_model_ep,
                    simulation_id=sim_id,
                    agent=app.state.sim_agent if next_ctrl == "ai" else None,
                    last_reward=0.0,
                    cumulative_reward=0.0,
                    epsilon=0.0,
                    last_action=0,
                    was_exploring=False,
                    obs=None,
                )
                await manager.broadcast(empty_frame.model_dump())
                await asyncio.sleep(0.8)

        # ── Auto-persist scenario benchmark to session files for dashboard history ──
        try:
            sessions_dir = Path(SESSION_DIR)
            sessions_dir.mkdir(parents=True, exist_ok=True)

            fixed_res = results.get("fixed")
            sc_improvements = {}
            if fixed_res:
                f_wait = fixed_res.get("avg_wait_time", 0.0)
                if "ai" in results and f_wait > 0:
                    sc_improvements["ai_wait_pct"] = round(((f_wait - results["ai"]["avg_wait_time"]) / f_wait) * 100, 1)
                if "greedy" in results and f_wait > 0:
                    sc_improvements["greedy_wait_pct"] = round(((f_wait - results["greedy"]["avg_wait_time"]) / f_wait) * 100, 1)

            def _sc_score(m):
                r = results.get(m, {})
                return (-r.get("avg_wait_time", 999.0), r.get("total_passed", 0))
            sc_winner = max(results.keys(), key=_sc_score) if results else "ai"

            for m_key, r_data in results.items():
                m_passed = int(r_data.get("total_passed", 0))
                m_wait = float(r_data.get("avg_wait_time", 0.0))
                m_q = int(r_data.get("max_queue", 0))
                m_dur = float(r_data.get("duration_seconds", duration_seconds))

                sess_key = f"bench_sc_{scenario_id[:8]}_{m_key}_{int(time.time())}_{seed % 1000}"
                file_p = sessions_dir / f"{sess_key}.json"

                is_ft, ft_scen = _detect_finetune_info(clean_model_id) if m_key == "ai" else (False, None)

                payload = {
                    "session_id": sess_key,
                    "mode": m_key,
                    "model_name": clean_model_id if m_key == "ai" else None,
                    "model_episodes": clean_model_ep if m_key == "ai" else None,
                    "is_finetuned": is_ft,
                    "finetune_scenario": ft_scen,
                    "throughput": m_passed,
                    "run_type": "benchmark",
                    "benchmark_id": run_group_id,
                    "benchmark_seed": seed,
                    "scenario_id": scenario_id,
                    "scenario_hash": scenario_hash,
                    "controller_type": m_key,
                    "duration_seconds": duration_seconds,
                    "winner": sc_winner,
                    "improvements": sc_improvements,
                    "benchmark_modes": controllers,
                    "benchmark_results": results,
                    "stats": {
                        "session_id": sess_key,
                        "mode": m_key,
                        "model_name": clean_model_id if m_key == "ai" else None,
                        "model_episodes": clean_model_ep if m_key == "ai" else None,
                        "is_finetuned": is_ft,
                        "finetune_scenario": ft_scen,
                        "frame_count": int(m_dur * 10),
                        "duration_s": m_dur,
                        "avg_fps": 10.0,
                        "total_detections": max(m_passed, int(m_passed * 1.05)),
                        "throughput": m_passed,
                        "avg_wait_s": m_wait,
                        "peak_queue": m_q,
                    },
                    "twin_data": {
                        "session_id": sess_key,
                        "total_frames_processed": int(m_dur * 10),
                        "total_vehicles_detected": max(m_passed, int(m_passed * 1.05)),
                        "video_duration_s": m_dur,
                        "total_passed": m_passed,
                        "arrivals": [],
                    },
                    "frames": [],
                }
                with open(file_p, "w", encoding="utf-8") as bf:
                    json.dump(payload, bf, indent=2)
        except Exception as se:
            logger.warning("Failed to auto-persist scenario benchmark session: %s", se)

        # ── Final broadcast with full 3-controller paired results ─────────────
        try:
            await websocket.send_json({
                "type":           "scenario_benchmark_results",
                "scenario_id":    scenario_id,
                "run_group_id":   run_group_id,
                "model_id":       clean_model_id,
                "scenario_hash":  scenario_hash,
                "benchmark_seed": seed,
                "duration_seconds": duration_seconds,
                "results":        results,
            })
        except Exception as e:
            logger.warning("Final scenario_benchmark_results broadcast failed: %s", e)

    except asyncio.CancelledError:
        logger.info("Scenario benchmark cancelled by user (run_group=%s)", run_group_id)
        try:
            await websocket.send_json({"type": "simulation_stopped", "run_group_id": run_group_id})
        except Exception:
            pass
    except Exception as e:
        logger.exception("Scenario benchmark error: %s", e)
        try:
            await websocket.send_json({"type": "error", "code": "SCENARIO_BENCHMARK_FAILED", "message": str(e)})
        except Exception:
            pass
    finally:
        app.state.benchmark_running = False
        app.state.mode = prev_mode
        app.state.sim_running = False
        app.state.sim_intersection.reset()
        try:
            app.state.sim_intersection.spawner.set_enabled(True)
            app.state.sim_intersection.spawner.set_seed(None)
        except Exception:
            pass


# ─── Simulation loop ──────────────────────────────────────────────────────────

async def _simulation_loop(app) -> None:
    cumulative_reward = 0.0
    last_reward = 0.0
    last_action = 0
    was_exploring = False
    obs = None

    forecaster = getattr(app.state, "sim_forecaster", None)
    if forecaster is None:
        forecaster = ArrivalForecaster()
        app.state.sim_forecaster = forecaster

    PHASE_DIRS = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
    PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}
    phase_starvation = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

    try:
        while True:
            if not app.state.sim_running or getattr(app.state, "benchmark_running", False):
                await asyncio.sleep(0.1)
                continue

            intersection = app.state.sim_intersection
            mode = app.state.mode
            trainer = app.state.trainer
            episode = trainer.current_episode if trainer else 0
            agent = app.state.sim_agent

            sim_speed = getattr(app.state, "sim_speed", 1.0)
            if sim_speed <= 1.0:
                sub_steps = 1
                sleep_duration = max(0.02, 0.1 / max(0.25, sim_speed))
            elif sim_speed <= 2.0:
                sub_steps = 2
                sleep_duration = 0.08
            elif sim_speed <= 4.0:
                sub_steps = 4
                sleep_duration = 0.06
            elif sim_speed <= 8.0:
                sub_steps = 8
                sleep_duration = 0.05
            else:
                sub_steps = 16
                sleep_duration = 0.04

            for _ in range(sub_steps):
                prev_spawned = getattr(intersection, "_spawned_this_interval", 0)
                if mode in ("fixed", "manual"):
                    intersection.tick(dt=0.1, action=None, is_manual=(mode == "manual"))
                    spawned_this = getattr(intersection, "_spawned_this_interval", 0) - prev_spawned
                    forecaster.tick(dt=0.1, spawned_this_step=max(0, spawned_this))
                    last_reward = 0.0
                elif mode == "greedy":
                    signal = intersection.signal
                    queues = intersection.get_movement_queues()
                    phase_counts = {
                        ph: sum(
                            queues.get(f"{d}_{t}", 0)
                            for d in PHASE_DIRS[ph]
                            for t in PHASE_TURNS[ph]
                        )
                        for ph in range(4)
                    }
                    current_count = phase_counts.get(signal.current_phase, 0)
                    max_count = max(phase_counts.values()) if phase_counts else 0

                    # Pure greedy: prioritize phase with most vehicles.
                    # Maintain current green if it is tied for maximum, or if all queues are empty.
                    if (current_count >= max_count and current_count > 0) or max_count == 0:
                        best_phase = signal.current_phase
                    else:
                        best_phase = max(phase_counts, key=lambda p: phase_counts[p])

                    greedy_action = best_phase if signal.can_switch_phase else signal.current_phase
                    intersection.tick(dt=0.1, action=greedy_action)
                    spawned_this = getattr(intersection, "_spawned_this_interval", 0) - prev_spawned
                    forecaster.tick(dt=0.1, spawned_this_step=max(0, spawned_this))
                    last_reward = 0.0
                elif mode == "ai":
                    signal = intersection.signal
                    spawned_this = getattr(intersection, "_spawned_this_interval", 0) - prev_spawned
                    forecaster.tick(dt=0.1, spawned_this_step=max(0, spawned_this))
                    obs = _build_obs_from_intersection(intersection, forecaster)

                    action, _ = _select_ai_phase_action(
                        signal=signal,
                        intersection=intersection,
                        agent=agent,
                        obs=obs,
                        phase_starvation=phase_starvation,
                        dt=0.1,
                    )

                    last_action = action

                    prev_pressures = compute_movement_pressures(intersection.get_movement_queues(), intersection.get_outgoing_counts())
                    prev_passed = intersection.total_passed
                    prev_phase = intersection.signal.current_phase

                    intersection.tick(dt=0.1, action=action)

                    curr_pressures = compute_movement_pressures(intersection.get_movement_queues(), intersection.get_outgoing_counts())
                    curr_passed = intersection.total_passed
                    vehicles_passed = curr_passed - prev_passed
                    phase_changed = (action != prev_phase) and (intersection.signal.color.value == "green")

                    last_reward = 0.0
                    try:
                        if getattr(app.state, "training_env", None) is not None:
                            reward_result = app.state.training_env.compute_reward(
                                prev_pressures=prev_pressures,
                                curr_pressures=curr_pressures,
                                vehicles_passed=vehicles_passed,
                                phase_changed=phase_changed,
                                signal=intersection.signal,
                                prev_phase=prev_phase,
                            )
                            last_reward = float(reward_result[0]) if isinstance(reward_result, tuple) else float(reward_result)
                    except Exception:
                        pass
                    cumulative_reward += last_reward
                else:
                    intersection.tick(dt=0.1, action=None)
                    last_reward = 0.0

            # ── Sample and buffer telemetry ──────────────────────────────────
            simulation_id = app.state.current_simulation_id
            if (
                simulation_id
                and not str(simulation_id).startswith("local-")
                and intersection.timestep % LOG_SAMPLE_INTERVAL == 0
                and intersection.timestep > 0
            ):
                should_flush = _buffer.add(simulation_id, intersection.timestep, intersection)
                if should_flush:
                    asyncio.create_task(_flush_buffer())

            target_duration = getattr(app.state, "target_duration", None)
            frame = build_frame(
                intersection=intersection,
                mode=mode,
                episode=episode,
                simulation_id=simulation_id,
                agent=agent,
                last_reward=last_reward,
                cumulative_reward=cumulative_reward,
                epsilon=0.0,
                last_action=last_action,
                was_exploring=was_exploring,
                obs=obs,
                target_duration=target_duration,
            )

            await manager.broadcast(frame.model_dump())

            # ── Check target duration auto-stop ──────────────────────────────
            run_start_step = getattr(app.state, "run_start_step", 0)
            if target_duration is not None and target_duration > 0:
                elapsed_sim_time = (intersection.timestep - run_start_step) * 0.1
                if elapsed_sim_time >= target_duration:
                    logger.info(
                        "Simulation target duration reached (%.1fs / %.1fs). Auto-stopping immediately.",
                        elapsed_sim_time, target_duration,
                    )
                    # 1. Immediately halt simulation state
                    app.state.sim_running = False
                    app.state.target_duration = None
                    try:
                        intersection.spawner.set_enabled(False)
                    except Exception:
                        pass

                    total_steps = intersection.timestep
                    duration_ms = int(total_steps * 0.1 * 1000)
                    duration_s = round(total_steps * 0.1, 1)
                    avg_wait = round(intersection.get_avg_wait_time(), 2)
                    passed = intersection.total_passed
                    peak_queue = max(intersection.get_queue_lengths().values(), default=0)
                    active_mode = getattr(app.state, "mode", "fixed")
                    active_model = getattr(app.state, "active_model_id", "FlowSync DQN")
                    active_eps = getattr(app.state, "active_model_episode", 300)
                    sim_id = app.state.current_simulation_id

                    # 2. IMMEDIATELY broadcast simulation_stopped to all connected clients without blocking
                    try:
                        await manager.broadcast({
                            "type": "simulation_stopped",
                            "reason": "duration_reached",
                            "simulation_id": sim_id,
                            "total_steps": total_steps,
                            "passed": passed,
                            "avg_wait": avg_wait,
                            "duration_seconds": target_duration,
                        })
                    except Exception as b_err:
                        logger.warning("Failed to broadcast duration_reached stop: %s", b_err)

                    # 3. Safely persist telemetry and session file (isolated in try/except)
                    try:
                        if sim_id and not str(sim_id).startswith("local-"):
                            try:
                                await _flush_buffer()
                            except Exception:
                                pass
                            try:
                                await asyncio.gather(
                                    asyncio.to_thread(
                                        supabase_service.update_simulation,
                                        sim_id,
                                        "completed",
                                        total_steps,
                                        duration_ms,
                                    ),
                                    asyncio.to_thread(
                                        supabase_service.save_performance_metric,
                                        sim_id,
                                        active_mode,
                                        avg_wait,
                                        passed,
                                        peak_queue,
                                        total_steps,
                                    ),
                                )
                            except Exception:
                                logger.exception("Failed to persist simulation metrics on duration stop")

                        # Save local session JSON
                        sessions_dir = Path(SESSION_DIR)
                        sessions_dir.mkdir(parents=True, exist_ok=True)
                        sess_key = sim_id or f"sim_{active_mode}_{int(time.time())}"
                        file_p = sessions_dir / f"{sess_key}.json"
                        movement_queues = intersection.get_movement_queues()
                        agg_counts = {k: int(v) for k, v in movement_queues.items()}
                        total_vehs = passed + sum(len(q) for q in intersection.lanes.values())

                        is_ft, ft_scen = _detect_finetune_info(active_model) if active_mode == "ai" else (False, None)

                        payload = {
                            "session_id": sess_key,
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "mode": active_mode,
                            "model_name": active_model if active_mode == "ai" else None,
                            "model_episodes": active_eps if active_mode == "ai" else None,
                            "is_finetuned": is_ft,
                            "finetune_scenario": ft_scen,
                            "throughput": passed,
                            "stats": {
                                "session_id": sess_key,
                                "mode": active_mode,
                                "model_name": active_model if active_mode == "ai" else None,
                                "model_episodes": active_eps if active_mode == "ai" else None,
                                "is_finetuned": is_ft,
                                "finetune_scenario": ft_scen,
                                "frame_count": total_steps,
                                "duration_s": duration_s,
                                "avg_fps": 10.0,
                                "total_detections": max(total_vehs, passed),
                                "throughput": passed,
                                "avg_wait_s": avg_wait,
                                "peak_queue": peak_queue,
                                "aggregate_counts": agg_counts,
                            },
                            "twin_data": {
                                "session_id": sess_key,
                                "total_frames_processed": total_steps,
                                "total_vehicles_detected": max(total_vehs, passed),
                                "video_duration_s": duration_s,
                                "total_passed": passed,
                                "arrivals": [],
                                "aggregate_counts": agg_counts,
                            },
                            "frames": [],
                        }
                        with open(file_p, "w", encoding="utf-8") as sf:
                            json.dump(payload, sf, indent=2)
                    except Exception as s_err:
                        logger.warning("Error saving session on duration stop: %s", s_err)

                    app.state.current_simulation_id = None
                    await asyncio.sleep(0.1)
                    continue

            await asyncio.sleep(sleep_duration)
    except asyncio.CancelledError:
        # Flush any remaining buffered rows before exiting
        await _flush_buffer()
    except Exception as fatal_err:
        logger.exception("[SimWS] Fatal error in _simulation_loop: %s", fatal_err)
    finally:
        app.state.sim_task = None


# ─── WebSocket Command Validation ─────────────────────────────────────────────

VALID_COMMANDS = {
    "start", "stop", "reset",
    "set_mode", "set_spawn_rate", "set_speed",
    "emergency_override", "manual_override",
    "run_timed_benchmark",
    "run_scenario_benchmark",
    "run_model_benchmark",
}

COMMAND_SCHEMAS = {
    "set_mode": {"mode": str},
    "set_spawn_rate": {"value": float},
    "set_speed": {"value": float},
    "emergency_override": {"lane": str},
    "manual_override": {"phase": int},
}


def validate_ws_command(data: dict) -> tuple[bool, str]:
    command = data.get("command")
    if command not in VALID_COMMANDS:
        return False, f"Unknown command: {command}"
    schema = COMMAND_SCHEMAS.get(command, {})
    for key, expected_type in schema.items():
        if key not in data:
            return False, f"Missing field: {key}"
        try:
            expected_type(data[key])
        except (ValueError, TypeError):
            return False, f"Invalid type for {key}"
    return True, ""


# ─── WebSocket handler ────────────────────────────────────────────────────────

async def simulation_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    app = websocket.app

    if not hasattr(app.state, "sim_task") or app.state.sim_task is None:
        app.state.sim_task = asyncio.create_task(_simulation_loop(app))

    try:
        while True:
            message = await websocket.receive_json()
            
            # Validate command
            is_valid, err_msg = validate_ws_command(message)
            if not is_valid:
                await websocket.send_json({"error": err_msg})
                continue

            command = message.get("command")

            if command == "start":
                # Parse optional target duration (seconds)
                duration_val = message.get("duration_seconds")
                if duration_val is not None:
                    try:
                        app.state.target_duration = max(5.0, min(3600.0, float(duration_val)))
                    except (ValueError, TypeError):
                        app.state.target_duration = None
                else:
                    app.state.target_duration = None

                logger.info(
                    "[SimWS] Starting simulation: mode=%s, target_duration=%s (raw=%s)",
                    getattr(app.state, "mode", "fixed"),
                    app.state.target_duration,
                    duration_val,
                )

                # Cancel any existing benchmark task if running
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                    app.state.benchmark_task = None

                # Clean reset of intersection to ensure a brand-new, consistent run
                app.state.sim_intersection.reset()
                app.state.run_start_step = 0
                app.state.sim_running = True
                
                try:
                    app.state.sim_intersection.spawner.set_enabled(True)
                    app.state.sim_intersection.spawner.seed_initial_vehicles(app.state.sim_intersection.lanes)
                except Exception:
                    pass

                if not hasattr(app.state, "sim_task") or app.state.sim_task is None:
                    app.state.sim_task = asyncio.create_task(_simulation_loop(app))

                try:
                    simulation_id = await asyncio.to_thread(
                        supabase_service.create_simulation,
                        app.state.mode,
                    )
                    app.state.current_simulation_id = simulation_id or f"local-{int(time.time())}"
                except Exception:
                    logger.exception("Failed to create simulation record")
                    app.state.current_simulation_id = f"local-{int(time.time())}"

            elif command == "stop":
                # 1. Immediately cancel any background benchmark task
                app.state.benchmark_running = False
                app.state.benchmark_cancelled = True
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                    app.state.benchmark_task = None

                # 2. Hard stop the simulation loop
                app.state.sim_running = False
                app.state.target_duration = None
                try:
                    app.state.sim_intersection.spawner.set_enabled(False)
                except Exception:
                    pass

                simulation_id = app.state.current_simulation_id
                intersection = app.state.sim_intersection
                total_steps = intersection.timestep
                duration_ms = int(total_steps * 0.1 * 1000)
                duration_s = round(total_steps * 0.1, 1)
                avg_wait = round(intersection.get_avg_wait_time(), 2)
                passed = intersection.total_passed
                peak_queue = max(intersection.get_queue_lengths().values(), default=0)
                active_mode = getattr(app.state, "mode", "fixed")
                active_model = getattr(app.state, "active_model_id", "FlowSync DQN")
                active_eps = getattr(app.state, "active_model_episode", 300)

                # Flush buffered telemetry rows to Supabase before closing
                if simulation_id and not str(simulation_id).startswith("local-"):
                    await _flush_buffer()

                    try:
                        await asyncio.gather(
                            asyncio.to_thread(
                                supabase_service.update_simulation,
                                simulation_id,
                                "completed",
                                total_steps,
                                duration_ms,
                            ),
                            asyncio.to_thread(
                                supabase_service.save_performance_metric,
                                simulation_id,
                                active_mode,
                                avg_wait,
                                passed,
                                peak_queue,
                                total_steps,
                            ),
                        )
                    except Exception:
                        logger.exception("Failed to persist simulation metrics on stop")

                # Auto-persist full session JSON locally for dashboard analytics and instant replay
                try:
                    sessions_dir = Path(SESSION_DIR)
                    sessions_dir.mkdir(parents=True, exist_ok=True)
                    sess_key = simulation_id or f"sim_{active_mode}_{int(time.time())}"
                    file_p = sessions_dir / f"{sess_key}.json"

                    movement_queues = intersection.get_movement_queues()
                    agg_counts = {k: int(v) for k, v in movement_queues.items()}
                    total_vehs = passed + sum(len(q) for q in intersection.lanes.values())

                    is_ft, ft_scen = _detect_finetune_info(active_model) if active_mode == "ai" else (False, None)

                    payload = {
                        "session_id": sess_key,
                        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "mode": active_mode,
                        "model_name": active_model if active_mode == "ai" else None,
                        "model_episodes": active_eps if active_mode == "ai" else None,
                        "is_finetuned": is_ft,
                        "finetune_scenario": ft_scen,
                        "throughput": passed,
                        "stats": {
                            "session_id": sess_key,
                            "mode": active_mode,
                            "model_name": active_model if active_mode == "ai" else None,
                            "model_episodes": active_eps if active_mode == "ai" else None,
                            "is_finetuned": is_ft,
                            "finetune_scenario": ft_scen,
                            "frame_count": total_steps,
                            "duration_s": duration_s,
                            "avg_fps": 10.0,
                            "total_detections": max(total_vehs, passed),
                            "throughput": passed,
                            "avg_wait_s": avg_wait,
                            "peak_queue": peak_queue,
                            "aggregate_counts": agg_counts,
                        },
                        "twin_data": {
                            "session_id": sess_key,
                            "total_frames_processed": total_steps,
                            "total_vehicles_detected": max(total_vehs, passed),
                            "video_duration_s": duration_s,
                            "total_passed": passed,
                            "arrivals": [],
                            "aggregate_counts": agg_counts,
                        },
                        "frames": [],
                    }
                    with open(file_p, "w", encoding="utf-8") as sf:
                        json.dump(payload, sf, indent=2)
                    logger.info("Saved simulation session file %s", file_p)
                except Exception as se:
                    logger.warning("Failed to write session file on stop: %s", se)

                app.state.current_simulation_id = None

                # Broadcast stopped confirmation to all connected clients
                try:
                    await manager.broadcast({
                        "type": "simulation_stopped",
                        "simulation_id": simulation_id,
                        "total_steps": total_steps,
                        "passed": passed,
                        "avg_wait": avg_wait,
                    })
                except Exception:
                    pass

            elif command == "reset":
                # 1. Cancel background benchmark task immediately
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                    app.state.benchmark_task = None

                # 2. Hard stop execution
                app.state.sim_running = False
                app.state.target_duration = None
                simulation_id = app.state.current_simulation_id
                if simulation_id and not str(simulation_id).startswith("local-"):
                    await _flush_buffer()

                # 3. Completely purge intersection state & all vehicle lists
                app.state.sim_intersection.reset()
                for queue in app.state.sim_intersection.lanes.values():
                    queue.clear()

                # 4. Spawner completely disabled — DO NOT re-seed vehicles
                try:
                    app.state.sim_intersection.spawner.set_enabled(False)
                except Exception:
                    pass

                app.state.current_simulation_id = None
                _buffer.traffic_rows.clear()
                _buffer.signal_rows.clear()
                app.state.sim_forecaster = ArrivalForecaster()

                # 5. Broadcast empty reset frame so 3D canvas and UI clear immediately
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
                    })
                except Exception as re:
                    logger.warning("Failed to broadcast reset empty frame: %s", re)

            elif command == "set_mode":
                mode = message.get("mode")
                if mode in ("fixed", "ai", "manual", "greedy"):
                    app.state.mode = mode

            elif command == "manual_override":
                phase = message.get("phase")
                if isinstance(phase, int) and 0 <= phase <= 3:
                    app.state.sim_intersection.signal.set_phase(phase)

            elif command == "set_spawn_rate":
                value = message.get("value")
                # Clamp between 0.1 and 5.0 to allow heavy rush hour / 500+ vehicle stress testing
                spawn_rate = max(0.1, min(5.0, float(value)))
                app.state.sim_intersection.set_spawn_rate(spawn_rate)

            elif command == "set_speed":
                value = message.get("value", 1.0)
                # Allow speeds up to 16.0x for rapid evaluation
                speed = max(0.25, min(16.0, float(value)))
                app.state.sim_speed = speed

            elif command == "emergency_override":
                lane = message.get("lane")
                if lane in ("north", "south", "east", "west"):
                    app.state.sim_intersection.trigger_emergency_override(lane)

            elif command == "run_timed_benchmark":
                duration_seconds = int(message.get("duration_seconds", 30))
                scenario_counts = message.get("scenario_counts", None)
                arrivals = message.get("arrivals", None)
                modes = message.get("modes", ["ai", "fixed", "greedy"])
                model_id = message.get("model_id")
                model_episode = message.get("model_episode")
                if model_episode is not None:
                    try:
                        model_episode = int(model_episode)
                    except Exception:
                        model_episode = None
                # Clamp duration between 10 and 600 seconds
                duration_seconds = max(10, min(600, duration_seconds))
                app.state.sim_running = False
                app.state.benchmark_running = True
                app.state.benchmark_cancelled = False
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                app.state.benchmark_task = asyncio.create_task(
                    _run_timed_benchmark(
                        app, websocket, duration_seconds, scenario_counts, modes, arrivals, model_id, model_episode
                    )
                )

            elif command == "run_scenario_benchmark":
                _sc_id   = str(message.get("scenario_id", ""))
                _seed    = int(message.get("seed", 42))
                _lambda  = float(message.get("spawn_lambda", 0.5))
                _dur     = max(10, min(600, int(message.get("duration_seconds", 60))))
                _model   = str(message.get("model_id", getattr(app.state, "active_model_id", "")))
                _ep      = int(message.get("model_episode", getattr(app.state, "active_model_episode", 0)))
                if not _sc_id:
                    try:
                        await websocket.send_json({"type": "error", "code": "MISSING_SCENARIO_ID", "message": "scenario_id is required"})
                    except Exception:
                        pass
                else:
                    app.state.sim_running = False
                    app.state.benchmark_running = True
                    app.state.benchmark_cancelled = False
                    if getattr(app.state, "benchmark_task", None) is not None:
                        app.state.benchmark_task.cancel()
                    app.state.benchmark_task = asyncio.create_task(
                        _run_scenario_benchmark(app, websocket, _sc_id, _seed, _lambda, _dur, _model, _ep)
                    )

            elif command == "run_model_benchmark":
                duration_seconds = int(message.get("duration_seconds", 30))
                models_to_test = message.get("models", [])
                scenario_counts = message.get("scenario_counts", None)
                seed = message.get("seed", None)
                if seed is not None:
                    try:
                        seed = int(seed)
                    except Exception:
                        seed = None
                duration_seconds = max(10, min(600, duration_seconds))
                app.state.sim_running = False
                app.state.benchmark_running = True
                app.state.benchmark_cancelled = False
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                app.state.benchmark_task = asyncio.create_task(
                    _run_model_benchmark(
                        app, websocket, duration_seconds, models_to_test, scenario_counts, seed
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if not manager.active_connections:
            app.state.sim_running = False
            try:
                app.state.sim_intersection.spawner.set_enabled(False)
            except Exception:
                pass

            simulation_id = app.state.current_simulation_id
            if simulation_id and not str(simulation_id).startswith("local-"):
                intersection = app.state.sim_intersection
                total_steps = intersection.timestep
                duration_ms = int(total_steps * 0.1 * 1000)

                # Flush buffered rows before closing the simulation
                await _flush_buffer()

                try:
                    await asyncio.gather(
                        asyncio.to_thread(
                            supabase_service.update_simulation,
                            simulation_id,
                            "stopped",
                            total_steps,
                            duration_ms,
                        ),
                        asyncio.to_thread(
                            supabase_service.save_performance_metric,
                            simulation_id,
                            app.state.mode,
                            intersection.get_avg_wait_time(),
                            intersection.total_passed,
                            max(intersection.get_queue_lengths().values(), default=0),
                            total_steps,
                        ),
                    )
                except Exception:
                    logger.exception("Failed to persist simulation metrics on disconnect")

                app.state.current_simulation_id = None

            task = app.state.sim_task
            if task and not task.done():
                task.cancel()

