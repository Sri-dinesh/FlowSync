import asyncio
import logging
from typing import List

from fastapi import WebSocket, WebSocketDisconnect
try:
    import ujson as json
except ImportError:  # pragma: no cover - fallback for missing optional dep
    import json

from ..services import supabase_service


logger = logging.getLogger(__name__)


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


async def _run_training_task(trainer, *args, **kwargs) -> None:
    """Run training without losing background-task exceptions."""
    try:
        await trainer.train(*args, **kwargs)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        trainer.is_training = False
        logger.exception("Training task failed")
        await broadcast_training_metric({
            "type": "training_error",
            "is_training": False,
            "message": str(exc) or exc.__class__.__name__,
        })


async def training_socket(websocket: WebSocket) -> None:
    await training_manager.connect(websocket)
    app = websocket.app

    # Send current status immediately on connect
    trainer = app.state.trainer
    await websocket.send_json(trainer.get_status())

    try:
        while True:
            message = await websocket.receive_json()
            command = message.get("command")

            if command == "start_training":
                await websocket.send_json({
                    "type": "training_request_received",
                    "is_training": True,
                    "message": "Training request received; preparing the run...",
                })
                num_episodes = int(message.get("num_episodes", 500))
                simulation_id = message.get("simulation_id")
                resume_model_id = message.get("resume_model_id")
                resume_episode = message.get("resume_episode")
                is_finetune = message.get("mode") == "finetune" or bool(message.get("is_finetune", False))
                finetune_scenario = message.get("finetune_scenario", "rush_hour")
                finetune_lr = float(message.get("finetune_lr", 1e-4))
                finetune_epsilon = float(message.get("finetune_epsilon", 0.25))
                custom_profile = message.get("custom_profile")

                if resume_episode is not None:
                    try:
                        resume_episode = int(resume_episode)
                    except Exception:
                        resume_episode = None

                if is_finetune:
                    base_id = resume_model_id.split(":")[0] if resume_model_id and ":" in resume_model_id else (resume_model_id or "base")
                    if finetune_scenario == "custom" and custom_profile and custom_profile.get("name"):
                        custom_slug = custom_profile["name"].lower().strip().replace(" ", "_")[:20]
                        scenario_slug = f"custom_{custom_slug}"
                    else:
                        scenario_slug = finetune_scenario.lower().replace(" ", "_")
                    simulation_id = f"{base_id}-ft-{scenario_slug}"
                    app.state.current_simulation_id = simulation_id
                elif resume_model_id and not simulation_id:
                    base_id = resume_model_id.split(":")[0] if ":" in resume_model_id else resume_model_id
                    simulation_id = base_id
                    app.state.current_simulation_id = simulation_id
                elif not simulation_id:
                    try:
                        simulation_id = await asyncio.wait_for(
                            asyncio.to_thread(
                                supabase_service.create_simulation, "ai"
                            ),
                            timeout=20.0,
                        )
                        if simulation_id:
                            app.state.current_simulation_id = simulation_id
                        else:
                            raise RuntimeError(
                                "Supabase create_simulation returned an empty id"
                            )
                    except Exception:
                        logger.exception("Failed to create training simulation record")
                        await websocket.send_json({
                            "type": "training_error",
                            "is_training": False,
                            "message": (
                                "Could not create the Supabase training run. "
                                "Check backend credentials/network and try again."
                            ),
                        })
                        continue

                if not trainer.is_training:
                    task = asyncio.create_task(
                        _run_training_task(
                            trainer,
                            simulation_id or "",
                            num_episodes,
                            resume_model_id=resume_model_id,
                            resume_episode=resume_episode,
                            is_finetune=is_finetune,
                            finetune_scenario=finetune_scenario,
                            finetune_lr=finetune_lr,
                            finetune_epsilon=finetune_epsilon,
                            custom_profile=custom_profile,
                        )
                    )
                    app.state.training_task = task
                    await websocket.send_json({
                        "type": "training_started",
                        "is_training": True,
                        "simulation_id": simulation_id,
                        "message": "Training started; collecting demonstration transitions...",
                    })
                else:
                    await websocket.send_json({
                        "type": "training_error",
                        "is_training": True,
                        "message": "A training run is already active.",
                    })
            elif command == "stop_training":
                app.state.trainer.stop()
    except WebSocketDisconnect:
        training_manager.disconnect(websocket)
        if not training_manager.active_connections:
            app.state.trainer.stop()
