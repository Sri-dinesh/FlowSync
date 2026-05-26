import asyncio
import time
from typing import List

from fastapi import WebSocket, WebSocketDisconnect
try:
    import ujson as json
except ImportError:  # pragma: no cover - fallback for missing optional dep
    import json

from ..services import supabase_service

class TrainingConnectionManager:
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


training_manager = TrainingConnectionManager()


async def broadcast_training_metric(data: dict) -> None:
    await training_manager.broadcast(data)


async def training_socket(websocket: WebSocket) -> None:
    await training_manager.connect(websocket)
    app_state = websocket.scope["app"].state.app_state

    try:
        while True:
            message = await websocket.receive_json()
            command = message.get("command")

            if command == "start_training":
                num_episodes = int(message.get("num_episodes", 500))
                simulation_id = message.get("simulation_id") or app_state.get(
                    "current_simulation_id"
                )
                if not simulation_id:
                    try:
                        simulation_id = await asyncio.to_thread(
                            supabase_service.create_simulation, "ai"
                        )
                        if simulation_id:
                            app_state["current_simulation_id"] = simulation_id
                    except Exception:
                        simulation_id = f"local-{int(time.time())}"
                trainer = app_state["trainer"]

                if not trainer.is_training:
                    task = asyncio.create_task(
                        trainer.train(simulation_id or "", num_episodes)
                    )
                    app_state["training_task"] = task
            elif command == "stop_training":
                app_state["trainer"].stop()
    except WebSocketDisconnect:
        training_manager.disconnect(websocket)
