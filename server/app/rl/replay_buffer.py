"""
replay_buffer.py — Prioritized Experience Replay (PER) Buffer
==============================================================
Improvements in this version:
  - BUG-03 fix: max_priority stored as RAW (|δ| + ε), exponentiation ^alpha
    applied only at the point of SumTree insertion. Eliminates double-exponent:
    old broken:  priority_stored = max_priority^alpha  (where max_priority was ALREADY ^alpha)
    corrected:   priority_stored = raw_max_priority^alpha  (raw = |δ| + ε)
  - Task 1.3:   Action masks stored per transition for masked Double-DQN targets.
"""
import numpy as np
import torch
from typing import Optional, Tuple
from app.rl.hyperparams import HyperParams

HP = HyperParams()


class SumTree:
    """
    Binary sum tree for O(log n) priority sampling.
    Each leaf stores a transition priority (already raised to alpha).
    Parent nodes store the sum of their children.
    """
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data = [None] * capacity
        self.write_ptr = 0
        self.n_entries = 0

    def _propagate(self, idx: int, change: float):
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx: int, s: float) -> int:
        left = 2 * idx + 1
        right = left + 1
        if left >= len(self.tree):
            return idx
        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])

    @property
    def total_priority(self) -> float:
        return self.tree[0]

    def add(self, priority: float, data):
        idx = self.write_ptr + self.capacity - 1
        self.data[self.write_ptr] = data
        self.update(idx, priority)
        self.write_ptr = (self.write_ptr + 1) % self.capacity
        self.n_entries = min(self.n_entries + 1, self.capacity)

    def update(self, idx: int, priority: float):
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)

    def get(self, s: float) -> Tuple[int, float, object]:
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return idx, self.tree[idx], self.data[data_idx]


class PrioritizedReplayBuffer:
    """
    Prioritized Experience Replay buffer.
    Based on: Schaul et al. 2016 (PER), applied in FPA-DQN, 3DQN-PER.

    Transitions with high TD-error are sampled more frequently.
    Importance sampling weights correct for the resulting bias.

    BUG-03 Fix:
    -----------
    self.max_priority is maintained as the RAW maximum priority value:
        raw_priority = |δ| + ε_per

    When inserting a new transition we apply alpha exactly once:
        stored_priority = raw_max_priority ** alpha

    When updating priorities after a train step we also store raw + apply alpha once:
        raw_priority   = |δ| + ε_per
        stored_priority = raw_priority ** alpha
        self.max_priority = max(self.max_priority, raw_priority)  ← raw!

    Previously max_priority stored (|δ| + ε)^alpha, so push() computed
    ((|δ| + ε)^alpha)^alpha = (|δ| + ε)^(alpha²) = p^0.36 instead of p^0.6.

    Task 1.3 (Action Masking):
    --------------------------
    Each transition optionally stores a valid_action_mask (bool[4]).
    This is used by DQNAgent.train_step() for masked Double-DQN target selection.
    """

    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self.tree = SumTree(capacity)
        self.alpha = HP.PER_ALPHA
        self.beta = HP.PER_BETA_START
        self.beta_end = HP.PER_BETA_END
        self.epsilon = HP.PER_EPSILON
        # BUG-03 FIX: max_priority is now stored as raw (|δ| + ε), NOT raised to alpha
        self.max_priority: float = 1.0  # raw priority floor

    def push(
        self,
        state,
        action: int,
        reward: float,
        next_state,
        done: bool,
        valid_action_mask: Optional[np.ndarray] = None,
    ) -> None:
        """
        Add transition with maximum-priority guarantee (ensures new transitions
        are sampled quickly — they have the highest uncertainty).

        BUG-03 FIX: priority = max_priority^alpha  where max_priority is RAW.
        Task 1.3:   Store optional valid_action_mask with the transition.
        """
        # Default action mask: all 4 actions valid (if no mask provided)
        if valid_action_mask is None:
            valid_action_mask = np.ones(HP.ACTION_DIM, dtype=bool)

        transition = (
            np.array(state, dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            float(done),
            valid_action_mask.astype(bool),   # Task 1.3: mask stored per transition
        )

        # BUG-03 CORRECTED: max_priority is raw, apply alpha here exactly once
        priority = self.max_priority ** self.alpha
        self.tree.add(priority, transition)

    def sample(self, batch_size: int) -> Tuple:
        """
        Sample batch_size transitions proportional to priority.

        Returns:
            (states, actions, rewards, next_states, dones, weights, indices, action_masks)
            action_masks: bool tensor [batch, 4] for masked Double-DQN (Task 1.3)
        """
        indices = []
        priorities = []
        transitions = []

        segment = self.tree.total_priority / batch_size

        for i in range(batch_size):
            a = segment * i
            b = segment * (i + 1)
            s = np.random.uniform(a, b)
            idx, priority, transition = self.tree.get(s)
            if transition is None:
                # Buffer not full yet, retry with random priority
                s = np.random.uniform(0, self.tree.total_priority)
                idx, priority, transition = self.tree.get(s)
            indices.append(idx)
            priorities.append(priority)
            transitions.append(transition)

        # Importance sampling weights to correct for priority bias
        sampling_probs = np.array(priorities) / self.tree.total_priority
        weights = (self.tree.n_entries * sampling_probs) ** (-self.beta)
        weights /= weights.max()  # normalize to [0, 1]

        states, actions, rewards, next_states, dones, masks = zip(*transitions)

        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(np.array(actions)),
            torch.FloatTensor(np.array(rewards)),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor(np.array(dones)),
            torch.FloatTensor(weights),
            indices,
            torch.BoolTensor(np.array(masks)),   # Task 1.3: action masks
        )

    def update_priorities(self, indices: list, td_errors: np.ndarray) -> None:
        """
        Update priorities after training step based on new TD errors.

        BUG-03 FIX: Store raw_priority in self.max_priority, apply alpha once
        when updating the SumTree leaf.
        """
        for idx, td_error in zip(indices, td_errors):
            # BUG-03 CORRECTED: compute raw priority, apply alpha once for SumTree
            raw_priority = abs(float(td_error)) + self.epsilon
            stored_priority = raw_priority ** self.alpha
            self.tree.update(idx, stored_priority)
            # Track RAW max priority for correct push() computation
            self.max_priority = max(self.max_priority, raw_priority)

    def anneal_beta(self, episode: int, total_episodes: int) -> None:
        """Anneal beta from PER_BETA_START to 1.0 over training."""
        self.beta = min(
            self.beta_end,
            HP.PER_BETA_START + (self.beta_end - HP.PER_BETA_START)
            * (episode / max(total_episodes, 1))
        )

    def __len__(self) -> int:
        return self.tree.n_entries

    @property
    def is_ready(self) -> bool:
        """True when buffer has enough samples to start training."""
        return len(self) >= HP.MIN_REPLAY_SIZE
