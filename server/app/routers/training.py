import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..schemas.training_schema import StartTrainingRequest
from ..services import model_service, supabase_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["training"])


class LoadModelRequest(BaseModel):
    model_id: str

    model_config = {"protected_namespaces": ()}


def _parse_episode(path: str) -> Optional[int]:
    filename = path.split("/")[-1]
    if not filename.startswith("checkpoint_") or not filename.endswith(".pt"):
        return None
    episode_text = filename[len("checkpoint_") : -len(".pt")]
    if not episode_text.isdigit():
        return None
    return int(episode_text)


@router.post("/start")
async def start_training(payload: StartTrainingRequest, request: Request) -> dict:
    app_state = request.app.state.app_state
    trainer = app_state["trainer"]

    if trainer.is_training:
        return {"status": "already_training"}

    simulation_id = payload.simulation_id or app_state.get("current_simulation_id")

    # Always ensure we have a real simulation record before training
    if not simulation_id:
        try:
            simulation_id = await asyncio.to_thread(
                supabase_service.create_simulation, "ai"
            )
            if simulation_id:
                app_state["current_simulation_id"] = simulation_id
            else:
                logger.error("create_simulation returned empty id, falling back to local")
                simulation_id = f"local-{int(time.time())}"
        except Exception:
            logger.exception("Failed to create simulation record for training")
            simulation_id = f"local-{int(time.time())}"

    task = asyncio.create_task(trainer.train(simulation_id, payload.num_episodes))
    app_state["training_task"] = task

    return {"status": "started", "simulation_id": simulation_id}


@router.post("/stop")
async def stop_training(request: Request) -> dict:
    app_state = request.app.state.app_state
    trainer = app_state["trainer"]
    trainer.stop()

    task = app_state.get("training_task")
    if task and not task.done():
        task.cancel()

    return {"status": "stopping"}


@router.get("/status")
async def training_status(request: Request) -> dict:
    app_state = request.app.state.app_state
    trainer = app_state["trainer"]
    return trainer.get_status()


@router.get("/models")
async def list_models() -> dict:
    models = await asyncio.to_thread(model_service.list_all_models)
    return {"models": models}


@router.post("/load")
async def load_model(payload: LoadModelRequest, request: Request) -> dict:
    app_state = request.app.state.app_state
    checkpoints = await asyncio.to_thread(
        model_service.list_checkpoints, payload.model_id
    )

    if not checkpoints:
        raise HTTPException(status_code=404, detail="No checkpoints found")

    episodes = [episode for path in checkpoints if (episode := _parse_episode(path))]
    if not episodes:
        raise HTTPException(status_code=404, detail="No valid checkpoints found")

    latest_episode = max(episodes)
    state_dict = await asyncio.to_thread(
        model_service.load_checkpoint, payload.model_id, latest_episode
    )

    agent = app_state["agent"]
    agent.online_net.load_state_dict(state_dict)
    agent.sync_target_network()

    return {"status": "loaded", "episode": latest_episode}
