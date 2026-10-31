"""Training checkpoint identity and failure behavior, without traffic collection."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
import torch

from app.rl.dqn_agent import DQNAgent
from app.rl.hyperparams import HyperParams
from app.rl.trainer import Trainer


def training_fixture(monkeypatch, *, stop_after_setup=True):
    agent, inference = DQNAgent(), DQNAgent()
    state = SimpleNamespace(sim_agent=inference,training_agent=agent,
        active_model_id="previous",active_model_episode=12,active_model_checkpoint_slot=12)
    env = MagicMock()
    env.max_steps = 0
    env.intersection.timestep = 0
    env.intersection.total_passed = 0
    env.intersection.get_avg_wait_time.return_value = 0.
    env.get_episode_telemetry.return_value = {}
    env.reset_to_decision.return_value = (np.zeros(28),{"valid_action_mask":np.ones(4,dtype=bool)})
    storage = SimpleNamespace(list_checkpoints=MagicMock(return_value=["checkpoint_0.pt","checkpoint_100.pt"]),
        load_checkpoint=MagicMock(),save_checkpoint=MagicMock())
    persistence = SimpleNamespace(save_episode=MagicMock(),save_model_metadata=MagicMock())
    broadcast = AsyncMock()
    trainer = Trainer(env,agent,persistence,storage,broadcast,app_state=state,
        hyperparams=HyperParams(MIN_REPLAY_SIZE=0),enable_curriculum=False,enable_greedy_warmup=False)
    async def observe(message):
        if stop_after_setup and message.get("type") in ("training_resumed","training_finetuned"):
            trainer.stop()
    broadcast.side_effect = observe
    metrics = SimpleNamespace(mean_queue_area=0.,mean_avg_wait=0.,mean_p95_delay=0.,mean_throughput=0.)
    monkeypatch.setattr("app.rl.trainer.DeterministicEvaluator",
        lambda **_:SimpleNamespace(run_multi_seed=lambda *_:metrics))
    return trainer,state,storage


@pytest.mark.anyio
@pytest.mark.parametrize("damage",["target","optimizer","episode","conflicting_slot"])
async def test_failed_training_resume_keeps_previous_agents_and_identity(monkeypatch,damage):
    trainer,state,storage = training_fixture(monkeypatch)
    previous_train,previous_sim = trainer.agent,state.sim_agent
    previous_weights = deepcopy(previous_train.online_net.state_dict())
    candidate = DQNAgent()
    checkpoint = {**deepcopy(candidate.get_checkpoint_state()),"episode":87}
    if damage == "target": checkpoint["target_net"][next(iter(checkpoint["target_net"]))] = torch.zeros(1)
    elif damage == "optimizer": checkpoint["optimizer"]["param_groups"][0]["lr"] = float("nan")
    elif damage == "episode": checkpoint.pop("episode")
    storage.load_checkpoint.return_value = checkpoint
    requested = 100 if damage == "conflicting_slot" else 0
    with pytest.raises((ValueError,RuntimeError)):
        await trainer.train("candidate-run",1,resume_model_id="candidate:0",resume_episode=requested)
    assert trainer.agent is previous_train and state.training_agent is previous_train
    assert state.sim_agent is previous_sim and state.active_model_id == "previous"
    assert state.active_model_episode == 12 and state.active_model_checkpoint_slot == 12
    for key,value in previous_weights.items():
        torch.testing.assert_close(previous_train.online_net.state_dict()[key],value,rtol=0,atol=0)
    storage.save_checkpoint.assert_not_called()
    assert not trainer.is_training


@pytest.mark.anyio
async def test_selected_slot_resumes_actual_episode_with_fresh_replay(monkeypatch):
    trainer,state,storage = training_fixture(monkeypatch)
    trainer.agent.replay_buffer.push(np.zeros(28),0,0.,np.zeros(28),False)
    checkpoint = {**deepcopy(DQNAgent().get_checkpoint_state()),"episode":87,"step_count":7,"total_train_steps":9}
    storage.load_checkpoint.return_value = checkpoint
    await trainer.train("candidate-run",1,resume_model_id="candidate")
    storage.load_checkpoint.assert_called_once_with("candidate",0)
    assert trainer.start_episode == 87 and trainer.target_episodes == 88
    assert len(trainer.agent.replay_buffer) == 0
    assert (trainer.agent.step_count,trainer.agent.total_train_steps) == (7,9)
    assert state.training_agent is trainer.agent
    assert (state.active_model_id,state.active_model_episode,state.active_model_checkpoint_slot) == ("candidate",87,0)


@pytest.mark.anyio
async def test_finetuning_preserves_parent_identity_and_resets_learning_state(monkeypatch):
    trainer,state,storage = training_fixture(monkeypatch)
    checkpoint = {**deepcopy(DQNAgent().get_checkpoint_state()),"episode":87,"step_count":7,"total_train_steps":9}
    storage.load_checkpoint.return_value = checkpoint
    await trainer.train("candidate-ft-custom_stadium",1,resume_model_id="candidate:0",is_finetune=True,
        finetune_scenario="custom",finetune_lr=5e-5,finetune_epsilon=0.,custom_profile={"name":"Stadium"})
    assert (trainer.parent_model_id,trainer.parent_episode,trainer.resume_checkpoint_slot) == ("candidate",87,0)
    assert (trainer.start_episode,trainer.target_episodes) == (0,1)
    assert (trainer.agent.step_count,trainer.agent.total_train_steps) == (0,0)
    assert len(trainer.agent.replay_buffer) == 0 and trainer.agent.optimizer.param_groups[0]["lr"] == 5e-5
    assert state.current_simulation_id == "candidate-ft-custom_stadium"
    assert state.training_agent is trainer.agent and trainer.agent.online_net.training
    assert not state.sim_agent.online_net.training and trainer.epsilon == 0.
    for key,value in checkpoint["online_net"].items():
        torch.testing.assert_close(trainer.agent.online_net.state_dict()[key],value,rtol=0,atol=0)


@pytest.mark.anyio
async def test_cancelled_training_clears_status(monkeypatch):
    import asyncio
    trainer,_,storage = training_fixture(monkeypatch)
    entered,release = asyncio.Event(),asyncio.Event()
    async def wait(*args):
        entered.set()
        await release.wait()
    trainer.ws_broadcast_fn.side_effect = wait
    storage.load_checkpoint.return_value = {**DQNAgent().get_checkpoint_state(),"episode":87}
    task = asyncio.create_task(trainer.train("candidate",1,resume_model_id="candidate:0"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not trainer.is_training


@pytest.mark.anyio
async def test_application_epsilon_decay_is_an_active_hyperparameter(monkeypatch):
    trainer,_,_ = training_fixture(monkeypatch,stop_after_setup=False)
    trainer.hyperparams.EPSILON_DECAY = .5
    await trainer.train("local-decay-check",1)
    assert trainer.epsilon == .5
    metrics = [call.args[0] for call in trainer.ws_broadcast_fn.call_args_list if "episode" in call.args[0]]
    assert metrics[0]["epsilon"] == .5


@pytest.mark.anyio
@pytest.mark.parametrize("save_fails",[False,True])
async def test_training_publishes_saved_checkpoint_identity_and_preserves_captured_agent(monkeypatch,save_fails):
    trainer,state,storage = training_fixture(monkeypatch,stop_after_setup=False)
    previous = state.sim_agent
    previous_weights = deepcopy(previous.online_net.state_dict())
    if save_fails:
        storage.save_checkpoint.side_effect = OSError("synthetic storage failure")
        with pytest.raises(OSError,match="synthetic storage"):
            await trainer.train("local-current",1)
        assert state.sim_agent is previous and state.active_model_id == "previous"
    else:
        await trainer.train("local-current",1)
        assert state.sim_agent is not previous
        assert (state.active_model_id,state.active_model_episode,state.active_model_checkpoint_slot) == ("local-current",1,1)
        assert not state.sim_agent.online_net.training
        saved = storage.save_checkpoint.call_args_list[0].args[2]
        for key,value in saved["online_net"].items():
            torch.testing.assert_close(state.sim_agent.online_net.state_dict()[key],value,rtol=0,atol=0)
    for key,value in previous_weights.items():
        torch.testing.assert_close(previous.online_net.state_dict()[key],value,rtol=0,atol=0)
    assert not trainer.is_training
