"""Behavioral regressions for methodology-critical numerical/identity boundaries."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.rl.dqn_agent import DQNAgent
from app.schemas.training_schema import StartTrainingRequest
from app.services.checkpoint_loading import load_website_agent,parse_model_request,select_checkpoint


@pytest.mark.parametrize("fields", [dict(num_episodes=0),dict(num_episodes=True),dict(mode="unknown"),
    dict(finetune_lr=0.),dict(finetune_lr=float("nan")),dict(finetune_epsilon=-.1),dict(finetune_epsilon=float("inf")),
    dict(mode="finetune"),dict(mode="resume"),dict(resume_episode=0)])
def test_training_numerical_boundary_rejects_invalid_values(fields):
    with pytest.raises(ValidationError):
        StartTrainingRequest(**fields)


def test_finetune_zero_reaches_fake_trainer_without_starting_training(monkeypatch):
    from app.routers import training
    trainer = SimpleNamespace(is_training=False,train=AsyncMock())
    app = SimpleNamespace(state=SimpleNamespace(trainer=trainer))
    captured = []
    def create_task(coroutine):
        captured.append(coroutine)
        return SimpleNamespace()
    monkeypatch.setattr(training.asyncio,"create_task",create_task)
    async def launch():
        await training.start_training(StartTrainingRequest(mode="finetune",resume_model_id="parent:0",finetune_epsilon=0.),SimpleNamespace(app=app))
        await captured[0]
    asyncio.run(launch())
    assert trainer.train.call_args.kwargs["finetune_epsilon"] == 0.
    assert len(captured) == 1 and trainer.train.await_count == 1


def test_checkpoint_selection_is_exact_and_retains_zero_slot():
    assert parse_model_request("model:0",0) == ("model",0)
    assert select_checkpoint(["checkpoint_0.pt","checkpoint_100.pt"],0) == 0
    with pytest.raises(FileNotFoundError):
        select_checkpoint(["checkpoint_100.pt"],90)
    with pytest.raises(ValueError):
        parse_model_request("model:0",100)
    with pytest.raises(ValueError):
        parse_model_request("../model",0)
    checkpoint = DQNAgent().get_checkpoint_state()
    with pytest.raises(ValueError,match="episode"):
        load_website_agent(checkpoint)


def test_websocket_failure_preserves_model_and_success_publishes_actual_episode(monkeypatch):
    from app.websockets.simulation_ws import _load_agent_checkpoint
    from app.services import model_service
    original = DQNAgent()
    app = SimpleNamespace(state=SimpleNamespace(sim_agent=original,active_model_id="old",active_model_episode=0))
    monkeypatch.setattr(model_service,"list_checkpoints",lambda _:[])
    with pytest.raises(FileNotFoundError):
        asyncio.run(_load_agent_checkpoint(app,"missing",50))
    assert app.state.sim_agent is original and app.state.active_model_id == "old"
    checkpoint = {**original.get_checkpoint_state(),"episode":27}
    monkeypatch.setattr(model_service,"list_checkpoints",lambda _:["checkpoint_0.pt"])
    monkeypatch.setattr(model_service,"load_checkpoint",lambda *_:checkpoint)
    assert asyncio.run(_load_agent_checkpoint(app,"new:0")) == ("new",27)
    assert app.state.active_model_checkpoint_slot == 0 and app.state.sim_agent is not original


def test_model_listing_has_no_upload_side_effect(tmp_path,monkeypatch):
    from app.services import model_service
    (tmp_path/"local").mkdir()
    (tmp_path/"local"/"checkpoint_100.pt").write_bytes(b"fixture only")
    (tmp_path/"local"/"checkpoint_0.pt").write_bytes(b"fixture only")
    storage = MagicMock()
    storage.list.return_value = []
    client = SimpleNamespace(storage=SimpleNamespace(from_=lambda _:storage))
    monkeypatch.setattr(model_service,"supabase_client",client)
    monkeypatch.setattr(model_service,"LOCAL_MODELS_DIR",tmp_path)
    monkeypatch.setattr(model_service,"_fetch_rl_models_from_db",lambda:[])
    models = model_service._list_all_models_uncached()
    assert models and not models[0]["in_cloud"]
    selected = next(model for model in models if model["id"] == "local:0")
    assert "Selected checkpoint" in selected["name"] and "validated" not in selected["name"]
    storage.upload.assert_not_called()


@pytest.mark.parametrize("epsilon", [0., -1., float("nan")])
def test_websocket_uses_training_schema_before_launch(monkeypatch,epsilon):
    from fastapi import WebSocketDisconnect
    from app.websockets import training_ws
    trainer = SimpleNamespace(is_training=False,get_status=lambda:{},stop=MagicMock())
    state = SimpleNamespace(trainer=trainer)
    socket = SimpleNamespace(app=SimpleNamespace(state=state),accept=AsyncMock(),send_json=AsyncMock(),
        receive_json=AsyncMock(side_effect=[dict(command="start_training",simulation_id="fixture",
            num_episodes=1,mode="finetune",resume_model_id="parent:0",finetune_epsilon=epsilon),WebSocketDisconnect()]))
    launch = AsyncMock()
    monkeypatch.setattr(training_ws,"training_manager",training_ws.TrainingConnectionManager())
    monkeypatch.setattr(training_ws,"_run_training_task",launch)
    def create_task(coroutine):
        coroutine.close()
        return SimpleNamespace()
    monkeypatch.setattr(training_ws.asyncio,"create_task",create_task)
    asyncio.run(training_ws.training_socket(socket))
    messages = [call.args[0] for call in socket.send_json.call_args_list]
    if epsilon == 0.:
        assert launch.call_args.kwargs["finetune_epsilon"] == 0.
        assert any(message.get("type") == "training_started" for message in messages)
    else:
        launch.assert_not_called()
        assert not hasattr(state,"training_task")
        assert any(message.get("type") == "training_error" for message in messages)


def test_http_load_rejects_missing_or_incompatible_checkpoint_before_publication(monkeypatch):
    from fastapi import HTTPException
    from app.routers import training
    from app.services import model_service
    old_agent = DQNAgent()
    trainer = SimpleNamespace(is_training=False,agent=old_agent)
    state = SimpleNamespace(sim_agent=old_agent,training_agent=old_agent,trainer=trainer,
        active_model_id="old",active_model_episode=10)
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    monkeypatch.setattr(model_service,"list_checkpoints",lambda _:["checkpoint_100.pt"])
    with pytest.raises(HTTPException) as missing:
        asyncio.run(training.load_model(training.LoadModelRequest(model_id="new",episode=90),request))
    assert missing.value.status_code == 404
    checkpoint = {**old_agent.get_checkpoint_state(),"episode":97,"obs_version":"v7_36dim_observed"}
    monkeypatch.setattr(model_service,"load_checkpoint",lambda *_:checkpoint)
    with pytest.raises(HTTPException) as incompatible:
        asyncio.run(training.load_model(training.LoadModelRequest(model_id="new",episode=100),request))
    assert incompatible.value.status_code == 409
    assert state.sim_agent is old_agent and state.training_agent is old_agent and trainer.agent is old_agent
    assert state.active_model_id == "old" and state.active_model_episode == 10
    checkpoint["obs_version"] = old_agent.obs_version
    response = asyncio.run(training.load_model(training.LoadModelRequest(model_id="new",episode=100),request))
    assert response["episode"] == 97 and response["checkpoint_episode"] == 100
    assert state.sim_agent is not old_agent and state.training_agent is trainer.agent
    assert state.training_agent.online_net.training and not state.sim_agent.online_net.training
