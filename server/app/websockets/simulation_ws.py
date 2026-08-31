"""
Simulation WebSocket handler.

Persistence strategy for traffic_logs and signal_states:
  - Sampled every LOG_SAMPLE_INTERVAL ticks (default 50 = every 5 s at 10 Hz)
    to avoid flooding the DB at 10 rows/second.
  - Rows are flushed in bulk every FLUSH_INTERVAL ticks to reduce round-trips.
  - Neither table is written on every tick — that would produce ~36 000 rows/hour.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

import numpy as np
try:
    import ujson as json
except ImportError:
    import json

from fastapi import WebSocket, WebSocketDisconnect

from ..schemas.simulation_schema import build_frame
from ..services import supabase_service

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


# ─── Timed Benchmark ─────────────────────────────────────────────────────────

async def _run_timed_benchmark(
    app,
    websocket: WebSocket,
    duration_seconds: int,
    scenario_counts: dict | None,
    modes: list[str],
    arrivals: list[dict] | None = None,
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
    TICK_SLEEP = 0.1       # wall-clock seconds between ticks (real-time 10 Hz)
    PHASE_DIRS  = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
    PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}

    results: dict = {}
    prev_mode    = getattr(app.state, "mode", "fixed")
    prev_running = getattr(app.state, "sim_running", False)

    # Pause normal simulation loop so both don't fight over the intersection
    app.state.sim_running = False
    if getattr(app.state, "sim_task", None) is not None:
        app.state.sim_task.cancel()
        try:
            await app.state.sim_task
        except Exception:
            pass
    await asyncio.sleep(0.2)

    # Generate a synchronized CRN seed for this benchmark session
    import random
    benchmark_seed = random.randint(1, 1_000_000)
    is_realworld = bool(arrivals and len(arrivals) > 0)
    total_vehicles_to_clear = len(arrivals) if is_realworld else 0
    sorted_arrivals = sorted(arrivals, key=lambda a: a.get("time_s", 0.0)) if is_realworld else []

    try:
        for mode_idx, mode in enumerate(modes):
            intersection = app.state.sim_intersection
            agent        = app.state.sim_agent

            # ── Setup ──────────────────────────────────────────────────────
            intersection.reset()
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
                # Real-world mode runs until all vehicles clear (or safety timeout e.g. 300s)
                max_timeout = max(90.0, total_vehicles_to_clear * 6.0)
                deadline = asyncio.get_event_loop().time() + max_timeout
            else:
                deadline = asyncio.get_event_loop().time() + duration_seconds

            while True:
                # Check exit condition
                now = asyncio.get_event_loop().time()
                if now >= deadline:
                    break
                if is_realworld and len(pending_arrivals) == 0 and intersection.total_passed >= total_vehicles_to_clear:
                    # All recorded vehicles have cleared the intersection!
                    break

                tick_start = now
                tick_count += 1
                sim_time += TICK_DT

                # ── Chronological vehicle arrivals (Real-World Replay) ───────
                if is_realworld:
                    while pending_arrivals and pending_arrivals[0].get("time_s", 0.0) <= sim_time:
                        arr = pending_arrivals.pop(0)
                        dir_name = arr.get("lane", "north")
                        turn = arr.get("turn", "straight")
                        lane_key = f"{dir_name}_{turn}"
                        if lane_key in intersection.lanes and len(intersection.lanes[lane_key]) < 12:
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
                    best_phase   = max(phase_counts, key=lambda p: phase_counts[p])
                    action       = best_phase if signal.can_switch_phase else signal.current_phase
                    last_action  = action
                    intersection.tick(dt=TICK_DT, action=action)
                elif mode == "ai" and agent is not None:
                    obs    = _build_obs_from_intersection(intersection)
                    action = agent.select_action(obs, epsilon=0.0)
                    last_action  = action
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
                    mode_elapsed = round(sim_time, 1)
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
                            "passed_count": intersection.total_passed,
                        })
                    except Exception:
                        pass

                # ── Real-time pacing ───────────────────────────────────────
                elapsed = asyncio.get_event_loop().time() - tick_start
                sleep_t = max(0.0, TICK_SLEEP - elapsed)
                await asyncio.sleep(sleep_t)

            # ── Collect results ────────────────────────────────────────────
            queue_lengths = intersection.get_queue_lengths()
            final_time = round(sim_time, 1)
            results[mode] = {
                "total_passed":    intersection.total_passed,
                "total_vehicles":  total_vehicles_to_clear if is_realworld else intersection.total_passed,
                "avg_wait_time":   round(intersection.get_avg_wait_time(), 2),
                "max_queue":       max(queue_lengths.values(), default=0),
                "duration_seconds": final_time if is_realworld else duration_seconds,
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
                    "elapsed":        final_time if is_realworld else duration_seconds,
                    "duration_seconds": final_time if is_realworld else duration_seconds,
                    "benchmark_seed": benchmark_seed,
                    "is_realworld":   is_realworld,
                    "total_vehicles": total_vehicles_to_clear,
                    "spawned_count":  spawned_count,
                    "passed_count":   intersection.total_passed,
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

        # Winner: lowest avg wait time, fastest clearance time as tiebreaker
        def _score_mode(m):
            r = results[m]
            return (-r.get("avg_wait_time", 0.0), -r.get("clearance_time", 0.0), r.get("total_passed", 0))

        winner = max(results.keys(), key=_score_mode) if results else None

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
                "is_realworld":     is_realworld,
                "total_vehicles":   total_vehicles_to_clear,
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
        app.state.sim_running = prev_running
        app.state.sim_intersection.reset()
        try:
            app.state.sim_intersection.spawner.set_seed(None)
        except Exception:
            pass


# ─── Simulation helper ────────────────────────────────────────────────────────

def _build_obs_from_intersection(intersection) -> np.ndarray:
    movement_queues = intersection.get_movement_queues()
    signal = intersection.signal
    MAX_CAP = 10.0

    movements = [
        movement_queues.get("north_straight", 0) / MAX_CAP,
        movement_queues.get("north_left", 0) / MAX_CAP,
        movement_queues.get("north_right", 0) / MAX_CAP,
        movement_queues.get("south_straight", 0) / MAX_CAP,
        movement_queues.get("south_left", 0) / MAX_CAP,
        movement_queues.get("south_right", 0) / MAX_CAP,
        movement_queues.get("east_straight", 0) / MAX_CAP,
        movement_queues.get("east_left", 0) / MAX_CAP,
        movement_queues.get("east_right", 0) / MAX_CAP,
        movement_queues.get("west_straight", 0) / MAX_CAP,
        movement_queues.get("west_left", 0) / MAX_CAP,
        movement_queues.get("west_right", 0) / MAX_CAP,
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

    obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv_norm]
    return np.array(obs, dtype=np.float32)


# ─── Simulation loop ──────────────────────────────────────────────────────────

async def _simulation_loop(app) -> None:
    cumulative_reward = 0.0
    last_reward = 0.0
    last_action = 0
    was_exploring = False
    obs = None

    try:
        while True:
            if not app.state.sim_running:
                await asyncio.sleep(0.1)
                continue

            intersection = app.state.sim_intersection
            mode = app.state.mode
            trainer = app.state.trainer
            episode = trainer.current_episode if trainer else 0
            agent = app.state.sim_agent

            if mode in ("fixed", "manual"):
                intersection.tick(dt=0.1, action=None, is_manual=(mode == "manual"))
                last_reward = 0.0
            elif mode == "greedy":
                # Greedy: always serve the phase with the highest total queue count.
                # Respects min_green (via signal.can_switch_phase) to prevent flickering.
                signal = intersection.signal
                queues = intersection.get_movement_queues()
                PHASE_DIRS = {
                    0: ["north", "south"],
                    1: ["east", "west"],
                    2: ["north", "south"],
                    3: ["east", "west"],
                }
                PHASE_TURNS = {
                    0: ["straight", "right"],
                    1: ["straight", "right"],
                    2: ["left"],
                    3: ["left"],
                }
                phase_counts = {}
                for ph in range(4):
                    count = sum(
                        queues.get(f"{d}_{t}", 0)
                        for d in PHASE_DIRS[ph]
                        for t in PHASE_TURNS[ph]
                    )
                    phase_counts[ph] = count
                best_phase = max(phase_counts, key=lambda p: phase_counts[p])
                # Only inject action if we can switch (respects MIN_GREEN_TIME)
                greedy_action = best_phase if signal.can_switch_phase else signal.current_phase
                intersection.tick(dt=0.1, action=greedy_action)
                last_reward = 0.0
            elif mode == "ai":
                obs = _build_obs_from_intersection(intersection)
                action = agent.select_action(obs, epsilon=0.0)
                last_action = action

                prev_pressures = app.state.training_env._compute_movement_pressures(intersection)
                prev_passed = intersection.total_passed
                prev_phase = intersection.signal.current_phase

                intersection.tick(dt=0.1, action=action)

                curr_pressures = app.state.training_env._compute_movement_pressures(intersection)
                curr_passed = intersection.total_passed
                vehicles_passed = curr_passed - prev_passed
                phase_changed = (action != prev_phase) and (intersection.signal.color.value == "green")

                # Compute reward using the training_env helper
                last_reward = app.state.training_env.compute_reward(
                    prev_pressures=prev_pressures,
                    curr_pressures=curr_pressures,
                    vehicles_passed=vehicles_passed,
                    phase_changed=phase_changed,
                    signal=intersection.signal,
                    prev_phase=prev_phase,
                )
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
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        # Flush any remaining buffered rows before exiting
        await _flush_buffer()
    finally:
        app.state.sim_task = None


# ─── WebSocket Command Validation ─────────────────────────────────────────────

VALID_COMMANDS = {
    "start", "stop", "reset",
    "set_mode", "set_spawn_rate",
    "emergency_override", "manual_override",
    "run_timed_benchmark",
}

COMMAND_SCHEMAS = {
    "set_mode": {"mode": str},
    "set_spawn_rate": {"value": float},
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
                app.state.sim_running = True
                if not hasattr(app.state, "sim_task") or app.state.sim_task is None:
                    app.state.sim_task = asyncio.create_task(_simulation_loop(app))
                    
                try:
                    app.state.sim_intersection.spawner.set_enabled(True)
                except Exception:
                    pass

                if not app.state.current_simulation_id:
                    try:
                        simulation_id = await asyncio.to_thread(
                            supabase_service.create_simulation,
                            app.state.mode,
                        )
                        if simulation_id:
                            app.state.current_simulation_id = simulation_id
                        else:
                            logger.error("create_simulation returned empty id")
                    except Exception:
                        logger.exception("Failed to create simulation record")
                        app.state.current_simulation_id = f"local-{int(time.time())}"

            elif command == "stop":
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                    app.state.benchmark_task = None
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
                                "completed",
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
                        logger.exception("Failed to persist simulation metrics on stop")

                    app.state.current_simulation_id = None

            elif command == "reset":
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                    app.state.benchmark_task = None
                simulation_id = app.state.current_simulation_id
                if simulation_id and not str(simulation_id).startswith("local-"):
                    await _flush_buffer()
                app.state.sim_intersection.reset()
                app.state.sim_running = False
                app.state.current_simulation_id = None
                _buffer.traffic_rows.clear()
                _buffer.signal_rows.clear()
                try:
                    app.state.sim_intersection.spawner.set_enabled(False)
                except Exception:
                    pass

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
                # Clamp between 0.1 and 1.0 (Fix 7.5)
                spawn_rate = max(0.1, min(1.0, float(value)))
                app.state.sim_intersection.set_spawn_rate(spawn_rate)

            elif command == "emergency_override":
                lane = message.get("lane")
                if lane in ("north", "south", "east", "west"):
                    app.state.sim_intersection.trigger_emergency_override(lane)

            elif command == "run_timed_benchmark":
                duration_seconds = int(message.get("duration_seconds", 30))
                scenario_counts = message.get("scenario_counts", None)
                arrivals = message.get("arrivals", None)
                modes = message.get("modes", ["fixed", "greedy", "ai"])
                # Clamp duration between 10 and 600 seconds
                duration_seconds = max(10, min(600, duration_seconds))
                if getattr(app.state, "benchmark_task", None) is not None:
                    app.state.benchmark_task.cancel()
                app.state.benchmark_task = asyncio.create_task(
                    _run_timed_benchmark(app, websocket, duration_seconds, scenario_counts, modes, arrivals)
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

