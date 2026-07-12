from dataclasses import dataclass


@dataclass
class HyperParams:
    STATE_DIM: int = 20           # updated from 8 to 20
    ACTION_DIM: int = 4
    LEARNING_RATE: float = 3e-4   # slightly lower for Dueling stability
    GAMMA: float = 0.97           # higher discount
    BATCH_SIZE: int = 128         # larger batch for PER stability
    TRAIN_EVERY_N_STEPS: int = 2  # train every 2 steps
    REPLAY_BUFFER_SIZE: int = 100_000
    MIN_REPLAY_SIZE: int = 2_000
    EPSILON_START: float = 1.0
    EPSILON_END: float = 0.05
    EPSILON_DECAY: float = 0.998
    MAX_STEPS_PER_EPISODE: int = 1000
    DEFAULT_EPISODES: int = 1000
    TARGET_UPDATE_FREQ: int = 300
    CHECKPOINT_EVERY_N_EPISODES: int = 50

    # PER parameters
    PER_ALPHA: float = 0.6
    PER_BETA_START: float = 0.4
    PER_BETA_END: float = 1.0
    PER_EPSILON: float = 1e-6

    # Constraints
    MIN_GREEN_TIME: float = 8.0
    MAX_GREEN_TIME: float = 40.0
    STARVATION_THRESHOLD: float = 45.0
    
    # Simulation
    TRAINING_LAMBDA: float = 0.8
    EVAL_LAMBDA: float = 0.5

    # Lowercase property mappings for backward compatibility
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
