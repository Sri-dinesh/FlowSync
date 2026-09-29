#!/usr/bin/env python3
"""Reproducible offline FlowSync RL training and held-out evaluation.

Run from ``server/``:

    ../.venv/bin/python scripts/train_rl_offline.py --episodes 1000

The script does not contact Supabase and never promotes the final episode merely
because it is latest.  ``checkpoint_best.pt`` is selected by held-out queue-area.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

from app.rl.dqn_agent import DQNAgent
from app.rl.hyperparams import HyperParams
from app.simulation.benchmark_harness import DeterministicEvaluator
from app.simulation.curriculum import TrainingCurriculum
from app.simulation.environment import TrafficEnv
from app.simulation.greedy_teacher import GreedyTeacher


HP = HyperParams()
VALIDATION_SEEDS = [104729, 130363, 155921, 181081, 205019]


def evaluate(agent: DQNAgent, steps: int = 1200) -> dict:
    results = {}
    for mode in ("ai", "fixed", "greedy"):
        evaluator = DeterministicEvaluator(
            agent=agent if mode == "ai" else None,
            mode=mode,
            spawn_lambda=0.5,
        )
        result = evaluator.run_multi_seed(steps, VALIDATION_SEEDS)
        results[mode] = {
            "mean_wait": result.mean_avg_wait,
            "mean_p95_delay": result.mean_p95_delay,
            "mean_queue_area": result.mean_queue_area,
            "mean_throughput": result.mean_throughput,
            "mean_override_rate": result.mean_override_rate,
            "checkpoint_hash": result.checkpoint_hash,
        }
    fixed_area = max(results["fixed"]["mean_queue_area"], 1e-9)
    greedy_area = max(results["greedy"]["mean_queue_area"], 1e-9)
    ai_area = results["ai"]["mean_queue_area"]
    results["improvement"] = {
        "queue_area_vs_fixed_pct": (fixed_area - ai_area) / fixed_area * 100.0,
        "queue_area_vs_greedy_pct": (greedy_area - ai_area) / greedy_area * 100.0,
    }
    return results


def checkpoint(agent: DQNAgent, episode: int, validation: dict) -> dict:
    state = agent.get_checkpoint_state()
    state.update({
        "episode": episode,
        "reward_version": "v4_incremental_delay",
        "demand_version": "v2_total_lambda_with_upstream_backlog",
        "validation": validation,
    })
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260928)
    parser.add_argument("--warmup-decisions", type=int, default=3000)
    parser.add_argument("--pretrain-updates", type=int, default=500)
    parser.add_argument("--validate-every", type=int, default=25)
    parser.add_argument("--output", type=Path, default=Path("models/offline_rl_v6"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    env = TrafficEnv()
    agent = DQNAgent()
    curriculum = TrainingCurriculum(env, total_episodes=args.episodes)
    started = time.time()

    print(f"Collecting {args.warmup_decisions} causal greedy demonstrations...", flush=True)
    GreedyTeacher(env).fill_buffer(
        agent.replay_buffer,
        n_steps=args.warmup_decisions,
        seed=args.seed,
    )
    print(f"Running {args.pretrain_updates} DQfD pretraining updates...", flush=True)
    for _ in range(args.pretrain_updates):
        agent.train_step(agent.replay_buffer.sample(HP.BATCH_SIZE))
        if agent.step_count % HP.TARGET_UPDATE_FREQ == 0:
            agent.sync_target_network()

    history: list[dict] = []
    baseline_validation = evaluate(agent)
    best_score = baseline_validation["ai"]["mean_queue_area"]
    best_episode = 0
    initial_best = checkpoint(agent, 0, baseline_validation)
    torch.save(initial_best, args.output / "checkpoint_best.pt")
    torch.save(initial_best, args.output / "checkpoint_0.pt")
    print("Pretrain validation:", json.dumps(baseline_validation, indent=2), flush=True)

    epsilon = HP.EPSILON_START
    for episode in range(1, args.episodes + 1):
        stage, demand_lambda = curriculum.apply(episode)
        state, reset_info = env.reset_to_decision(seed=args.seed + episode)
        action_mask = reset_info["valid_action_mask"]
        episode_reward = 0.0
        losses = []
        decisions = 0

        while env.intersection.timestep < env.max_steps:
            action = agent.select_action(state, epsilon, action_mask)
            next_state, reward, terminated, truncated, info = env.step_decision(action)
            next_mask = info["valid_action_mask"]
            agent.replay_buffer.push(
                state,
                info["executed_action"],
                reward,
                next_state,
                terminated,
                valid_action_mask=action_mask,
                next_valid_action_mask=next_mask,
                bootstrap_discount=info["bootstrap_discount"],
            )
            loss, _ = agent.train_step(agent.replay_buffer.sample(HP.BATCH_SIZE))
            losses.append(loss)
            if agent.step_count % HP.TARGET_UPDATE_FREQ == 0:
                agent.sync_target_network()
            state, action_mask = next_state, next_mask
            episode_reward += reward
            decisions += 1
            if terminated or truncated:
                break

        epsilon = max(HP.EPSILON_END, epsilon * HP.EPSILON_DECAY)
        agent.replay_buffer.anneal_beta(episode, args.episodes)
        row = {
            "episode": episode,
            "stage": stage,
            "lambda": demand_lambda,
            "epsilon": epsilon,
            "reward": episode_reward,
            "mean_loss": float(np.mean(losses)),
            "avg_wait": env.intersection.get_avg_wait_time(),
            "throughput": env.intersection.total_passed,
            "arrivals": env.intersection.spawner.total_generated,
            "decisions": decisions,
            "q_stats": agent.latest_q_stats,
        }
        history.append(row)

        should_validate = episode % args.validate_every == 0 or episode == args.episodes
        if should_validate:
            validation = evaluate(agent)
            row["validation"] = validation
            score = validation["ai"]["mean_queue_area"]
            if score < best_score:
                best_score = score
                best_episode = episode
                best_state = checkpoint(agent, episode, validation)
                torch.save(best_state, args.output / "checkpoint_best.pt")
                # The web/server model loader reserves checkpoint_0.pt as the
                # held-out winner while preserving the actual episode inside.
                torch.save(best_state, args.output / "checkpoint_0.pt")
            torch.save(
                checkpoint(agent, episode, validation),
                args.output / f"checkpoint_{episode}.pt",
            )
            print(
                f"ep={episode} stage={stage} eps={epsilon:.3f} "
                f"train_wait={row['avg_wait']:.2f}s "
                f"val_area={score:.1f} best_ep={best_episode}",
                flush=True,
            )

        (args.output / "training_history.json").write_text(
            json.dumps(history, indent=2), encoding="utf-8"
        )

    summary = {
        "best_episode": best_episode,
        "best_validation_queue_area": best_score,
        "elapsed_seconds": time.time() - started,
        "episodes": args.episodes,
        "seed": args.seed,
        "obs_version": HP.OBS_VERSION,
        "reward_version": "v4_incremental_delay",
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
