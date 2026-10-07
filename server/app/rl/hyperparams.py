"""RL agent hyperparameters and environment timing constraints."""
from dataclasses import dataclass


@dataclass
class HyperParams:
    STATE_DIM: int = 28
    ACTION_DIM: int = 4

    LEARNING_RATE: float = 3e-4
    # Discount scaled per DECISION_DT seconds for semi-MDP variable-duration transitions.
    GAMMA: float = 0.99
    BATCH_SIZE: int = 128

    TRAIN_EVERY_N_STEPS: int = 1
    # 3000 steps = 300s, ensuring multiple complete four-phase signal cycles per episode.
    MAX_STEPS_PER_EPISODE: int = 3_000
    DEFAULT_EPISODES: int = 500
    TARGET_UPDATE_FREQ: int = 500
    CHECKPOINT_EVERY_N_EPISODES: int = 50

    REPLAY_BUFFER_SIZE: int = 100_000
    MIN_REPLAY_SIZE: int = 1_000

    EPSILON_START: float = 1.0
    EPSILON_END: float = 0.05
    EPSILON_DECAY: float = 0.997

    PER_ALPHA: float = 0.6
    PER_BETA_START: float = 0.4
    PER_BETA_END: float = 1.0
    # Schaul et al. (2016) standard; smaller epsilon (1e-6) causes priority collapse.
    PER_EPSILON: float = 0.01

    MIN_GREEN_TIME: float = 8.0
    MAX_GREEN_TIME: float = 40.0
    STARVATION_THRESHOLD: float = 45.0

    # Reference decision interval for discount scaling under variable phase durations.
    DECISION_DT: float = 2.0

    TRAINING_LAMBDA: float = 0.8
    EVAL_LAMBDA: float = 0.5

    FORECAST_DIMS: int = 8
    OBS_VERSION: str = "v6_28dim_smdp"

    @property
    def learning_rate(self) -> float: return self.LEARNING_RATE
    @property
    def gamma(self) -> float: return self.GAMMA
    @property
    def epsilon_start(self) -> float: return self.EPSILON_START
    @property
    def epsilon_end(self) -> float: return self.EPSILON_END
    @property
    def epsilon_decay(self) -> float: return self.EPSILON_DECAY
    @property
    def batch_size(self) -> int: return self.BATCH_SIZE
    @property
    def replay_buffer_size(self) -> int: return self.REPLAY_BUFFER_SIZE
    @property
    def target_update_freq(self) -> int: return self.TARGET_UPDATE_FREQ
    @property
    def max_steps_per_episode(self) -> int: return self.MAX_STEPS_PER_EPISODE
    @property
    def episodes(self) -> int: return self.DEFAULT_EPISODES
    @property
    def min_replay_size(self) -> int: return self.MIN_REPLAY_SIZE
