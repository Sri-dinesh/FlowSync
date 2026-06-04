from dataclasses import dataclass


@dataclass
class HyperParams:
    learning_rate: float = 1e-3
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 0.995
    batch_size: int = 64
    replay_buffer_size: int = 10_000
    target_update_freq: int = 500
    max_steps_per_episode: int = 500
    episodes: int = 500
    min_replay_size: int = 64
