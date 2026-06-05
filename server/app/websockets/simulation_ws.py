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


# ─── Simulation loop ──────────────────────────────────────────────────────────

async def _simulation_loop(app_state: dict) -> None:
    try:
        while True:
            if not app_state.get("sim_running"):
                await asyncio.sleep(0.1)
                continue

            intersection = app_state["intersection"]
            mode = app_state["mode"]
            reward = 0.0
            trainer = app_state.get("trainer")
            episode = trainer.current_episode if trainer else 0

            if mode == "fixed":
                intersection.tick(dt=0.1, action=None)
            else:
                env = app_state["env"]
                agent = app_state["agent"]
                state = env._get_obs()
                action = agent.select_action(state, epsilon=0.0)
                _, reward, _, _, _ = env.step(action)

            # ── Sample and buffer telemetry ──────────────────────────────────
            simulation_id = app_state.get("current_simulation_id")
            if (
                simulation_id
                and not str(simulation_id).startswith("local-")
                and intersection.timestep % LOG_SAMPLE_INTERVAL == 0
                and intersection.timestep > 0
            ):
                should_flush = _buffer.add(simulation_id, intersection.timestep, intersection)
                if should_flush:
                    asyncio.create_task(_flush_buffer())

            frame = build_frame(intersection, mode, reward, episode)
            await manager.broadcast(frame.model_dump())
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        # Flush any remaining buffered rows before exiting
        await _flush_buffer()
    finally:
        app_state["sim_task"] = None


# ─── WebSocket handler ────────────────────────────────────────────────────────

async def simulation_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    app_state = websocket.scope["app"].state.app_state

    if app_state.get("sim_task") is None:
        app_state["sim_task"] = asyncio.create_task(_simulation_loop(app_state))

    try:
        while True:
            message = await websocket.receive_json()
            command = message.get("command")

            if command == "start":
                app_state["sim_running"] = True
                try:
                    app_state["intersection"].spawner.set_enabled(True)
                except Exception:
                    pass

                if not app_state.get("current_simulation_id"):
                    try:
                        simulation_id = await asyncio.to_thread(
                            supabase_service.create_simulation,
                            app_state.get("mode", "fixed"),
                        )
                        if simulation_id:
                            app_state["current_simulation_id"] = simulation_id
                        else:
                            logger.error("create_simulation returned empty id")
                    except Exception:
                        logger.exception("Failed to create simulation record")
                        app_state["current_simulation_id"] = f"local-{int(time.time())}"

            elif command == "stop":
                app_state["sim_running"] = False
                try:
                    app_state["intersection"].spawner.set_enabled(False)
                except Exception:
                    pass

                simulation_id = app_state.get("current_simulation_id")
                if simulation_id and not str(simulation_id).startswith("local-"):
                    intersection = app_state["intersection"]
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
                                app_state.get("mode", "fixed"),
                                intersection.get_avg_wait_time(),
                                intersection.total_passed,
                            ),
                        )
                    except Exception:
                        logger.exception("Failed to persist simulation metrics on stop")

                    app_state["current_simulation_id"] = None

            elif command == "reset":
                simulation_id = app_state.get("current_simulation_id")
                if simulation_id and not str(simulation_id).startswith("local-"):
                    await _flush_buffer()
                app_state["intersection"].reset()
                app_state["sim_running"] = False
                app_state["current_simulation_id"] = None
                _buffer.traffic_rows.clear()
                _buffer.signal_rows.clear()
                try:
                    app_state["intersection"].spawner.set_enabled(False)
                except Exception:
                    pass

            elif command == "set_mode":
                mode = message.get("mode")
                if mode in ("fixed", "ai"):
                    app_state["mode"] = mode

            elif command == "set_spawn_rate":
                value = message.get("value")
                try:
                    rate = float(value)
                except (TypeError, ValueError):
                    continue
                app_state["intersection"].set_spawn_rate(rate)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if not manager.active_connections:
            app_state["sim_running"] = False
            task = app_state.get("sim_task")
            if task and not task.done():
                task.cancel()
