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

from .dqn_agent import DQNAgent
from .hyperparams import HyperParams
from ..simulation.environment import TrafficEnv
from ..simulation.greedy_teacher import GreedyTeacher
from ..simulation.curriculum import TrainingCurriculum
from ..simulation.spawner import SCENARIO_PROFILES
from ..simulation.benchmark_harness import DeterministicEvaluator

logger = logging.getLogger(__name__)

# Seed buffer with demonstrations before RL to accelerate early convergence.
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
        if self.is_training:
            raise RuntimeError("A training run is already active")
        if is_finetune and (not resume_model_id or not resume_model_id.strip()):
            raise ValueError("Fine-tuning requires a parent model checkpoint")
        self.is_training = True
        try:
            await self._train_run(simulation_id,num_episodes,resume_model_id,resume_episode,
                is_finetune,finetune_scenario,finetune_lr,finetune_epsilon,custom_profile)
        finally:
            self.is_training = False

    def _publish_inference(self, candidate: DQNAgent, model_id: str, episode: int, slot: int) -> None:
        """Publish a staged snapshot without mutating a captured inference agent."""
        if self.app_state is not None and hasattr(self.app_state,"sim_agent"):
            self.app_state.sim_agent = candidate
            self.app_state.active_model_id = model_id
            self.app_state.active_model_episode = episode
            self.app_state.active_model_checkpoint_slot = slot

    async def _train_run(
        self, simulation_id: str, num_episodes: int, resume_model_id: Optional[str],
        resume_episode: Optional[int], is_finetune: bool, finetune_scenario: str,
        finetune_lr: float, finetune_epsilon: float, custom_profile: Optional[Dict[str, Any]],
    ) -> None:
        from ..services.checkpoint_loading import load_website_agent, parse_model_request, select_checkpoint

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

        start_episode = 0
        base_model_id = None
        self.resume_checkpoint_slot = None
        if resume_model_id:
            try:
                base_model_id,requested_slot = parse_model_request(resume_model_id,resume_episode)
                checkpoints = await asyncio.to_thread(self.model_service.list_checkpoints,base_model_id)
                slot = select_checkpoint(checkpoints,requested_slot)
                chk_data = await asyncio.to_thread(self.model_service.load_checkpoint,base_model_id,slot)
                candidate,start_episode = load_website_agent(chk_data)
                inference,_ = load_website_agent(chk_data)
                if candidate.obs_version != self.hyperparams.OBS_VERSION:
                    raise ValueError("Training observation configuration differs from checkpoint")
                if is_finetune:
                    candidate.prepare_for_finetuning(learning_rate=finetune_lr)
                candidate.online_net.train()
                self.agent = candidate
                self.resume_checkpoint_slot = slot
                if self.app_state is not None:
                    self.app_state.training_agent = candidate
                self._publish_inference(inference,base_model_id,start_episode,slot)

                logger.info(
                    "Successfully loaded checkpoint for model %s (episode %d) for %s",
                    base_model_id,
                    start_episode,
                    "fine-tuning" if is_finetune else "resumed training",
                )
            except Exception as load_err:
                raise RuntimeError(
                    f"Cannot resume {resume_model_id!r}: checkpoint load failed: {load_err}"
                ) from load_err

            if is_finetune:
                self.parent_model_id = base_model_id
                self.parent_episode = start_episode

                scenario_slug = finetune_scenario.lower().replace(" ", "_")
                if finetune_scenario == "custom" and custom_profile and custom_profile.get("name"):
                    scenario_slug = "custom_" + custom_profile["name"].lower().strip().replace(" ","_")[:20]
                simulation_id = f"{base_model_id}-ft-{scenario_slug}"
                if self.app_state:
                    self.app_state.current_simulation_id = simulation_id

                self.env.set_traffic_profile(profile)

                start_episode = 0
                total_target_episodes = num_episodes

                self.epsilon = finetune_epsilon
                decay_steps = max(1, int(num_episodes * 0.75))
                self.finetune_decay = (0.05 / max(0.06, finetune_epsilon)) ** (1.0 / decay_steps)
            else:
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
            self.agent.reset_for_fresh_training()
            self.env.set_traffic_profile(SCENARIO_PROFILES["uniform"])
            total_target_episodes = num_episodes
            self.epsilon = self.hyperparams.epsilon_start

        self.start_episode = start_episode
        self.current_episode = start_episode
        self.target_episodes = total_target_episodes

        curriculum = TrainingCurriculum(
            env=self.env,
            total_episodes=total_target_episodes,
        ) if (self.enable_curriculum and not self.is_finetune) else None

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
                "parent_checkpoint_slot": self.resume_checkpoint_slot,
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

        if self.is_resumed:
            await self.ws_broadcast_fn({
                "type":                  "training_resumed",
                "model_id":              base_model_id,
                "start_episode":         start_episode,
                "checkpoint_slot":       self.resume_checkpoint_slot,
                "num_episodes":          num_episodes,
                "total_target_episodes": total_target_episodes,
                "message":               f"Resumed model training from episode {start_episode} for +{num_episodes} episodes (target: {total_target_episodes}).",
            })

        _recent_rewards: list[dict] = []
        _REWARD_WINDOW = 50

        best_avg_wait: float = float("inf")
        best_validation_queue_area: float = float("inf")
        best_episode: int = 0

        for episode_index in range(num_episodes):
            if not self.is_training:
                break

            episode_num = start_episode + episode_index + 1
            self.current_episode = episode_num

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

            self.agent.replay_buffer.anneal_beta(episode_num, total_target_episodes)

            decision_step = 0
            while self.env.intersection.timestep < self.env.max_steps:
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(
                    state, self.epsilon, valid_action_mask=action_mask
                )

                next_state, reward, terminated, truncated, info = self.env.step_decision(action)
                done = terminated or truncated

            # Record executed action to account for physical watchdog overrides.
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

            # Yield periodically to event loop so WebSocket keep-alives process smoothly.
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

            episode_telemetry = self.env.get_episode_telemetry()
            reward_components = episode_telemetry.get("reward_components", {})
            watchdog_rate = episode_telemetry.get("watchdog_override_rate", 0.0)
            watchdog_count = episode_telemetry.get("watchdog_override_count", 0)

            _recent_rewards.append({"reward": total_reward})
            if len(_recent_rewards) > _REWARD_WINDOW:
                _recent_rewards.pop(0)

            persist_remote = bool(simulation_id) and not simulation_id.startswith("local-")

            if persist_remote:
            # Dispatch remote persistence in background so latency does not block training.
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
                    "total_train_steps":       self.agent.total_train_steps,
                    "reward_components":       reward_components,
                    "watchdog_override_rate":  watchdog_rate,
                    "watchdog_override_count": watchdog_count,
                    "curriculum":              curriculum_status,
                    "q_stats":                 getattr(self.agent, "latest_q_stats", {}),
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
                    chk_state["parent_checkpoint_slot"] = self.resume_checkpoint_slot
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
                    await asyncio.to_thread(
                        self.model_service.save_checkpoint,
                        simulation_id,
                        0,  # 0 indicates best checkpoint
                        chk_state,
                    )

                inference,_ = load_website_agent(chk_state)
                self._publish_inference(inference,simulation_id,episode_num,episode_num)

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

    def stop(self) -> None:
        self.is_training = False

    def get_status(self) -> dict:
        return {
            "current_episode":   self.current_episode,
            "start_episode":     getattr(self, "start_episode", 0),
            "target_episodes":   getattr(self, "target_episodes", 0),
            "is_resumed":        getattr(self, "is_resumed", False),
            "resume_model_id":   getattr(self, "resume_model_id", None),
            "resume_checkpoint_slot": getattr(self,"resume_checkpoint_slot",None),
            "is_finetuned":      getattr(self, "is_finetune", False),
            "finetune_scenario": getattr(self, "finetune_scenario", None),
            "parent_model_id":   getattr(self, "parent_model_id", None),
            "parent_episode":    getattr(self, "parent_episode", None),
            "epsilon":           self.epsilon,
            "is_training":       self.is_training,
        }
