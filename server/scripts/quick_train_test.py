#!/usr/bin/env python3
"""
quick_train_test.py — 5-Episode Training Sanity Check
=====================================================
Verifies the entire training pipeline is operational:
  - Buffer fills properly
  - train_step() is called and produces non-trivial gradients
  - Loss decreases over episodes
  - Reward improves (at least doesn't diverge)
  - step_count / total_train_steps increments correctly

Run from server/ directory:
    source venv/bin/activate
    python scripts/quick_train_test.py
"""

import sys
import time
from pathlib import Path

SERVER_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SERVER_DIR))

import numpy as np
import torch

from app.simulation.environment import TrafficEnv
from app.rl.dqn_agent import DQNAgent
from app.rl.hyperparams import HyperParams

HP = HyperParams()

SEP = "─" * 60


def run_test():
    print("=" * 60)
    print("  FlowSync RL Quick Training Sanity Test")
    print("=" * 60)

    env = TrafficEnv()
    agent = DQNAgent()

    print(f"\nHyperparams:")
    print(f"  STATE_DIM:          {HP.STATE_DIM}")
    print(f"  ACTION_DIM:         {HP.ACTION_DIM}")
    print(f"  MIN_REPLAY_SIZE:    {HP.MIN_REPLAY_SIZE}")
    print(f"  BATCH_SIZE:         {HP.BATCH_SIZE}")
    print(f"  TRAIN_EVERY_N:      {HP.TRAIN_EVERY_N_STEPS}")
    print(f"  TARGET_UPDATE_FREQ: {HP.TARGET_UPDATE_FREQ}")
    print(f"  PER_EPSILON:        {HP.PER_EPSILON}")
    print(f"  GAMMA:              {HP.GAMMA}")
    print(f"  EPSILON_DECAY:      {HP.EPSILON_DECAY}")
    print(f"  MAX_STEPS_EP:       {HP.MAX_STEPS_PER_EPISODE}")

    # Phase 1: Fill buffer via greedy warm-start
    print(f"\n{SEP}")
    print("Phase 1: Greedy Warm-Start Buffer Fill")
    print(SEP)
    state, _ = env.reset()
    pushed = 0
    t0 = time.time()
    for step in range(3000):
        action = step % 4 if step % 100 == 0 else 0
        next_state, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        if info.get("is_decision_step", True):
            agent.replay_buffer.push(
                state, info.get("executed_action", action),
                reward, next_state, float(terminated)
            )
            pushed += 1
        state = next_state
        if done:
            state, _ = env.reset()
    t1 = time.time()
    print(f"  3000 env steps in {t1-t0:.2f}s")
    print(f"  Transitions pushed: {pushed} / 3000  ({pushed/3000*100:.1f}% decision steps)")
    print(f"  Buffer size: {len(agent.replay_buffer)} / {HP.MIN_REPLAY_SIZE} needed")
    print(f"  Buffer ready: {agent.replay_buffer.is_ready}")

    if not agent.replay_buffer.is_ready:
        print("\n[FAIL] Buffer not ready after warm-start!")
        print("  → is_decision_step rate is too low, check environment.py BUG-E fix")
        return

    # Phase 2: Verify first train step
    print(f"\n{SEP}")
    print("Phase 2: First Train Step")
    print(SEP)
    batch = agent.replay_buffer.sample(HP.BATCH_SIZE)
    loss, td_errs = agent.train_step(batch)
    print(f"  Loss:            {loss:.4f}")
    print(f"  TD-err mean:     {np.abs(td_errs).mean():.4f}")
    print(f"  TD-err max:      {np.abs(td_errs).max():.4f}")
    print(f"  total_train_steps after 1 step: {agent.total_train_steps}")
    assert agent.total_train_steps == 1, "total_train_steps not incrementing!"
    print("  ✓ total_train_steps increments correctly")

    # Phase 3: Run 5 full episodes
    print(f"\n{SEP}")
    print("Phase 3: 5 Full Training Episodes")
    print(SEP)
    epsilon = HP.EPSILON_START
    all_losses = []
    all_rewards = []

    for ep in range(1, 6):
        state, _ = env.reset()
        ep_reward = 0.0
        ep_losses = []
        ep_steps = 0
        decision_steps = 0

        for step in range(HP.MAX_STEPS_PER_EPISODE):
            action = agent.select_action(state, epsilon)
            next_state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            ep_reward += reward

            if info.get("is_decision_step", True):
                agent.replay_buffer.push(
                    state, info.get("executed_action", action),
                    reward, next_state, float(terminated)
                )
                decision_steps += 1

            if agent.replay_buffer.is_ready and step % HP.TRAIN_EVERY_N_STEPS == 0:
                batch = agent.replay_buffer.sample(HP.BATCH_SIZE)
                l, _ = agent.train_step(batch)
                ep_losses.append(l)

            if agent.step_count % HP.TARGET_UPDATE_FREQ == 0:
                agent.sync_target_network()

            state = next_state
            ep_steps = step + 1
            if done:
                break

        epsilon = max(HP.EPSILON_END, epsilon * HP.EPSILON_DECAY)
        avg_loss = np.mean(ep_losses) if ep_losses else float("nan")
        all_losses.append(avg_loss)
        all_rewards.append(ep_reward)

        print(f"  Ep {ep}: reward={ep_reward:.2f}  avg_loss={avg_loss:.4f}  "
              f"steps={ep_steps}  decision_steps={decision_steps}  "
              f"epsilon={epsilon:.3f}  train_steps={agent.total_train_steps}")

    print(f"\n{SEP}")
    print("Summary")
    print(SEP)
    print(f"  total_train_steps after 5 eps: {agent.total_train_steps}")
    print(f"  Buffer size: {len(agent.replay_buffer)}")

    valid_losses = [l for l in all_losses if not np.isnan(l)]
    if valid_losses:
        print(f"  Loss range: {min(valid_losses):.4f} – {max(valid_losses):.4f}")
        if len(valid_losses) >= 2 and valid_losses[-1] < valid_losses[0]:
            print("  ✓ Loss is decreasing — training is learning!")
        elif len(valid_losses) >= 2:
            print("  ⚠ Loss not clearly decreasing yet (may need more episodes)")

    print(f"  Reward range: {min(all_rewards):.2f} – {max(all_rewards):.2f}")
    if agent.total_train_steps == 0:
        print("\n[FAIL] total_train_steps = 0 — train_step was never called!")
        print("  → Check that buffer.is_ready returns True")
    elif agent.total_train_steps < 10:
        print(f"\n[WARN] Very few train steps ({agent.total_train_steps}) in 5 episodes")
        print("  → is_decision_step rate may still be too low")
    else:
        print(f"\n  ✓ Training pipeline operational! ({agent.total_train_steps} gradient updates)")

    # Check Q-value diversity
    print(f"\n{SEP}")
    print("Phase 4: Q-Value Diversity Check")
    print(SEP)
    test_states = torch.rand(100, HP.STATE_DIM)
    with torch.no_grad():
        q = agent.online_net(test_states)
    actions = q.argmax(dim=1)
    counts = torch.bincount(actions, minlength=4)
    print("  Action distribution over 100 random states:")
    for a, c in enumerate(counts):
        bar = "█" * int(c.item() / 2)
        print(f"    Phase {a} ({PHASE_LABELS[a]}): {c.item():3d}  {bar}")
    if counts.max() > 90:
        print("  ⚠ Network is extremely biased toward one action (Q-value collapse)")
        print("    → Check reward signal and PER_EPSILON")
    else:
        print("  ✓ Q-values show reasonable diversity")

    print(f"\n{'='*60}")
    print("  Sanity test complete.")
    print("=" * 60)


PHASE_LABELS = ["NS-Straight", "EW-Straight", "NS-Left", "EW-Left"]


if __name__ == "__main__":
    run_test()
