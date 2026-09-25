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
    episode: Optional[int] = None

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
    app = request.app
    trainer = app.state.trainer

    if trainer.is_training:
        return {"status": "already_training"}

    simulation_id = payload.simulation_id
    resume_model_id = payload.resume_model_id
    resume_episode = payload.resume_episode

    # If resuming, reuse base model id as simulation_id so checkpoints stay organized
    if resume_model_id and not simulation_id:
        base_id = resume_model_id.split(":")[0] if ":" in resume_model_id else resume_model_id
        simulation_id = base_id
        app.state.current_simulation_id = simulation_id
    elif not simulation_id:
        try:
            simulation_id = await asyncio.to_thread(
                supabase_service.create_simulation, "ai"
            )
            if simulation_id:
                app.state.current_simulation_id = simulation_id
            else:
                logger.error("create_simulation returned empty id")
                simulation_id = f"local-{int(time.time())}"
                app.state.current_simulation_id = simulation_id
        except Exception:
            logger.exception("Failed to create simulation record for training")
            simulation_id = f"local-{int(time.time())}"
            app.state.current_simulation_id = simulation_id

    # Start training task in background
    app.state.training_task = asyncio.create_task(
        trainer.train(
            num_episodes=payload.num_episodes,
            simulation_id=simulation_id,
            resume_model_id=resume_model_id,
            resume_episode=resume_episode,
        )
    )

    return {
        "status": "started",
        "simulation_id": simulation_id,
        "is_resumed": bool(resume_model_id),
        "resume_model_id": resume_model_id,
    }


@router.post("/stop")
async def stop_training(request: Request) -> dict:
    app = request.app
    trainer = app.state.trainer
    trainer.stop()

    task = app.state.training_task
    if task and not task.done():
        task.cancel()

    return {"status": "stopping"}


@router.get("/status")
async def training_status(request: Request) -> dict:
    app = request.app
    trainer = app.state.trainer
    return trainer.get_status()


@router.get("/models")
async def list_models() -> dict:
    models = await asyncio.to_thread(model_service.list_all_models)
    return {"models": models}


@router.post("/load")
async def load_model(payload: LoadModelRequest, request: Request) -> dict:
    app = request.app
    raw_model_id = payload.model_id
    target_episode = payload.episode

    if ":" in raw_model_id:
        base_id, ep_str = raw_model_id.split(":", 1)
        ep_clean = ep_str.replace("checkpoint_", "").replace(".pt", "")
        if ep_clean.isdigit():
            target_episode = int(ep_clean)
        model_id = base_id
    else:
        model_id = raw_model_id

    checkpoints = await asyncio.to_thread(
        model_service.list_checkpoints, model_id
    )

    if not checkpoints:
        raise HTTPException(status_code=404, detail=f"No checkpoints found for {model_id}")

    episodes = [episode for path in checkpoints if (episode := _parse_episode(path))]
    if not episodes:
        raise HTTPException(status_code=404, detail="No valid checkpoints found")

    if target_episode is not None and target_episode in episodes:
        chosen_episode = target_episode
    elif target_episode is not None:
        chosen_episode = min(episodes, key=lambda e: abs(e - target_episode))
    else:
        chosen_episode = max(episodes)

    checkpoint_data = await asyncio.to_thread(
        model_service.load_checkpoint, model_id, chosen_episode
    )

    sim_agent = app.state.sim_agent
    training_agent = app.state.training_agent
    
    sim_agent.online_net.load_state_dict(checkpoint_data['online_net'])
    training_agent.online_net.load_state_dict(checkpoint_data['online_net'])
    
    if 'target_net' in checkpoint_data:
        sim_agent.target_net.load_state_dict(checkpoint_data['target_net'])
        training_agent.target_net.load_state_dict(checkpoint_data['target_net'])
    else:
        sim_agent.sync_target_network()
        training_agent.sync_target_network()
    
    if 'optimizer' in checkpoint_data:
        try:
            sim_agent.optimizer.load_state_dict(checkpoint_data['optimizer'])
            training_agent.optimizer.load_state_dict(checkpoint_data['optimizer'])
        except Exception:
            pass
    if 'step_count' in checkpoint_data:
        sim_agent.step_count = checkpoint_data['step_count']
        training_agent.step_count = checkpoint_data['step_count']
        
    sim_agent.target_net.eval()
    training_agent.target_net.eval()

    app.state.active_model_id = model_id
    app.state.active_model_episode = chosen_episode

    return {"status": "loaded", "model_id": model_id, "episode": chosen_episode}

