import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from .dqn_agent import DQNAgent
from .hyperparams import HyperParams
from ..simulation.environment import TrafficEnv

logger = logging.getLogger(__name__)

# Yield to the event loop every N steps to keep WebSocket connections alive.
_YIELD_EVERY_N_STEPS = 10
# Only run a train_step every N steps to avoid saturating the CPU on free tier.
_TRAIN_EVERY_N_STEPS = 4


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

    async def train(self, simulation_id: str, num_episodes: int) -> None:
        self.is_training = True
        self.current_episode = 0
        self.epsilon = self.hyperparams.epsilon_start

        # Rolling window of recent rewards for model metadata
        _recent_rewards: list[dict] = []
        _REWARD_WINDOW = 50

        for episode_index in range(num_episodes):
            if not self.is_training:
                break

            episode_num = episode_index + 1
            self.current_episode = episode_num
            state, _ = self.env.reset()
            total_reward = 0.0
            loss_value: Optional[float] = None
            steps = 0
            stopped_early = False
            done = False

            # Anneal PER beta over training
            self.agent.replay_buffer.anneal_beta(episode_index, num_episodes)

            for step in range(self.hyperparams.MAX_STEPS_PER_EPISODE):
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(state, self.epsilon)
                next_state, reward, terminated, truncated, _ = self.env.step(action)
                done = terminated or truncated

                self.agent.replay_buffer.push(state, action, reward, next_state, terminated)

                # Only train once the buffer is warm and on specific step intervals
                if (
                    self.agent.replay_buffer.is_ready
                    and step % self.hyperparams.TRAIN_EVERY_N_STEPS == 0
                ):
                    batch = self.agent.replay_buffer.sample(self.hyperparams.BATCH_SIZE)
                    loss_value, td_errors = await asyncio.to_thread(self.agent.train_step, batch)

                if self.agent.step_count % self.hyperparams.TARGET_UPDATE_FREQ == 0:
                    self.agent.sync_target_network()

                total_reward += reward
                state = next_state
                steps = step + 1

                # Yield to event loop — more frequently during warmup
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

            # Track rolling rewards for model metadata avg_reward
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
            await self.ws_broadcast_fn(
                {
                    "episode": episode_num,
                    "total_reward": total_reward,
                    "avg_wait_time": avg_wait,
                    "throughput": throughput,
                    "epsilon": self.epsilon,
                    "loss": loss_value,
                    "is_training": False if is_last_episode else self.is_training,
                }
            )

            if simulation_id and (episode_num % 50 == 0 or is_last_episode):
                await asyncio.to_thread(
                    self.model_service.save_checkpoint,
                    simulation_id,
                    episode_num,
                    self.agent.get_checkpoint_state() if hasattr(self.agent, 'get_checkpoint_state') else {
                        'online_net': self.agent.online_net.state_dict(),
                        'target_net': self.agent.target_net.state_dict(),
                        'optimizer': self.agent.optimizer.state_dict(),
                        'step_count': self.agent.step_count,
                        'obs_version': 'v3_20dim_pressure',
                    },
                )
                if self.app_state and hasattr(self.app_state, "sim_agent"):
                    sim_agent = self.app_state.sim_agent
                    sim_agent.online_net.load_state_dict(self.agent.online_net.state_dict())
                    sim_agent.target_net.load_state_dict(self.agent.target_net.state_dict())
                    logger.info(f"Synced sim_agent weights from training_agent at episode {episode_num}")
                
                # Persist metadata row in rl_models so the model appears in the UI
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
                # Notify the frontend that a new checkpoint is available
                await self.ws_broadcast_fn(
                    {
                        "type": "checkpoint_saved",
                        "model_id": simulation_id,
                        "episode": episode_num,
                    }
                )

        self.is_training = False

    def stop(self) -> None:
        self.is_training = False

    def get_status(self) -> dict:
        return {
            "current_episode": self.current_episode,
            "epsilon": self.epsilon,
            "is_training": self.is_training,
        }
