import asyncio

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.research_contract import live_controller
from app.websockets.research_ws import ExperimentSession, _load_scenario


@pytest.mark.parametrize("controller", ["dqn", "d3qn", "flowsync_uq", "plain_dqn", "ai"])
def test_live_learning_requires_an_implemented_checkpoint_runtime(controller):
    with pytest.raises(ValueError, match="checkpoint"):
        live_controller(controller)


def test_live_controller_catalog_and_historical_summary():
    client = TestClient(app)
    catalog = client.get("/research/controllers").json()
    available = {c["id"] for c in catalog["controllers"] if c["available_live"]}
    assert available == {"fixed", "greedy", "actuated", "max_pressure"}
    assert client.get("/research/runtime").json()["audited_headless_parity"] is False
    summary = client.get("/research/summary").json()
    assert summary["status"] == "historical_invalid"
    assert summary["benchmark_summary"] == {}


def test_unknown_scenario_is_not_replaced_with_synthetic_test_data():
    with pytest.raises(ValueError, match="Unknown or missing"):
        _load_scenario("this_scenario_does_not_exist")


@pytest.mark.parametrize("paired", [False, True])
def test_session_reports_unavailable_model_before_starting_or_recording(monkeypatch, paired):
    from app.websockets import research_ws
    messages = []

    async def capture(socket, payload):
        messages.append(payload)

    monkeypatch.setattr(research_ws.research_manager, "send_json", capture)
    session = ExperimentSession(object())
    if paired:
        asyncio.run(session.run_paired("test_clean_balanced_01", "fixed", "d3qn"))
    else:
        asyncio.run(session.run_single("test_clean_balanced_01", "d3qn", 101))
    assert len(messages) == 1
    assert messages[0]["type"] == "experiment_error"
    assert "checkpoint" in messages[0]["error"]
    assert session.is_running is False


def test_classical_session_streams_actual_telemetry_without_a_fake_checkpoint(monkeypatch):
    from app.websockets import research_ws
    from research.scenarios.scenario_schema import ScenarioConfig
    messages = []

    async def capture(socket, payload):
        messages.append(payload)

    monkeypatch.setattr(research_ws.research_manager, "send_json", capture)
    monkeypatch.setattr(research_ws, "_load_scenario", lambda _: ScenarioConfig(
        scenario_id="contract_smoke", split="train", name="Contract smoke", duration_steps=2,
    ))
    session = ExperimentSession(object())
    asyncio.run(session.run_single("contract_smoke", "fixed", 101, speed=10, save_bundle=False))
    frames = [m for m in messages if m["type"] == "research_frame"]
    assert len(frames) == 2
    assert frames[0]["model_hash"] == ""
    assert frames[0]["controller"] == "fixed"
    assert frames[0]["runtime"]["audited_headless_parity"] is False
    assert frames[0]["perception"]["cv_latency_ms"] is None
    assert messages[-1]["type"] == "experiment_completed"
