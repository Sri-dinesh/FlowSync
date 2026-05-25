import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from .simulation_ws import manager


async def broadcast_training_metric(data: dict) -> None:
    await manager.broadcast(data)


async def training_socket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
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
                trainer = app_state["trainer"]

                if not trainer.is_training:
                    task = asyncio.create_task(
                        trainer.train(simulation_id or "", num_episodes)
                    )
                    app_state["training_task"] = task
            elif command == "stop_training":
                app_state["trainer"].stop()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
