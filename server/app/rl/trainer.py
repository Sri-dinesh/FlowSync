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
        self.start_episode = 0
        self.target_episodes = 0
        self.is_resumed = False
        self.resume_model_id: Optional[str] = None
        self.epsilon = self.hyperparams.epsilon_start
        self.enable_curriculum = enable_curriculum
        self.enable_greedy_warmup = enable_greedy_warmup

    async def train(
        self,
        simulation_id: str,
        num_episodes: int,
        resume_model_id: Optional[str] = None,
        resume_episode: Optional[int] = None,
    ) -> None:
        self.is_training = True
        self.is_resumed = bool(resume_model_id)
        self.resume_model_id = resume_model_id

        # ── Checkpoint & Resume Loading ────────────────────────────────────
        start_episode = 0
        base_model_id = None
        if resume_model_id:
            if ":" in resume_model_id:
                base_model_id, ep_str = resume_model_id.split(":", 1)
                ep_clean = ep_str.replace("checkpoint_", "").replace(".pt", "")
                if ep_clean.isdigit() and resume_episode is None:
                    resume_episode = int(ep_clean)
            else:
                base_model_id = resume_model_id

            if resume_episode is None:
                try:
                    checkpoints = await asyncio.to_thread(self.model_service.list_checkpoints, base_model_id)
                    eps_found = []
                    for cp in checkpoints:
                        fn = cp.split("/")[-1]
                        if fn.startswith("checkpoint_") and fn.endswith(".pt"):
                            t = fn[len("checkpoint_"):-len(".pt")]
                            if t.isdigit():
                                eps_found.append(int(t))
                    if eps_found:
                        resume_episode = max(eps_found)
                except Exception as list_err:
                    logger.warning("Could not list checkpoints for resume model %s: %s", base_model_id, list_err)

            start_episode = resume_episode or 0

            # Load checkpoint state into training agent and sync sim_agent
            try:
                chk_data = await asyncio.to_thread(self.model_service.load_checkpoint, base_model_id, start_episode)
                if isinstance(chk_data, dict) and "online_net" in chk_data:
                    self.agent.online_net.load_state_dict(chk_data["online_net"])
                    self.agent.target_net.load_state_dict(chk_data.get("target_net", chk_data["online_net"]))
                    if "optimizer" in chk_data and chk_data["optimizer"]:
                        try:
                            self.agent.optimizer.load_state_dict(chk_data["optimizer"])
                        except Exception as opt_err:
                            logger.warning("Could not restore optimizer state: %s", opt_err)
                    if "step_count" in chk_data:
                        self.agent.step_count = chk_data["step_count"]
                    if "total_train_steps" in chk_data:
                        self.agent.total_train_steps = chk_data["total_train_steps"]
                else:
                    self.agent.online_net.load_state_dict(chk_data)
                    self.agent.sync_target_network()
                self.agent.target_net.eval()

                # Sync inference agent
                if self.app_state and hasattr(self.app_state, "sim_agent"):
                    self.app_state.sim_agent.online_net.load_state_dict(self.agent.online_net.state_dict())
                    self.app_state.sim_agent.target_net.load_state_dict(self.agent.target_net.state_dict())
                    self.app_state.active_model_id = base_model_id
                    self.app_state.active_model_episode = start_episode

                logger.info(
                    "Successfully loaded checkpoint for model %s (episode %d) to resume training",
                    base_model_id,
                    start_episode,
                )
            except Exception as load_err:
                logger.error("Failed to load checkpoint for resume model %s (ep %s): %s", base_model_id, start_episode, load_err)

            # Preserve the model's simulation_id so newly saved checkpoints live under the same model folder
            if not simulation_id or simulation_id.startswith("local-"):
                simulation_id = base_model_id

        self.start_episode = start_episode
        self.current_episode = start_episode
        total_target_episodes = start_episode + num_episodes
        self.target_episodes = total_target_episodes

        # ── Calculate Epsilon for resumed or fresh training ─────────────────
        if start_episode > 0:
            # Continue the mathematical exponential decay from the start episode
            decayed_eps = self.hyperparams.epsilon_start * (self.hyperparams.epsilon_decay ** start_episode)
            self.epsilon = max(self.hyperparams.epsilon_end, decayed_eps)
        else:
            self.epsilon = self.hyperparams.epsilon_start

        # ── Task 5.2: Curriculum setup ─────────────────────────────────────
        curriculum = TrainingCurriculum(
            env=self.env,
            total_episodes=total_target_episodes,
        ) if self.enable_curriculum else None

        # ── Task 5.1: Greedy demonstration warm-start ──────────────────────
        # Only warm up when starting fresh with an empty buffer; skip if resumed
        if not self.is_resumed and self.enable_greedy_warmup and len(self.agent.replay_buffer) < self.hyperparams.MIN_REPLAY_SIZE:
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
        elif self.is_resumed:
            logger.info(
                "Skipping greedy warmup: Resuming from episode %d with pre-trained agent.",
                start_episode,
            )
        elif self.enable_greedy_warmup:
            logger.info(
                "Skipping greedy warmup — buffer already has %d/%d samples.",
                len(self.agent.replay_buffer),
                self.hyperparams.MIN_REPLAY_SIZE,
            )

        # Broadcast resume event notification
        if self.is_resumed:
            await self.ws_broadcast_fn({
                "type":                  "training_resumed",
                "model_id":              base_model_id,
                "start_episode":         start_episode,
                "num_episodes":          num_episodes,
                "total_target_episodes": total_target_episodes,
                "message":               f"Resumed model training from episode {start_episode} for +{num_episodes} episodes (target: {total_target_episodes}).",
            })

        # Rolling window of recent rewards for model metadata avg_reward
        _recent_rewards: list[dict] = []
        _REWARD_WINDOW = 50

        # TR-03: Best-checkpoint tracking by validation delay
        best_avg_wait: float = float("inf")
        best_episode: int = 0

        for episode_index in range(num_episodes):
            if not self.is_training:
                break

            episode_num = start_episode + episode_index + 1
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

            # Anneal PER beta over training with global target
            self.agent.replay_buffer.anneal_beta(episode_num, total_target_episodes)

            for step in range(self.hyperparams.MAX_STEPS_PER_EPISODE):
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(state, self.epsilon)

                # ── Step environment (fast in-thread execution) ─────────────
                next_state, reward, terminated, truncated, info = self.env.step(action)
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
                    loss_value, td_errors = self.agent.train_step(batch)

                if self.agent.step_count % self.hyperparams.TARGET_UPDATE_FREQ == 0:
                    self.agent.sync_target_network()

                total_reward += reward
                state = next_state
                steps = step + 1

                # Periodically yield to event loop so WebSocket keep-alives and commands process smoothly
                if step % 25 == 0:
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

            # TR-03: Track best-checkpoint by minimum average wait time
            is_new_best = False
            if avg_wait > 0 and avg_wait < best_avg_wait and episode_num >= 10:
                best_avg_wait = avg_wait
                best_episode = episode_num
                is_new_best = True
                logger.info(
                    "New best validation delay: %.2fs at episode %d",
                    best_avg_wait,
                    best_episode,
                )

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
                # Dispatch remote save in background so high Supabase cloud network latency
                # does not block subsequent training episodes
                asyncio.create_task(
                    asyncio.to_thread(
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
                )

            is_last_episode = episode_index == num_episodes - 1

            # ── Broadcast episode metrics ────────────────────────────────────
            await self.ws_broadcast_fn(
                {
                    "episode":                 episode_num,
                    "start_episode":           start_episode,
                    "target_episodes":         total_target_episodes,
                    "is_resumed":              self.is_resumed,
                    "resume_model_id":         self.resume_model_id,
                    "total_reward":            total_reward,
                    "avg_wait_time":           avg_wait,
                    "throughput":              throughput,
                    "epsilon":                 self.epsilon,
                    "loss":                    loss_value,
                    "steps":                   steps,
                    "buffer_ready":            self.agent.replay_buffer.is_ready,
                    "is_training":             False if is_last_episode else self.is_training,
                    "total_train_steps":       self.agent.total_train_steps,  # BUG-B visibility
                    # Task 0.2: reward component telemetry
                    "reward_components":       reward_components,
                    "watchdog_override_rate":  watchdog_rate,
                    "watchdog_override_count": watchdog_count,
                    # Task 5.2: curriculum info
                    "curriculum":              curriculum_status,
                    # P-01/P-02/P-03: Q-value health monitoring
                    "q_stats":                 getattr(self.agent, "latest_q_stats", {}),
                    # TR-03: Best-checkpoint tracking
                    "best_avg_wait":           best_avg_wait if best_avg_wait < float("inf") else None,
                    "best_episode":            best_episode if best_episode > 0 else None,
                    "is_new_best":             is_new_best,
                }
            )

            is_stopping = not self.is_training
            should_save_checkpoint = simulation_id and (
                episode_num % 50 == 0 or is_last_episode or is_stopping
            )

            # Sync active inference agent immediately whenever a new best or milestone occurs
            if (is_new_best or should_save_checkpoint) and self.app_state and hasattr(self.app_state, "sim_agent"):
                sim_agent = self.app_state.sim_agent
                sim_agent.online_net.load_state_dict(self.agent.online_net.state_dict())
                sim_agent.target_net.load_state_dict(self.agent.target_net.state_dict())
                logger.info(
                    "Synced sim_agent weights from training_agent at episode %d",
                    episode_num,
                )

            if should_save_checkpoint:
                chk_state = self.agent.get_checkpoint_state() if hasattr(self.agent, "get_checkpoint_state") else {
                    "online_net":  self.agent.online_net.state_dict(),
                    "target_net":  self.agent.target_net.state_dict(),
                    "optimizer":   self.agent.optimizer.state_dict(),
                    "step_count":  self.agent.step_count,
                    "obs_version": "v5_28dim_forecast",
                }
                chk_state["is_best"] = is_new_best
                chk_state["best_avg_wait"] = best_avg_wait
                chk_state["episode"] = episode_num
                await asyncio.to_thread(
                    self.model_service.save_checkpoint,
                    simulation_id,
                    episode_num,
                    chk_state,
                )
                if is_new_best:
                    # Save dedicated 'best' checkpoint file
                    await asyncio.to_thread(
                        self.model_service.save_checkpoint,
                        simulation_id,
                        0,  # 0 indicates best checkpoint
                        chk_state,
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
            "start_episode":   getattr(self, "start_episode", 0),
            "target_episodes": getattr(self, "target_episodes", 0),
            "is_resumed":      getattr(self, "is_resumed", False),
            "resume_model_id": getattr(self, "resume_model_id", None),
            "epsilon":         self.epsilon,
            "is_training":     self.is_training,
        }
