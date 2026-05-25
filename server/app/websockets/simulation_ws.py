import asyncio
from typing import List

from fastapi import WebSocket, WebSocketDisconnect

from ..schemas.simulation_schema import build_frame


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
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


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
            elif command == "stop":
                app_state["sim_running"] = False
            elif command == "reset":
                app_state["intersection"].reset()
            elif command == "set_mode":
                mode = message.get("mode")
                if mode in ("fixed", "ai"):
                    app_state["mode"] = mode
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if not manager.active_connections:
            app_state["sim_running"] = False
            task = app_state.get("sim_task")
            if task and not task.done():
                task.cancel()
