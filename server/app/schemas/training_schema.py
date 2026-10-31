from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class TrainingMetric(BaseModel):
    episode: int
    total_reward: float
    avg_wait_time: float
    throughput: int
    epsilon: float
    loss: Optional[float]
    is_training: bool


class StartTrainingRequest(BaseModel):
    num_episodes: int = Field(default=500, ge=1, strict=True)
    simulation_id: Optional[str] = None
    resume_model_id: Optional[str] = None
    resume_episode: Optional[int] = Field(default=None, ge=0, strict=True)
    mode: Literal["fresh", "resume", "finetune"] = "fresh"
    finetune_scenario: Optional[str] = "rush_hour"
    finetune_lr: Optional[float] = Field(default=1e-4, gt=0, allow_inf_nan=False, strict=True)
    finetune_epsilon: Optional[float] = Field(default=0.25, ge=0, le=1, allow_inf_nan=False, strict=True)
    custom_profile: Optional[Dict[str, Any]] = None

    model_config = {"protected_namespaces": ()}

    @model_validator(mode="after")
    def require_parent_model(self):
        if self.resume_model_id is not None and not self.resume_model_id.strip():
            raise ValueError("Parent model identifier must be nonempty")
        if (self.mode in ("resume","finetune") or self.resume_episode is not None) and not self.resume_model_id:
            raise ValueError("Resume, fine-tuning and explicit checkpoint slots require a parent model")
        return self
