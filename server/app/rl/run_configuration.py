"""Capture selected effective website-training settings and their source bytes."""
from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np
import torch

from . import replay_buffer
from ..simulation import environment

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = (
    "server/app/rl/run_configuration.py", "server/app/rl/trainer.py",
    "server/app/rl/dqn_agent.py", "server/app/rl/dqn_network.py", "server/app/rl/hyperparams.py",
    "server/app/rl/replay_buffer.py", "server/app/rl/observations.py",
    "server/app/simulation/environment.py", "server/app/simulation/intersection.py",
    "server/app/simulation/vehicle.py", "server/app/simulation/traffic_signal.py",
    "server/app/simulation/spawner.py", "server/app/simulation/curriculum.py",
    "server/app/simulation/greedy_teacher.py", "server/app/simulation/demand_forecast.py",
    "server/app/simulation/traffic_math.py", "server/app/simulation/benchmark_harness.py",
    "server/app/services/model_service.py", "server/app/services/artifact_files.py",
    "server/app/services/checkpoint_loading.py", "server/app/services/training_tasks.py",
    "server/app/schemas/training_schema.py", "server/app/config.py",
)


def canonical_bytes(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def configuration_hash(configuration: dict) -> str:
    return hashlib.sha256(canonical_bytes(configuration)).hexdigest()


def environment_settings(env) -> dict:
    signal,spawner = env.intersection.signal,env.intersection.spawner
    return {"max_ticks":env.max_steps,"reward_version":env.reward_version,"watchdogs":env.enable_watchdogs,
        "dt_s":environment.SIMULATION_DT,"discount_gamma":environment.HP.GAMMA,"discount_reference_s":environment.HP.DECISION_DT,
        "signal":{name:getattr(signal,name) for name in ("min_green_duration","fixed_duration","yellow_duration",
            "red_duration","MAX_GREEN_TIME","STARVATION_THRESHOLD")},
        "demand":{"base_rate_vehicles_per_s":spawner.lambda_rate,"profile":spawner.profile}}


def json_settings(value, unavailable: list[str], path="configuration"):
    """Expose absent instrumentation as null, never as fabricated numeric values."""
    if is_dataclass(value) and not isinstance(value,type):
        value = asdict(value)
    if isinstance(value,np.generic):
        value = value.item()
    if value is None or type(value) in (str,int,bool):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"Nonfinite run configuration at {path}")
        return value
    if isinstance(value,(list,tuple)):
        return [json_settings(item,unavailable,f"{path}.{index}") for index,item in enumerate(value)]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key:json_settings(item,unavailable,f"{path}.{key}") for key,item in value.items()}
    unavailable.append(path)
    return None


def capture_configuration(trainer, model_id: str, episodes: int, curriculum, plan: dict) -> tuple[dict,dict[str,bytes]]:
    agent,hp = trainer.agent,trainer.hyperparams
    optimizer_groups = [{key:group[key] for key in ("lr","eps","betas","weight_decay","amsgrad") if key in group}
        for group in agent.optimizer.param_groups]
    config = {"schema_version":"website_training_configuration_v1","runtime_profile":"interactive_legacy",
        "model_id":model_id,"mode":"finetune" if trainer.is_finetune else "resume" if trainer.is_resumed else "fresh",
        "requested_episodes":episodes,"start_episode":trainer.start_episode,"target_episode":trainer.target_episodes,
        "parent":{"model_id":trainer.resume_model_id.split(":",1)[0] if trainer.resume_model_id else None,
            "requested_identifier":trainer.resume_model_id,"checkpoint_slot":trainer.resume_checkpoint_slot,
            "storage_provenance":trainer.parent_checkpoint_storage,
            "actual_episode":trainer.parent_episode if trainer.is_finetune else trainer.start_episode if trainer.is_resumed else None},
        "declared_hyperparams":asdict(hp),
        "agent":{"observation_version":agent.obs_version,"state_dim":agent.state_dim,"reward_version":agent.reward_version,
            "network":type(agent.online_net).__name__,"parameter_shapes":{key:list(value.shape) for key,value in agent.online_net.state_dict().items()},
            "optimizer":type(agent.optimizer).__name__,"optimizer_groups":optimizer_groups,
            "demonstration_loss_weight":agent.demonstration_loss_weight,
            "initial_optimizer_updates":agent.total_train_steps,"initial_target_counter":agent.step_count},
        "replay":{"capacity":agent.replay_buffer.capacity,"alpha":agent.replay_buffer.alpha,
            "beta_at_capture":agent.replay_buffer.beta,"beta_end":agent.replay_buffer.beta_end,
            "priority_epsilon":agent.replay_buffer.epsilon,"readiness_transitions":replay_buffer.HP.MIN_REPLAY_SIZE,
            "initial_size":len(agent.replay_buffer),"restored_from_checkpoint":False},
        "collector":{"reward_version":trainer.env.reward_version,"action_label":"executed_action",
            "batch_size":hp.BATCH_SIZE,"train_every_decisions":hp.TRAIN_EVERY_N_STEPS,"target_sync_updates":hp.TARGET_UPDATE_FREQ},
        "exploration":{"epsilon_at_setup":trainer.epsilon,"epsilon_floor":hp.EPSILON_END,
            "episode_multiplier":trainer.finetune_decay if trainer.is_finetune else hp.EPSILON_DECAY},
        "environment_at_setup":environment_settings(trainer.env),
        "curriculum_stages":curriculum.stages if curriculum is not None else [],"plan":plan,
        "runtime":{"python":platform.python_version(),"torch":str(torch.__version__),"numpy":str(np.__version__),
            "device":str(next(agent.online_net.parameters()).device)},
        "randomness":{"policy_training_seed":None,"global_rng_state_recorded":False,
            "note":"Website training has no declared global training seed; this record does not establish deterministic reruns."}}
    unavailable = []
    config = json_settings(config,unavailable)
    config["unavailable_fields"] = unavailable
    sources = {name:(ROOT/name).read_bytes() for name in SOURCE_FILES}
    config["source_sha256"] = {name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}
    try:
        revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip())
        config["source_revision"] = {"git_commit":revision,"worktree_dirty":dirty}
    except (OSError,subprocess.CalledProcessError):
        config["source_revision"] = {"git_commit":None,"worktree_dirty":None}
    return config,sources


def capture_episode(trainer, episode: int, curriculum_status: dict) -> dict:
    unavailable = []
    record = {"episode":episode,"epsilon_at_start":trainer.epsilon,
        "replay_beta":trainer.agent.replay_buffer.beta,
        "optimizer_groups":[{key:group[key] for key in ("lr","eps","betas") if key in group}
            for group in trainer.agent.optimizer.param_groups],
        "environment_after_reset":environment_settings(trainer.env),"curriculum":curriculum_status}
    record = json_settings(record,unavailable,"episode")
    record["unavailable_fields"] = unavailable
    return record
