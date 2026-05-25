from pydantic import BaseModel


class MetricsSnapshot(BaseModel):
    avg_wait_time: float
    throughput: int
    max_queue: int
    current_phase: int
    is_training: bool
    current_episode: int
    epsilon: float
