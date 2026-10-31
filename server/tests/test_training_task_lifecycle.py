"""Single-process training request ownership and observable task failures."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, WebSocketDisconnect

from app.routers import training
from app.schemas.training_schema import StartTrainingRequest


@pytest.mark.anyio
async def test_preparing_training_rejects_duplicate_start_and_model_replacement(monkeypatch):
    entered,release = asyncio.Event(),asyncio.Event()
    trainer = SimpleNamespace(is_training=False,train=AsyncMock())
    state = SimpleNamespace(trainer=trainer,training_task=None)
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    async def create_record(*args):
        entered.set()
        await release.wait()
        return "supplied-run"
    monkeypatch.setattr(training.asyncio,"to_thread",create_record)
    first = asyncio.create_task(training.start_training(StartTrainingRequest(num_episodes=1),request))
    await entered.wait()
    try:
        duplicate = await training.start_training(StartTrainingRequest(simulation_id="duplicate"),request)
        assert duplicate["status"] == "already_training"
        with pytest.raises(HTTPException) as blocked:
            await training.load_model(training.LoadModelRequest(model_id="candidate"),request)
        assert blocked.value.status_code == 409
    finally:
        release.set()
        await first
        if state.training_task is not None:
            await state.training_task
    assert trainer.train.await_count == 1


@pytest.mark.anyio
async def test_pending_task_rejects_websocket_start_before_preparation(monkeypatch):
    from app.websockets import training_ws
    pending = asyncio.get_running_loop().create_future()
    trainer = SimpleNamespace(is_training=False,get_status=lambda:{},stop=MagicMock())
    state = SimpleNamespace(trainer=trainer,training_task=pending)
    socket = SimpleNamespace(app=SimpleNamespace(state=state),accept=AsyncMock(),send_json=AsyncMock(),
        receive_json=AsyncMock(side_effect=[dict(command="start_training",simulation_id="duplicate"),WebSocketDisconnect()]))
    launch = AsyncMock()
    monkeypatch.setattr(training_ws,"training_manager",training_ws.TrainingConnectionManager())
    monkeypatch.setattr(training_ws,"_run_training_task",launch)
    try:
        await training_ws.training_socket(socket)
        launch.assert_not_called()
        assert state.training_task is pending
        messages = [call.args[0] for call in socket.send_json.call_args_list]
        assert any(message.get("type") == "training_error" for message in messages)
        assert not any(message.get("type") == "training_request_received" for message in messages)
    finally:
        pending.cancel()


@pytest.mark.anyio
async def test_http_background_failure_is_broadcast_and_status_is_released():
    from app.rl.dqn_agent import DQNAgent
    from app.rl.trainer import Trainer
    broadcast = AsyncMock()
    storage = SimpleNamespace(list_checkpoints=lambda _:[])
    trainer = Trainer(MagicMock(),DQNAgent(),MagicMock(),storage,broadcast)
    state = SimpleNamespace(trainer=trainer,training_task=None)
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    response = await training.start_training(StartTrainingRequest(resume_model_id="missing:0"),request)
    assert response["status"] == "started"
    await state.training_task
    assert not trainer.is_training and state.training_task.done()
    failures = [call.args[0] for call in broadcast.call_args_list if call.args[0].get("type") == "training_error"]
    assert len(failures) == 1 and failures[0]["is_training"] is False
    assert "missing" in failures[0]["message"]
