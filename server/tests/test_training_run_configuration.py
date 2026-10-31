"""Effective settings and actual file/checkpoint linkage, without online training."""
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.rl.dqn_agent import DQNAgent
from app.rl.hyperparams import HyperParams
from app.rl.run_configuration import capture_configuration, capture_episode, configuration_hash
from app.rl.trainer import Trainer
from app.services import model_service
from app.simulation.environment import TrafficEnv
from research.audits.verify_training_run import verify


def configured_trainer():
    trainer = Trainer(TrafficEnv(max_steps=17,red_duration=4.5,enable_watchdogs=False),DQNAgent(),MagicMock(),
        model_service,AsyncMock(),hyperparams=HyperParams(LEARNING_RATE=.123,GAMMA=.5,MIN_REPLAY_SIZE=0,BATCH_SIZE=7),
        enable_curriculum=False,enable_greedy_warmup=False)
    trainer.agent.optimizer.param_groups[0]["lr"] = .0007
    return trainer


def test_effective_values_are_distinct_from_declared_overrides_and_private_environment(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY","private_fixture_never_export")
    trainer = configured_trainer()
    config,sources = capture_configuration(trainer,"model",1,None,{"demo_enabled":False})
    assert config["declared_hyperparams"]["LEARNING_RATE"] == .123
    assert config["agent"]["optimizer_groups"][0]["lr"] == .0007
    assert config["environment_at_setup"]["signal"]["red_duration"] == 4.5
    assert config["environment_at_setup"]["discount_gamma"] == .99
    assert config["replay"]["readiness_transitions"] == 1000
    assert not config["unavailable_fields"]
    assert config["randomness"]["policy_training_seed"] is None
    assert "private_fixture_never_export" not in json.dumps(config)
    for name,raw in sources.items():
        assert hashlib.sha256(raw).hexdigest() == config["source_sha256"][name]
        assert "private_fixture_never_export".encode() not in raw


def test_configuration_freezes_settings_while_episode_capture_reports_later_values():
    trainer = configured_trainer()
    config,_ = capture_configuration(trainer,"model",1,None,{})
    before = configuration_hash(config)
    trainer.agent.optimizer.param_groups[0]["lr"] = .002
    trainer.env.intersection.spawner.set_rate(.9)
    record = capture_episode(trainer,1,{"stage":"supplied","lambda":.9})
    assert configuration_hash(config) == before
    assert record["optimizer_groups"][0]["lr"] == .002
    assert record["environment_after_reset"]["demand"]["base_rate_vehicles_per_s"] == .9


def test_real_bundle_checkpoint_round_trip_and_tamper_detection(tmp_path,monkeypatch):
    monkeypatch.setattr(model_service,"LOCAL_MODELS_DIR",tmp_path)
    cloud = MagicMock()
    cloud.upload.side_effect = OSError("offline fixture")
    monkeypatch.setattr(model_service,"supabase_client",SimpleNamespace(storage=SimpleNamespace(from_=lambda _:cloud)))
    trainer = configured_trainer()
    config,sources = capture_configuration(trainer,"model",1,None,{})
    run_id = "a"*32
    manifest = model_service.save_training_configuration("model",run_id,config,sources)
    record = capture_episode(trainer,1,{})
    digest = manifest["configuration_sha256"]
    model_service.record_training_episode("model",run_id,digest,record)
    state = {**trainer.agent.get_checkpoint_state(),"episode":1,
        "training_run":{"run_id":run_id,"configuration_sha256":digest,"configuration":config,"episode_configuration":record}}
    receipt = model_service.save_checkpoint("model",1,state)
    root = tmp_path/"model"/"runs"/run_id
    checkpoint = tmp_path/"model"/"checkpoint_1.pt"
    assert verify(root,checkpoint)["checkpoints_checked"] == 1
    assert receipt["cloud_uploaded"] is False
    restored = model_service.load_checkpoint("model",1,expected_sha256=receipt["sha256"])
    assert restored["training_run"]["configuration_sha256"] == digest
    with pytest.raises(FileExistsError):
        model_service.save_training_configuration("model",run_id,config,sources)
    with pytest.raises(ValueError,match="different contents"):
        model_service.record_training_episode("model",run_id,digest,{**record,"epsilon_at_start":.123})
    (root/"episodes"/"episode_1.json").write_text("{}")
    with pytest.raises(ValueError,match="hash differs"):
        verify(root)


@pytest.mark.parametrize("damage",["source","nonfinite"])
def test_invalid_bundle_is_rejected_before_creating_run(tmp_path,monkeypatch,damage):
    monkeypatch.setattr(model_service,"LOCAL_MODELS_DIR",tmp_path)
    config,sources = capture_configuration(configured_trainer(),"model",1,None,{})
    if damage == "source": sources[next(iter(sources))] = b"changed"
    else: config["bad"] = float("nan")
    with pytest.raises(ValueError):
        model_service.save_training_configuration("model","a"*32,config,sources)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.anyio
async def test_trainer_persists_actual_run_and_checkpoint_with_offline_storage(tmp_path,monkeypatch):
    monkeypatch.setattr(model_service,"LOCAL_MODELS_DIR",tmp_path)
    cloud = MagicMock()
    cloud.upload.side_effect = OSError("offline fixture")
    monkeypatch.setattr(model_service,"supabase_client",SimpleNamespace(storage=SimpleNamespace(from_=lambda _:cloud)))
    metrics = SimpleNamespace(mean_queue_area=0.,mean_avg_wait=0.,mean_p95_delay=0.,mean_throughput=0.)
    monkeypatch.setattr("app.rl.trainer.DeterministicEvaluator",
        lambda **_:SimpleNamespace(run_multi_seed=lambda *_:metrics))
    trainer = Trainer(TrafficEnv(max_steps=90,red_duration=4.5,enable_watchdogs=False),DQNAgent(),
        SimpleNamespace(save_episode=lambda *_:None,save_model_metadata=lambda *_:None),model_service,AsyncMock(),
        enable_curriculum=False,enable_greedy_warmup=False)
    await trainer.train("local-manifest-fixture",1)
    root = tmp_path/"local-manifest-fixture"/"runs"/trainer.run_id
    checkpoint = root.parent.parent/"checkpoint_1.pt"
    report = verify(root,checkpoint)
    assert report["verified"] and report["episode_records"] == 1 and report["checkpoints_checked"] == 1
    assert not report["configuration_unavailable_fields"]
    state = trainer.get_status()
    state["run_configuration"]["agent"]["state_dim"] = 999
    assert trainer.run_configuration["agent"]["state_dim"] == 28
    events = [call.args[0] for call in trainer.ws_broadcast_fn.call_args_list]
    saved = next(event for event in events if event.get("type") == "checkpoint_saved")
    assert saved["storage"]["cloud_uploaded"] is False and saved["storage"]["local_saved"]
    assert trainer.agent.total_train_steps == 0
    episode = json.loads((root/"episodes"/"episode_1.json").read_bytes())
    assert episode["replay_beta"] == trainer.agent.replay_buffer.beta
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.routers.training import router
    app = FastAPI()
    app.include_router(router)
    app.state.trainer = trainer
    app.state.training_task = None
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://fixture") as client:
        response = await client.post("/training/load",json={"model_id":"local-manifest-fixture","episode":1})
    assert response.status_code == 200
    loaded = response.json()
    assert loaded["episode"] == 1 and loaded["storage"]["source"] == "local"
    assert loaded["storage"]["sha256"] == saved["storage"]["sha256"]
