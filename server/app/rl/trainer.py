"""
trainer.py — FlowSync RL Training Loop
=======================================
All improvements integrated in this version:

  Phase 0 / BUG-01:
  - BUG-01 fix: Uses info["executed_action"] when pushing to replay buffer,
    ensuring stored transitions reflect the actual phase applied.
  - Task 0.2: Streams reward component breakdown and watchdog override rate
    to the frontend training WebSocket at episode boundaries.

  Phase 2:
  - Task 2.1 (Semi-MDP): Only pushes transitions on `is_decision_step` ticks,
    filtering out non-causal yellow/all-red/min-green steps.

  Phase 5:
  - Task 5.1: Greedy teacher warm-start seeds buffer before training begins.
  - Task 5.2: Multi-regime curriculum adjusts λ per episode.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

import numpy as np

from .dqn_agent import DQNAgent
from .hyperparams import HyperParams
from ..simulation.environment import TrafficEnv
from ..simulation.greedy_teacher import GreedyTeacher
from ..simulation.curriculum import TrainingCurriculum

logger = logging.getLogger(__name__)

# Greedy warm-start: number of demonstration transitions to collect before RL
_GREEDY_WARMUP_STEPS = 3000


class Trainer:
    def __init__(
        self,
        env: TrafficEnv,
        agent: DQNAgent,
        supabase_service: Any,
        model_service: Any,
        ws_broadcast_fn: Callable[[dict], Awaitable[None]],
        app_state: Any = None,
        hyperparams: Optional[HyperParams] = None,
        enable_curriculum: bool = True,
        enable_greedy_warmup: bool = True,
    ) -> None:
        self.env = env
        self.agent = agent
        self.supabase_service = supabase_service
        self.model_service = model_service
        self.ws_broadcast_fn = ws_broadcast_fn
        self.app_state = app_state
        self.hyperparams = hyperparams or HyperParams()
        self.is_training = False
        self.current_episode = 0
        self.epsilon = self.hyperparams.epsilon_start
        self.enable_curriculum = enable_curriculum
        self.enable_greedy_warmup = enable_greedy_warmup

    async def train(self, simulation_id: str, num_episodes: int) -> None:
        self.is_training = True
        self.current_episode = 0
        self.epsilon = self.hyperparams.epsilon_start

        # ── Task 5.2: Curriculum setup ─────────────────────────────────────
        curriculum = TrainingCurriculum(
            env=self.env,
            total_episodes=num_episodes,
        ) if self.enable_curriculum else None

        # ── Task 5.1: Greedy demonstration warm-start ──────────────────────
        # Issue-3 fix: skip warmup if buffer already has enough samples
        # (prevents overwriting good trained transitions on restart)
        if self.enable_greedy_warmup and len(self.agent.replay_buffer) < self.hyperparams.MIN_REPLAY_SIZE:
            teacher = GreedyTeacher(env=self.env)
            logger.info("Starting Greedy teacher warm-start...")
            await asyncio.to_thread(
                teacher.fill_buffer,
                self.agent.replay_buffer,
                _GREEDY_WARMUP_STEPS,
            )
            await self.ws_broadcast_fn({
                "type":    "warmup_complete",
                "message": f"Greedy teacher seeded buffer with {_GREEDY_WARMUP_STEPS} transitions.",
            })
        elif self.enable_greedy_warmup:
            logger.info(
                "Skipping greedy warmup — buffer already has %d/%d samples.",
                len(self.agent.replay_buffer),
                self.hyperparams.MIN_REPLAY_SIZE,
            )

        # Rolling window of recent rewards for model metadata avg_reward
        _recent_rewards: list[dict] = []
        _REWARD_WINDOW = 50

        for episode_index in range(num_episodes):
            if not self.is_training:
                break

            episode_num = episode_index + 1
            self.current_episode = episode_num

            # ── Task 5.2: Apply curriculum λ for this episode ───────────────
            curriculum_status = {}
            if curriculum is not None:
                stage_name, applied_lambda = curriculum.apply(episode_num)
                curriculum_status = {
                    "stage": stage_name,
                    "lambda": applied_lambda,
                }

            state, _ = self.env.reset()
            total_reward = 0.0
            loss_value: Optional[float] = None
            steps = 0
            stopped_early = False

            # Anneal PER beta over training
            self.agent.replay_buffer.anneal_beta(episode_index, num_episodes)

            for step in range(self.hyperparams.MAX_STEPS_PER_EPISODE):
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(state, self.epsilon)

                # ── Step environment ────────────────────────────────────────
                next_state, reward, terminated, truncated, info = await asyncio.to_thread(
                    self.env.step, action
                )
                done = terminated or truncated

                # ── BUG-01 FIX: Use executed_action for replay buffer push ──
                executed_action = info.get("executed_action", action)

                # ── Task 2.1 (Semi-MDP): Only push causal transitions ────────
                # BUG-E FIX: subsample GREEN steps — store 1 per 10 (1 simulated second).
                # Old: push every GREEN step (~680/ep) — redundant near-identical transitions.
                # Now: push every 10th GREEN step (~65/ep) — informative, diverse transitions.
                is_decision_step = info.get("is_decision_step", True)

                if is_decision_step and (step % 10 == 0):
                    self.agent.replay_buffer.push(
                        state,
                        executed_action,   # BUG-01: actual executed action
                        reward,
                        next_state,
                        terminated,
                        valid_action_mask=None,
                    )

                # ── Train step ───────────────────────────────────────────────
                if (
                    self.agent.replay_buffer.is_ready
                    and step % self.hyperparams.TRAIN_EVERY_N_STEPS == 0
                ):
                    batch = self.agent.replay_buffer.sample(self.hyperparams.BATCH_SIZE)
                    loss_value, td_errors = await asyncio.to_thread(
                        self.agent.train_step, batch
                    )

                if self.agent.step_count % self.hyperparams.TARGET_UPDATE_FREQ == 0:
                    self.agent.sync_target_network()

                total_reward += reward
                state = next_state
                steps = step + 1

                # Yield to event loop
                if not self.agent.replay_buffer.is_ready or step % 4 == 0:
                    await asyncio.sleep(0)

                if done:
                    break

            if stopped_early:
                break

            self.epsilon = max(
                self.hyperparams.epsilon_end,
                self.epsilon * self.hyperparams.epsilon_decay,
            )

            avg_wait = self.env.intersection.get_avg_wait_time()
            throughput = self.env.intersection.total_passed

            # ── Task 0.2: Collect reward component telemetry ─────────────────
            episode_telemetry = self.env.get_episode_telemetry()
            reward_components = episode_telemetry.get("reward_components", {})
            watchdog_rate = episode_telemetry.get("watchdog_override_rate", 0.0)
            watchdog_count = episode_telemetry.get("watchdog_override_count", 0)

            _recent_rewards.append({"reward": total_reward})
            if len(_recent_rewards) > _REWARD_WINDOW:
                _recent_rewards.pop(0)

            persist_remote = bool(simulation_id) and not simulation_id.startswith("local-")

            if persist_remote:
                try:
                    await asyncio.to_thread(
                        self.supabase_service.save_episode,
                        simulation_id,
                        episode_num,
                        total_reward,
                        avg_wait,
                        throughput,
                        self.epsilon,
                        loss_value,
                        steps,
                    )
                except Exception:
                    logger.exception(
                        "Failed to save episode %d for simulation %s",
                        episode_num,
                        simulation_id,
                    )

            is_last_episode = episode_index == num_episodes - 1

            # ── Broadcast episode metrics ────────────────────────────────────
            await self.ws_broadcast_fn(
                {
                    "episode":           episode_num,
                    "total_reward":      total_reward,
                    "avg_wait_time":     avg_wait,
                    "throughput":        throughput,
                    "epsilon":           self.epsilon,
                    "loss":              loss_value,
                    "steps":             steps,
                    "buffer_ready":      self.agent.replay_buffer.is_ready,
                    "is_training":       False if is_last_episode else self.is_training,
                    "total_train_steps": self.agent.total_train_steps,  # BUG-B visibility
                    # Task 0.2: reward component telemetry
                    "reward_components":       reward_components,
                    "watchdog_override_rate":  watchdog_rate,
                    "watchdog_override_count": watchdog_count,
                    # Task 5.2: curriculum info
                    "curriculum":              curriculum_status,
                }
            )

            if simulation_id and (episode_num % 50 == 0 or is_last_episode):
                await asyncio.to_thread(
                    self.model_service.save_checkpoint,
                    simulation_id,
                    episode_num,
                    self.agent.get_checkpoint_state() if hasattr(self.agent, "get_checkpoint_state") else {
                        "online_net":  self.agent.online_net.state_dict(),
                        "target_net":  self.agent.target_net.state_dict(),
                        "optimizer":   self.agent.optimizer.state_dict(),
                        "step_count":  self.agent.step_count,
                        "obs_version": "v5_28dim_forecast",
                    },
                )
                if self.app_state and hasattr(self.app_state, "sim_agent"):
                    sim_agent = self.app_state.sim_agent
                    sim_agent.online_net.load_state_dict(self.agent.online_net.state_dict())
                    sim_agent.target_net.load_state_dict(self.agent.target_net.state_dict())
                    logger.info(
                        "Synced sim_agent weights from training_agent at episode %d",
                        episode_num,
                    )

                avg_reward = (
                    sum(m["reward"] for m in _recent_rewards) / len(_recent_rewards)
                    if _recent_rewards else total_reward
                )
                await asyncio.to_thread(
                    self.supabase_service.save_model_metadata,
                    simulation_id,
                    episode_num,
                    avg_reward,
                    self.epsilon,
                    episode_num,
                )
                await self.ws_broadcast_fn(
                    {
                        "type":     "checkpoint_saved",
                        "model_id": simulation_id,
                        "episode":  episode_num,
                    }
                )

        self.is_training = False

    def stop(self) -> None:
        self.is_training = False

    def get_status(self) -> dict:
        return {
            "current_episode": self.current_episode,
            "epsilon":         self.epsilon,
            "is_training":     self.is_training,
        }
