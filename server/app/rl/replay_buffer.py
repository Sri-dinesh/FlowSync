import numpy as np
import torch
from typing import Tuple
from app.rl.hyperparams import HyperParams

HP = HyperParams()


class SumTree:
    """
    Binary sum tree for O(log n) priority sampling.
    Each leaf stores a transition priority.
    Parent nodes store sum of children.
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
    """
    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self.tree = SumTree(capacity)
        self.alpha = HP.PER_ALPHA
        self.beta = HP.PER_BETA_START
        self.beta_end = HP.PER_BETA_END
        self.epsilon = HP.PER_EPSILON
        self.max_priority = 1.0

    def push(self, state, action, reward, next_state, done):
        """Add transition with maximum priority (ensures new transitions are sampled soon)."""
        transition = (
            np.array(state, dtype=np.float32),
            int(action),
            float(reward),
            np.array(next_state, dtype=np.float32),
            float(done),
        )
        priority = self.max_priority ** self.alpha
        self.tree.add(priority, transition)

    def sample(self, batch_size: int) -> Tuple:
        """
        Sample batch_size transitions proportional to priority.
        Returns transitions + importance sampling weights + tree indices for later update.
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
        weights /= weights.max()  # normalize

        states, actions, rewards, next_states, dones = zip(*transitions)

        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(np.array(actions)),
            torch.FloatTensor(np.array(rewards)),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor(np.array(dones)),
            torch.FloatTensor(weights),
            indices,
        )

    def update_priorities(self, indices: list, td_errors: np.ndarray):
        """Update priorities after training step based on new TD errors."""
        for idx, td_error in zip(indices, td_errors):
            priority = (abs(float(td_error)) + self.epsilon) ** self.alpha
            self.tree.update(idx, priority)
            self.max_priority = max(self.max_priority, priority)

    def anneal_beta(self, episode: int, total_episodes: int):
        """Anneal beta from PER_BETA_START to 1.0 over training."""
        self.beta = min(
            self.beta_end,
            HP.PER_BETA_START + (self.beta_end - HP.PER_BETA_START)
            * (episode / total_episodes)
        )

    def __len__(self) -> int:
        return self.tree.n_entries

    @property
    def is_ready(self) -> bool:
        """True when buffer has enough samples to start training."""
        return len(self) >= HP.MIN_REPLAY_SIZE
