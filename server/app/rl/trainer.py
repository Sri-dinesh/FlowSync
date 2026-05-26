import asyncio
from typing import Any, Awaitable, Callable, Optional

from .dqn_agent import DQNAgent
from .hyperparams import HyperParams
from ..simulation.environment import TrafficEnv


class Trainer:
    def __init__(
        self,
        env: TrafficEnv,
        agent: DQNAgent,
        supabase_service: Any,
        model_service: Any,
        ws_broadcast_fn: Callable[[dict], Awaitable[None]],
        hyperparams: Optional[HyperParams] = None,
    ) -> None:
        self.env = env
        self.agent = agent
        self.supabase_service = supabase_service
        self.model_service = model_service
        self.ws_broadcast_fn = ws_broadcast_fn
        self.hyperparams = hyperparams or HyperParams()
        self.is_training = False
        self.current_episode = 0
        self.epsilon = self.hyperparams.epsilon_start

    async def train(self, simulation_id: str, num_episodes: int) -> None:
        self.is_training = True
        self.current_episode = 0
        self.epsilon = self.hyperparams.epsilon_start

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

            for step in range(self.hyperparams.max_steps_per_episode):
                if not self.is_training:
                    stopped_early = True
                    break

                action = self.agent.select_action(state, self.epsilon)
                next_state, reward, terminated, truncated, _ = self.env.step(action)
                done = terminated or truncated

                self.agent.replay_buffer.push(state, action, reward, next_state, done)

                if len(self.agent.replay_buffer) >= 1000:
                    batch = self.agent.replay_buffer.sample(self.hyperparams.batch_size)
                    loss_value = await asyncio.to_thread(self.agent.train_step, batch)

                if step % self.hyperparams.target_update_freq == 0:
                    self.agent.sync_target_network()

                total_reward += reward
                state = next_state
                steps = step + 1

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

            if simulation_id:
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

            if simulation_id and episode_num % 50 == 0:
                await asyncio.to_thread(
                    self.model_service.save_checkpoint,
                    simulation_id,
                    episode_num,
                    self.agent.online_net.state_dict(),
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
