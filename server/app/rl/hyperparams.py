"""
hyperparams.py — FlowSync RL Hyperparameters
=============================================
Changes:
  - Task 4.2: STATE_DIM updated to 28 (from 20) to accommodate 8 demand-forecast features
  - Task 2.1: Added DECISION_DT = 2.0 seconds (Semi-MDP decision interval reference)
  - Updated obs_version to v5_28dim_forecast for checkpoint compatibility tracking
"""
from dataclasses import dataclass


@dataclass
class HyperParams:
    # ── Core network dimensions ───────────────────────────────────────────────
    # Task 4.2: 28 = 12 queues + 4 phase-onehot + 4 signal-context + 8 forecast
    STATE_DIM: int = 28           # expanded from 20 → 28 (8 demand-forecast dims appended)
    ACTION_DIM: int = 4

    # ── Learning ──────────────────────────────────────────────────────────────
    LEARNING_RATE: float = 3e-4   # slightly lower for Dueling stability
    GAMMA: float = 0.97           # higher discount, appropriate for semi-MDP
    BATCH_SIZE: int = 128         # larger batch for PER stability

    # ── Training schedule ─────────────────────────────────────────────────────
    TRAIN_EVERY_N_STEPS: int = 2  # train every 2 steps for faster learning
    MAX_STEPS_PER_EPISODE: int = 1000
    DEFAULT_EPISODES: int = 1000
    TARGET_UPDATE_FREQ: int = 300
    CHECKPOINT_EVERY_N_EPISODES: int = 50

    # ── Replay buffer ─────────────────────────────────────────────────────────
    REPLAY_BUFFER_SIZE: int = 100_000
    MIN_REPLAY_SIZE: int = 500    # warm up in <1 episode (500 steps × 0.1dt = 50s)

    # ── Exploration ───────────────────────────────────────────────────────────
    EPSILON_START: float = 1.0
    EPSILON_END: float = 0.05
    EPSILON_DECAY: float = 0.994  # reaches 0.05 by ~550 episodes (good for 500-ep runs)

    # ── PER parameters (Schaul et al. 2016) ──────────────────────────────────
    PER_ALPHA: float = 0.6
    PER_BETA_START: float = 0.4
    PER_BETA_END: float = 1.0
    PER_EPSILON: float = 0.01   # BUG-F fix: Schaul 2016 standard; 1e-6 caused priority collapse

    # ── Signal timing constraints ─────────────────────────────────────────────
    MIN_GREEN_TIME: float = 8.0
    MAX_GREEN_TIME: float = 40.0
    STARVATION_THRESHOLD: float = 45.0

    # ── Semi-MDP timing (Task 2.1) ────────────────────────────────────────────
    # Reference decision interval: agent decisions are effective every ~2.0s
    # (MIN_GREEN_TIME sets the actual gate; DECISION_DT used for GAMMA discounting)
    DECISION_DT: float = 2.0

    # ── Simulation ────────────────────────────────────────────────────────────
    TRAINING_LAMBDA: float = 0.8
    EVAL_LAMBDA: float = 0.5

    # ── Demand forecaster (Task 4.1) ──────────────────────────────────────────
    FORECAST_DIMS: int = 8        # dims 20-27 in the 28-D state vector

    # ── Observation versioning (for checkpoint compatibility) ─────────────────
    OBS_VERSION: str = "v5_28dim_forecast"

    # ── Backward-compatible property mappings ─────────────────────────────────
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
