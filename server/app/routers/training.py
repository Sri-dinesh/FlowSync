import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..schemas.training_schema import StartTrainingRequest
from ..services import model_service, supabase_service
from ..services.training_tasks import reserve_training_state, run_training

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["training"])


class LoadModelRequest(BaseModel):
    model_id: str
    episode: Optional[int] = Field(default=None, ge=0, strict=True)

    model_config = {"protected_namespaces": ()}


from ..simulation.spawner import SCENARIO_PROFILES

@router.get("/scenarios")
async def list_scenarios() -> dict:
    """Return available fine-tuning scenarios with directional weights and turn distributions."""
    scenarios = []
    for key, profile in SCENARIO_PROFILES.items():
        if key == "uniform":
            continue
        scenarios.append({
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "directional_weights": profile.directional_weights,
            "turn_probs": profile.turn_probs,
            "base_lambda": profile.base_lambda,
            "lambda_multiplier": profile.lambda_multiplier,
        })
    return {"scenarios": scenarios}


@router.post("/start")
async def start_training(payload: StartTrainingRequest, request: Request) -> dict:
    app = request.app
    with reserve_training_state(app.state) as claimed:
        if not claimed:
            return {"status": "already_training"}
        trainer = app.state.trainer

        simulation_id = payload.simulation_id
        resume_model_id = payload.resume_model_id
        resume_episode = payload.resume_episode
        is_finetune = payload.mode == "finetune"
        finetune_scenario = payload.finetune_scenario or "rush_hour"
        custom_profile = payload.custom_profile

        if is_finetune:
            # Fine-tuning forks from the base model checkpoint into a new scenario-specific model ID
            base_id = resume_model_id.split(":")[0] if resume_model_id and ":" in resume_model_id else (resume_model_id or "base")
            if finetune_scenario == "custom" and custom_profile and custom_profile.get("name"):
                custom_slug = custom_profile["name"].lower().strip().replace(" ", "_")[:20]
                scenario_slug = f"custom_{custom_slug}"
            else:
                scenario_slug = finetune_scenario.lower().replace(" ", "_")
            simulation_id = f"{base_id}-ft-{scenario_slug}"
            app.state.current_simulation_id = simulation_id
        elif resume_model_id and not simulation_id:
            # If resuming, reuse base model id as simulation_id so checkpoints stay organized
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
            run_training(trainer,
                num_episodes=payload.num_episodes,
                simulation_id=simulation_id,
                resume_model_id=resume_model_id,
                resume_episode=resume_episode,
                is_finetune=is_finetune,
                finetune_scenario=finetune_scenario,
                finetune_lr=1e-4 if payload.finetune_lr is None else payload.finetune_lr,
                finetune_epsilon=0.25 if payload.finetune_epsilon is None else payload.finetune_epsilon,
                custom_profile=custom_profile,
            )
        )

        return {
            "status": "started",
            "simulation_id": simulation_id,
            "mode": payload.mode,
            "is_resumed": bool(resume_model_id) and not is_finetune,
            "is_finetuned": is_finetune,
            "scenario": (
                custom_profile.get("name", "Custom")
                if finetune_scenario == "custom" and custom_profile
                else (finetune_scenario if is_finetune else None)
            ),
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
    with reserve_training_state(app.state) as claimed:
        if not claimed:
            raise HTTPException(status_code=409,detail="Stop training before replacing its model")
        from ..services.checkpoint_loading import load_website_agent,parse_model_request,select_checkpoint
        try:
            model_id,target_episode = parse_model_request(payload.model_id,payload.episode)
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc
        try:
            checkpoints = await asyncio.to_thread(model_service.list_checkpoints,model_id)
            chosen_episode = select_checkpoint(checkpoints,target_episode)
            checkpoint_data = await asyncio.to_thread(model_service.load_checkpoint,model_id,chosen_episode)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404,detail=str(exc)) from exc
        try:
            sim_agent,actual_episode = load_website_agent(checkpoint_data)
            training_agent,_ = load_website_agent(checkpoint_data)
            training_agent.online_net.train()
        except ValueError as exc:
            raise HTTPException(status_code=409,detail=str(exc)) from exc
        app.state.sim_agent = sim_agent
        app.state.training_agent = training_agent
        app.state.trainer.agent = training_agent
        app.state.active_model_id = model_id
        app.state.active_model_episode = actual_episode
        app.state.active_model_checkpoint_slot = chosen_episode

        return {
            "status": "loaded",
            "model_id": model_id,
            "episode": actual_episode,
            "checkpoint_episode": chosen_episode,
        }
