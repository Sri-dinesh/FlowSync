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
    pressure_norm = 0.0   # simplified for inference
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
            elif mode == "ai":
                obs = _build_obs_from_intersection(intersection)
                action = agent.select_action(obs, epsilon=0.0)
                last_action = action

                prev_pressures = app.state.training_env._compute_movement_pressures()
                prev_passed = intersection.total_passed
                prev_phase = intersection.signal.current_phase

                intersection.tick(dt=0.1, action=action)

                curr_pressures = app.state.training_env._compute_movement_pressures()
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
            
            import os
            # Log frames if in local/development environment
            if os.getenv("ENV") != "production" and os.getenv("FASTAPI_ENV") != "production":
                print(f"[SimWS Send Data] Timestep {intersection.timestep}: {frame.model_dump()}")
                
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
    "emergency_override", "manual_override"
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

            elif command == "pause":
                app.state.sim_running = False
                try:
                    app.state.sim_intersection.spawner.set_enabled(False)
                except Exception:
                    pass

            elif command == "stop":
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
                if mode in ("fixed", "ai", "manual"):
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

