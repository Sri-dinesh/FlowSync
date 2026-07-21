"""
City Simulation WebSocket handler — /ws/city

Manages the 2×2 city grid simulation loop at 10 Hz.
Supports Fixed / Greedy / AI (shared-policy DQN) control modes.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import ujson as json
except ImportError:
    import json

from fastapi import WebSocket, WebSocketDisconnect

from ..schemas.city_schema import build_city_frame
from ..simulation.city_network import CityNetwork
from ..simulation.city_spawner import CitySpawner

logger = logging.getLogger(__name__)


class CityConnectionManager:
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


city_manager = CityConnectionManager()


# ── Comparison test state ─────────────────────────────────────────────────────

class ComparisonTestState:
    def __init__(self) -> None:
        self.running: bool = False
        self.current_mode_idx: int = 0
        self.modes = ["fixed", "greedy", "ai"]
        self.duration_per_mode: int = 30   # seconds
        self.results: Dict[str, Dict] = {}
        self.started_at: float = 0.0
        self.snapshots: Dict[str, List] = {}

    def start(self) -> None:
        self.running = True
        self.current_mode_idx = 0
        self.results = {}
        self.snapshots = {}
        self.started_at = time.time()

    def current_mode(self) -> str:
        return self.modes[self.current_mode_idx]

    def elapsed(self) -> float:
        return time.time() - self.started_at

    def should_advance(self) -> bool:
        return self.elapsed() >= self.duration_per_mode

    def record_snapshot(self, city_metrics: dict) -> None:
        mode = self.current_mode()
        if mode not in self.snapshots:
            self.snapshots[mode] = []
        self.snapshots[mode].append({
            "avg_wait": city_metrics["avg_wait_time"],
            "throughput": city_metrics["total_throughput"],
        })

    def advance(self) -> bool:
        """Move to next mode. Returns True if all modes done."""
        mode = self.current_mode()
        snaps = self.snapshots.get(mode, [])
        if snaps:
            avg_waits = [s["avg_wait"] for s in snaps]
            throughputs = [s["throughput"] for s in snaps]
            self.results[mode] = {
                "avg_wait_time": round(sum(avg_waits) / len(avg_waits), 2),
                "throughput": throughputs[-1] if throughputs else 0,
            }
        self.current_mode_idx += 1
        self.started_at = time.time()
        return self.current_mode_idx >= len(self.modes)

    def finish(self) -> Dict:
        self.running = False
        return self.results


comparison_state = ComparisonTestState()


# ── City simulation loop ──────────────────────────────────────────────────────

async def _city_simulation_loop(app) -> None:
    try:
        while True:
            if not getattr(app.state, "city_running", False):
                await asyncio.sleep(0.1)
                continue

            city_net: CityNetwork = app.state.city_network
            city_spawner: CitySpawner = app.state.city_spawner
            agent = app.state.sim_agent  # shared policy — same agent as single-intersection

            # Determine mode
            if comparison_state.running:
                mode = comparison_state.current_mode()
                # Sample metrics for comparison
                if city_net.timestep % 10 == 0:
                    raw = city_net.get_city_metrics()
                    comparison_state.record_snapshot(raw)
                # Advance comparison phases
                if comparison_state.should_advance():
                    done = comparison_state.advance()
                    if done:
                        results = comparison_state.finish()
                        # Broadcast comparison results
                        await city_manager.broadcast({
                            "frame_type": "comparison_results",
                            "results": results,
                        })
                        app.state.city_mode = "fixed"
                        city_net.reset()
                        city_spawner.set_enabled(True)
                        continue
                    else:
                        # Reset for next mode
                        city_net.reset()
                        city_spawner.set_enabled(True)
                        await city_manager.broadcast({
                            "frame_type": "comparison_phase",
                            "current_mode": comparison_state.current_mode(),
                            "elapsed": 0,
                            "total": comparison_state.duration_per_mode,
                        })
            else:
                mode = getattr(app.state, "city_mode", "fixed")

            # Spawn new vehicles
            city_spawner.spawn(dt=0.1, intersections=city_net.intersections)

            # Tick city network
            city_net.tick(dt=0.1, mode=mode, shared_agent=agent if mode == "ai" else None)

            # Build and broadcast frame
            frame = build_city_frame(
                city_network=city_net,
                mode=mode,
                shared_agent=agent if mode == "ai" else None,
            )
            payload = frame.model_dump()

            # Inject comparison progress if running
            if comparison_state.running:
                payload["comparison_progress"] = {
                    "running": True,
                    "current_mode": comparison_state.current_mode(),
                    "elapsed": round(comparison_state.elapsed(), 1),
                    "total": comparison_state.duration_per_mode,
                    "mode_index": comparison_state.current_mode_idx,
                    "total_modes": len(comparison_state.modes),
                }
            else:
                payload["comparison_progress"] = {"running": False}

            await city_manager.broadcast(payload)
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        pass
    finally:
        app.state.city_task = None


# ── Command validation ────────────────────────────────────────────────────────

VALID_CITY_COMMANDS = {"start", "stop", "reset", "set_mode", "set_spawn_rate", "run_comparison"}

CITY_COMMAND_SCHEMAS = {
    "set_mode": {"mode": str},
    "set_spawn_rate": {"value": float},
}


def _validate_city_command(data: dict) -> tuple[bool, str]:
    command = data.get("command")
    if command not in VALID_CITY_COMMANDS:
        return False, f"Unknown command: {command}"
    schema = CITY_COMMAND_SCHEMAS.get(command, {})
    for key, expected_type in schema.items():
        if key not in data:
            return False, f"Missing field: {key}"
        try:
            expected_type(data[key])
        except (ValueError, TypeError):
            return False, f"Invalid type for {key}"
    return True, ""


# ── WebSocket handler ─────────────────────────────────────────────────────────

async def city_socket(websocket: WebSocket) -> None:
    await city_manager.connect(websocket)
    app = websocket.app

    # Lazy-init city state
    if not hasattr(app.state, "city_network") or app.state.city_network is None:
        app.state.city_network = CityNetwork()
        app.state.city_spawner = CitySpawner(lambda_rate=0.3)
        app.state.city_mode = "fixed"
        app.state.city_running = False
        app.state.city_task = None

    # Ensure background loop is running
    if not hasattr(app.state, "city_task") or app.state.city_task is None:
        app.state.city_task = asyncio.create_task(_city_simulation_loop(app))

    try:
        while True:
            message = await websocket.receive_json()

            is_valid, err_msg = _validate_city_command(message)
            if not is_valid:
                await websocket.send_json({"error": err_msg})
                continue

            command = message.get("command")

            if command == "start":
                app.state.city_running = True
                app.state.city_spawner.set_enabled(True)

            elif command == "stop":
                app.state.city_running = False
                app.state.city_spawner.set_enabled(False)

            elif command == "reset":
                app.state.city_running = False
                app.state.city_spawner.set_enabled(False)
                app.state.city_network.reset()
                comparison_state.running = False
                # Broadcast the cleared frame immediately
                frame = build_city_frame(
                    city_network=app.state.city_network,
                    mode=getattr(app.state, "city_mode", "fixed"),
                    shared_agent=app.state.sim_agent if getattr(app.state, "city_mode", "fixed") == "ai" else None,
                )
                payload = frame.model_dump()
                payload["comparison_progress"] = {"running": False}
                await city_manager.broadcast(payload)

            elif command == "set_mode":
                mode = message.get("mode")
                if mode in ("fixed", "greedy", "ai"):
                    app.state.city_mode = mode

            elif command == "set_spawn_rate":
                value = message.get("value")
                rate = max(0.05, min(2.0, float(value)))
                app.state.city_spawner.set_rate(rate)
                app.state.city_network.set_spawn_rate(rate)

            elif command == "run_comparison":
                if not comparison_state.running:
                    app.state.city_network.reset()
                    app.state.city_spawner.set_enabled(True)
                    app.state.city_running = True
                    comparison_state.start()
                    await websocket.send_json({
                        "frame_type": "comparison_started",
                        "modes": comparison_state.modes,
                        "duration_per_mode": comparison_state.duration_per_mode,
                    })

    except WebSocketDisconnect:
        city_manager.disconnect(websocket)
        if not city_manager.active_connections:
            app.state.city_running = False
            if hasattr(app.state, "city_spawner"):
                app.state.city_spawner.set_enabled(False)
            task = getattr(app.state, "city_task", None)
            if task and not task.done():
                task.cancel()
