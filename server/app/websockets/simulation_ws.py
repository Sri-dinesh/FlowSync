import asyncio
import logging
import time

try:
    import ujson as json
except ImportError:  # pragma: no cover - fallback for missing optional dep
    import json
from typing import List

from fastapi import WebSocket, WebSocketDisconnect

from ..schemas.simulation_schema import build_frame
from ..services import supabase_service


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
logger = logging.getLogger(__name__)


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

            frame = build_frame(intersection, mode, reward, episode)
            await manager.broadcast(frame.model_dump())
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        app_state["sim_task"] = None


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
                # enable spawner to allow vehicle arrivals
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
                    except Exception:
                        logger.exception("Failed to create simulation record")
                        app_state["current_simulation_id"] = f"local-{int(time.time())}"
            elif command == "stop":
                app_state["sim_running"] = False
                # disable spawner so no new vehicles are introduced while stopped
                try:
                    app_state["intersection"].spawner.set_enabled(False)
                except Exception:
                    pass
                simulation_id = app_state.get("current_simulation_id")
                if simulation_id and not str(simulation_id).startswith("local-"):
                    intersection = app_state["intersection"]
                    total_steps = intersection.timestep
                    duration_ms = int(total_steps * 0.1 * 1000)
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
                                app_state.get("mode", "fixed"),
                                intersection.get_avg_wait_time(),
                                intersection.total_passed,
                            ),
                        )
                    except Exception:
                        logger.exception("Failed to persist simulation metrics")
                    app_state["current_simulation_id"] = None
            elif command == "reset":
                app_state["intersection"].reset()
                app_state["sim_running"] = False
                app_state["current_simulation_id"] = None
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
