from dataclasses import dataclass


@dataclass
class HyperParams:
    # Network
    STATE_DIM: int = 8
    ACTION_DIM: int = 4
    HIDDEN_LAYERS: tuple = (256, 256, 128)   # wider, 3 layers

    # Training
    LEARNING_RATE: float = 5e-4              # slightly lower for stability
    GAMMA: float = 0.95                      # discount factor
    BATCH_SIZE: int = 64
    TRAIN_EVERY_N_STEPS: int = 1             # train every step (after warmup)

    # Replay buffer
    REPLAY_BUFFER_SIZE: int = 50_000         # larger buffer = more diverse samples
    MIN_REPLAY_SIZE: int = 1_000             # was 64 — now proper warmup

    # Exploration
    EPSILON_START: float = 1.0
    EPSILON_END: float = 0.05
    EPSILON_DECAY: float = 0.997             # slightly slower decay for better exploration

    # Episode config
    MAX_STEPS_PER_EPISODE: int = 500
    DEFAULT_EPISODES: int = 500

    # Target network
    TARGET_UPDATE_FREQ: int = 200            # was 500 — update more frequently

    # Checkpoint
    CHECKPOINT_EVERY_N_EPISODES: int = 50

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
