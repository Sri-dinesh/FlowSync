from typing import Optional

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
