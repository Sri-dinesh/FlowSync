from typing import Any, Dict, Optional

from pydantic import BaseModel


class TrainingMetric(BaseModel):
    episode: int
    total_reward: float
    avg_wait_time: float
    throughput: int
    epsilon: float
    loss: Optional[float]
    is_training: bool


class StartTrainingRequest(BaseModel):
    num_episodes: int = 500
    simulation_id: Optional[str] = None
    resume_model_id: Optional[str] = None
    resume_episode: Optional[int] = None
    mode: str = "fresh"  # "fresh" | "resume" | "finetune"
    finetune_scenario: Optional[str] = "rush_hour"
    finetune_lr: Optional[float] = 1e-4
    finetune_epsilon: Optional[float] = 0.25
    custom_profile: Optional[Dict[str, Any]] = None

    model_config = {"protected_namespaces": ()}
