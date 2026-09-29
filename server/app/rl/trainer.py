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
from typing import Any, Awaitable, Callable, Dict, Optional

import numpy as np

from .dqn_agent import DQNAgent
from .hyperparams import HyperParams
from ..simulation.environment import TrafficEnv
from ..simulation.greedy_teacher import GreedyTeacher
from ..simulation.curriculum import TrainingCurriculum
from ..simulation.spawner import SCENARIO_PROFILES
from ..simulation.benchmark_harness import DeterministicEvaluator

logger = logging.getLogger(__name__)

# Greedy warm-start: number of demonstration transitions to collect before RL
_GREEDY_WARMUP_STEPS = 3000
_GREEDY_PRETRAIN_UPDATES = 500


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
        self.is_finetune = False
        self.finetune_scenario: Optional[str] = None
        self.finetune_lr: float = 1e-4
        self.finetune_epsilon: float = 0.25
        self.finetune_decay: float = 0.98
        self.parent_model_id: Optional[str] = None
        self.parent_episode: Optional[int] = None
        self.epsilon = self.hyperparams.epsilon_start
        self.enable_curriculum = enable_curriculum
        self.enable_greedy_warmup = enable_greedy_warmup

    def _pretrain_on_demonstrations(self, updates: int) -> None:
        """Fit the initialized Q-network to demonstration transitions first."""
        if not self.agent.replay_buffer.is_ready:
            return
        for _ in range(max(0, updates)):
            batch = self.agent.replay_buffer.sample(self.hyperparams.BATCH_SIZE)
            self.agent.train_step(batch)
            if self.agent.step_count % self.hyperparams.TARGET_UPDATE_FREQ == 0:
                self.agent.sync_target_network()

    async def _broadcast_warmup_progress(
        self,
        phase: str,
        completed: int,
        total: int,
    ) -> None:
        await self.ws_broadcast_fn({
            "type": "warmup_progress",
            "phase": phase,
            "completed": completed,
            "total": total,
            "is_training": True,
            "message": (
                f"Collecting demonstrations: {completed}/{total}"
                if phase == "collect"
                else f"Pretraining network: {completed}/{total}"
            ),
        })

    async def train(
        self,
        simulation_id: str,
        num_episodes: int,
        resume_model_id: Optional[str] = None,
        resume_episode: Optional[int] = None,
        is_finetune: bool = False,
        finetune_scenario: str = "rush_hour",
        finetune_lr: float = 1e-4,
        finetune_epsilon: float = 0.25,
        custom_profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.is_training = True
        self.is_finetune = is_finetune
        self.finetune_scenario = finetune_scenario
        self.finetune_lr = finetune_lr
        self.finetune_epsilon = finetune_epsilon
        self.custom_profile = custom_profile
        self.is_resumed = bool(resume_model_id) and not is_finetune
        self.resume_model_id = resume_model_id
        self.parent_model_id = None
        self.parent_episode = None
        self.finetune_decay = 0.98

        profile = None
        if self.is_finetune:
            if finetune_scenario == "custom" and custom_profile:
                profile = custom_profile
            else:
                profile = SCENARIO_PROFILES.get(finetune_scenario, SCENARIO_PROFILES["rush_hour"])
        profile_name = (
            profile.get("name", "Custom") if isinstance(profile, dict)
            else getattr(profile, "name", "Custom")
        )
        profile_lambda = (
            float(profile.get("base_lambda", 0.85)) if isinstance(profile, dict)
            else float(getattr(profile, "base_lambda", 0.85))
        )

        # ── Checkpoint & Resume / Fine-Tune Loading ─────────────────────────
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
                if (
                    chk_data.get("obs_version") != self.hyperparams.OBS_VERSION
                    or chk_data.get("reward_version") != "v4_incremental_delay"
                ):
                    raise ValueError(
                        "legacy checkpoint is incompatible with corrected v6 training"
                    )
                if isinstance(chk_data, dict) and "online_net" in chk_data:
                    self.agent.online_net.load_state_dict(chk_data["online_net"])
                    self.agent.target_net.load_state_dict(chk_data.get("target_net", chk_data["online_net"]))
                    if not is_finetune and "optimizer" in chk_data and chk_data["optimizer"]:
                        try:
                            self.agent.optimizer.load_state_dict(chk_data["optimizer"])
                        except Exception as opt_err:
                            logger.warning("Could not restore optimizer state: %s", opt_err)
                    if not is_finetune and "step_count" in chk_data:
                        self.agent.step_count = chk_data["step_count"]
                    if not is_finetune and "total_train_steps" in chk_data:
                        self.agent.total_train_steps = chk_data["total_train_steps"]
                    # checkpoint_0.pt is an alias; continue numbering from the
                    # real winning episode stored inside the checkpoint.
                    start_episode = int(chk_data.get("episode", start_episode))
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
                    "Successfully loaded checkpoint for model %s (episode %d) for %s",
                    base_model_id,
                    start_episode,
                    "fine-tuning" if is_finetune else "resumed training",
                )
            except Exception as load_err:
                self.is_training = False
                raise RuntimeError(
                    f"Cannot resume model {base_model_id!r} at episode "
                    f"{start_episode}: checkpoint load failed"
                ) from load_err

            if is_finetune:
                self.parent_model_id = base_model_id
                self.parent_episode = start_episode
                # Re-initialize optimizer with reduced LR and reset replay buffer
                self.agent.prepare_for_finetuning(learning_rate=finetune_lr)

                # Fork simulation_id into branched model name
                clean_base = base_model_id.split(":")[0] if ":" in base_model_id else base_model_id
                scenario_slug = finetune_scenario.lower().replace(" ", "_")
                simulation_id = f"{clean_base}-ft-{scenario_slug}"
                if self.app_state:
                    self.app_state.current_simulation_id = simulation_id

                # Assign traffic profile
                self.env.set_traffic_profile(profile)

                # Episode indexing: fine-tune runs for 1..num_episodes
                start_episode = 0
                total_target_episodes = num_episodes

                # Epsilon schedule: warm reset to finetune_epsilon, decaying to 0.05
                self.epsilon = finetune_epsilon
                decay_steps = max(1, int(num_episodes * 0.75))
                self.finetune_decay = (0.05 / max(0.06, finetune_epsilon)) ** (1.0 / decay_steps)
            else:
                # Normal resume: preserve simulation_id
                if not simulation_id or simulation_id.startswith("local-"):
                    simulation_id = base_model_id
                self.env.set_traffic_profile(SCENARIO_PROFILES["uniform"])
                total_target_episodes = start_episode + num_episodes
                if start_episode > 0:
                    decayed_eps = self.hyperparams.epsilon_start * (self.hyperparams.epsilon_decay ** start_episode)
                    self.epsilon = max(self.hyperparams.epsilon_end, decayed_eps)
                else:
                    self.epsilon = self.hyperparams.epsilon_start
        else:
            # Fresh training
            self.agent.reset_for_fresh_training()
            self.env.set_traffic_profile(SCENARIO_PROFILES["uniform"])
            total_target_episodes = num_episodes
            self.epsilon = self.hyperparams.epsilon_start

        self.start_episode = start_episode
        self.current_episode = start_episode
        self.target_episodes = total_target_episodes

        # ── Task 5.2: Curriculum setup ─────────────────────────────────────
        curriculum = TrainingCurriculum(
            env=self.env,
            total_episodes=total_target_episodes,
        ) if (self.enable_curriculum and not self.is_finetune) else None

        # ── Warm-start Seeding ─────────────────────────────────────────────
        if self.is_finetune and profile:
            logger.info("Fine-tuning: seeding replay buffer with base policy on scenario '%s'...", profile_name)
            state, reset_info = self.env.reset_to_decision()
            action_mask = reset_info["valid_action_mask"]
            seed_steps = min(self.hyperparams.MIN_REPLAY_SIZE, 600)
            for _ in range(seed_steps):
                action = self.agent.select_action(
                    state, epsilon=self.epsilon, valid_action_mask=action_mask
                )
                next_state, reward, terminated, truncated, info = self.env.step_decision(action)
                executed_action = info.get("executed_action", action)
                next_action_mask = info["valid_action_mask"]
                self.agent.replay_buffer.push(
                    state,
                    executed_action,
                    reward,
                    next_state,
                    terminated,
                    valid_action_mask=action_mask,
                    next_valid_action_mask=next_action_mask,
                    bootstrap_discount=info["bootstrap_discount"],
                )
                if terminated or truncated:
                    state, reset_info = self.env.reset_to_decision()
                    action_mask = reset_info["valid_action_mask"]
                else:
                    state = next_state
                    action_mask = next_action_mask

            await self.ws_broadcast_fn({
                "type": "warmup_complete",
                "message": f"Pre-trained policy seeded buffer with {seed_steps} transitions on scenario '{profile_name}'.",
            })
            await self.ws_broadcast_fn({
                "type":                  "training_finetuned",
                "model_id":              simulation_id,
                "parent_model_id":       self.parent_model_id,
                "parent_episode":        self.parent_episode,
                "scenario":              finetune_scenario,
                "scenario_name":         profile_name,
                "num_episodes":          num_episodes,
                "target_episodes":       num_episodes,
                "learning_rate":         finetune_lr,
                "initial_epsilon":       finetune_epsilon,
                "message":               f"Fine-tuning started for '{profile_name}' ({num_episodes} episodes, α={finetune_lr}, ε={finetune_epsilon}).",
            })
        elif not self.is_resumed and self.enable_greedy_warmup and len(self.agent.replay_buffer) < self.hyperparams.MIN_REPLAY_SIZE:
            teacher = GreedyTeacher(env=self.env)
            logger.info("Starting Greedy teacher warm-start...")
            loop = asyncio.get_running_loop()

            def report_collection(completed: int, total: int) -> None:
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_warmup_progress(
                        "collect", completed, total
                    ),
                    loop,
                )

            await asyncio.to_thread(
                teacher.fill_buffer,
                self.agent.replay_buffer,
                _GREEDY_WARMUP_STEPS,
                42,
                report_collection,
            )
            for completed in range(0, _GREEDY_PRETRAIN_UPDATES, 25):
                batch_updates = min(25, _GREEDY_PRETRAIN_UPDATES - completed)
                await asyncio.to_thread(
                    self._pretrain_on_demonstrations,
                    batch_updates,
                )
                await self._broadcast_warmup_progress(
                    "pretrain",
                    completed + batch_updates,
                    _GREEDY_PRETRAIN_UPDATES,
                )
            await self.ws_broadcast_fn({
                "type":    "warmup_complete",
                "message": f"Greedy teacher seeded buffer with {_GREEDY_WARMUP_STEPS} transitions.",
            })
        elif self.is_resumed:
            if (
                self.enable_greedy_warmup
                and len(self.agent.replay_buffer) < self.hyperparams.MIN_REPLAY_SIZE
            ):
                teacher = GreedyTeacher(env=self.env)
                await asyncio.to_thread(
                    teacher.fill_buffer,
                    self.agent.replay_buffer,
                    self.hyperparams.MIN_REPLAY_SIZE,
                )
                await asyncio.to_thread(
                    self._pretrain_on_demonstrations,
                    _GREEDY_PRETRAIN_UPDATES,
                )
            self.epsilon = max(0.20, self.epsilon)
            logger.info(
                "Resumed episode %d with replay re-warm and epsilon %.2f.",
                start_episode,
                self.epsilon,
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
        best_validation_queue_area: float = float("inf")
        best_episode: int = 0

        for episode_index in range(num_episodes):
            if not self.is_training:
                break

            episode_num = start_episode + episode_index + 1
            self.current_episode = episode_num

            # ── Curriculum or Scenario Status ──────────────────────────────
            curriculum_status = {}
            if curriculum is not None and not self.is_finetune:
                stage_name, applied_lambda = curriculum.apply(episode_num)
                curriculum_status = {
                    "stage": stage_name,
                    "lambda": applied_lambda,
                }
            elif self.is_finetune and profile:
                curriculum_status = {
                    "stage": f"Fine-Tuning: {profile_name}",
                    "lambda": profile_lambda,
                    "scenario": self.finetune_scenario,
                }

            state, reset_info = self.env.reset_to_decision()
            action_mask = reset_info["valid_action_mask"]
            total_reward = 0.0
            loss_value: Optional[float] = None
            steps = 0
            stopped_early = False

            # Anneal PER beta over training with global target
            self.agent.replay_buffer.anneal_beta(episode_num, total_target_episodes)

            decision_step = 0
            while self.env.intersection.timestep < self.env.max_steps:
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(
                    state, self.epsilon, valid_action_mask=action_mask
                )

                # ── Step environment (fast in-thread execution) ─────────────
                next_state, reward, terminated, truncated, info = self.env.step_decision(action)
                done = terminated or truncated

                # ── BUG-01 FIX: Use executed_action for replay buffer push ──
                executed_action = info.get("executed_action", action)

                # ── Task 2.1 (Semi-MDP): Only push causal transitions ────────
                # BUG-E FIX: subsample GREEN steps — store 1 per 10 (1 simulated second).
                # Old: push every GREEN step (~680/ep) — redundant near-identical transitions.
                # Now: push every 10th GREEN step (~65/ep) — informative, diverse transitions.
                next_action_mask = info["valid_action_mask"]
                self.agent.replay_buffer.push(
                    state,
                    executed_action,
                    reward,
                    next_state,
                    terminated,
                    valid_action_mask=action_mask,
                    next_valid_action_mask=next_action_mask,
                    bootstrap_discount=info["bootstrap_discount"],
                )

                # ── Train step ───────────────────────────────────────────────
                if (
                    self.agent.replay_buffer.is_ready
                    and decision_step % self.hyperparams.TRAIN_EVERY_N_STEPS == 0
                ):
                    batch = self.agent.replay_buffer.sample(self.hyperparams.BATCH_SIZE)
                    loss_value, td_errors = self.agent.train_step(batch)

                if (
                    self.agent.step_count > 0
                    and self.agent.step_count % self.hyperparams.TARGET_UPDATE_FREQ == 0
                ):
                    self.agent.sync_target_network()

                total_reward += reward
                state = next_state
                action_mask = next_action_mask
                decision_step += 1
                steps = self.env.intersection.timestep

                # Periodically yield to event loop so WebSocket keep-alives and commands process smoothly
                if decision_step % 10 == 0:
                    await asyncio.sleep(0)

                if done:
                    break

            if stopped_early:
                break

            current_decay = self.finetune_decay if self.is_finetune else self.hyperparams.epsilon_decay
            self.epsilon = max(
                self.hyperparams.epsilon_end,
                self.epsilon * current_decay,
            )

            avg_wait = self.env.intersection.get_avg_wait_time()
            throughput = self.env.intersection.total_passed

            is_last_episode = episode_index == num_episodes - 1
            validation_metrics: Dict[str, Any] = {}
            is_new_best = False
            if episode_num % 25 == 0 or is_last_episode:
                evaluator = DeterministicEvaluator(
                    agent=self.agent,
                    mode="ai",
                    spawn_lambda=0.5,
                )
                validation = await asyncio.to_thread(
                    evaluator.run_multi_seed,
                    1200,
                    [104729, 130363, 155921],
                )
                validation_metrics = {
                    "mean_queue_area": validation.mean_queue_area,
                    "mean_avg_wait": validation.mean_avg_wait,
                    "mean_p95_delay": validation.mean_p95_delay,
                    "mean_throughput": validation.mean_throughput,
                }
                if validation.mean_queue_area < best_validation_queue_area:
                    best_validation_queue_area = validation.mean_queue_area
                    best_avg_wait = validation.mean_avg_wait
                    best_episode = episode_num
                    is_new_best = True
                    logger.info(
                        "New held-out best: queue_area=%.2f wait=%.2fs at episode %d",
                        best_validation_queue_area,
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

            effective_scenario = (
                self.custom_profile.get("name", "Custom")
                if self.is_finetune and self.finetune_scenario == "custom" and self.custom_profile
                else self.finetune_scenario
            )

            # ── Broadcast episode metrics ────────────────────────────────────
            await self.ws_broadcast_fn(
                {
                    "episode":                 episode_num,
                    "start_episode":           start_episode,
                    "target_episodes":         total_target_episodes,
                    "is_resumed":              self.is_resumed,
                    "resume_model_id":         self.resume_model_id,
                    "is_finetuned":            self.is_finetune,
                    "finetune_scenario":       effective_scenario,
                    "parent_model_id":         self.parent_model_id,
                    "parent_episode":          self.parent_episode,
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
                    "validation":              validation_metrics,
                }
            )

            is_stopping = not self.is_training
            save_interval = 25 if self.is_finetune else 50
            should_save_checkpoint = simulation_id and (
                episode_num % save_interval == 0
                or is_last_episode
                or is_stopping
                or is_new_best
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
                    "obs_version": self.hyperparams.OBS_VERSION,
                }
                chk_state["is_best"] = is_new_best
                chk_state["best_avg_wait"] = best_avg_wait
                chk_state["best_validation_queue_area"] = best_validation_queue_area
                chk_state["validation_metrics"] = validation_metrics
                chk_state["episode"] = episode_num
                if self.is_finetune:
                    chk_state["is_finetuned"] = True
                    chk_state["parent_model_id"] = self.parent_model_id
                    chk_state["parent_episode"] = self.parent_episode
                    chk_state["scenario"] = effective_scenario
                    if self.custom_profile:
                        chk_state["custom_profile"] = self.custom_profile

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
            "current_episode":   self.current_episode,
            "start_episode":     getattr(self, "start_episode", 0),
            "target_episodes":   getattr(self, "target_episodes", 0),
            "is_resumed":        getattr(self, "is_resumed", False),
            "resume_model_id":   getattr(self, "resume_model_id", None),
            "is_finetuned":      getattr(self, "is_finetune", False),
            "finetune_scenario": getattr(self, "finetune_scenario", None),
            "parent_model_id":   getattr(self, "parent_model_id", None),
            "parent_episode":    getattr(self, "parent_episode", None),
            "epsilon":           self.epsilon,
            "is_training":       self.is_training,
        }
