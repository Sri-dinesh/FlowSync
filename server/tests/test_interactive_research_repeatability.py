"""Repeat production interactive sessions; no claim of headless/browser parity."""
import asyncio
import copy

import pytest

from app.websockets import research_ws
from research.noise.fault_injector import FAULT_PRESETS
from research.scenarios.scenario_schema import ScenarioConfig


@pytest.mark.parametrize("preset", ["clean", "miss_30"])
def test_interactive_classical_repeatability(monkeypatch, preset):
    messages = []

    async def capture(socket, payload):
        messages.append(payload)

    async def no_pacing(delay):
        pass

    monkeypatch.setattr(research_ws.research_manager, "send_json", capture)
    monkeypatch.setattr(research_ws.asyncio, "sleep", no_pacing)
    monkeypatch.setattr(research_ws, "_load_scenario", lambda _: ScenarioConfig(
        scenario_id="interactive_repeat", split="train", name="Repeat mechanics", duration_steps=160,
    ))
    profile_before = copy.deepcopy(FAULT_PRESETS[preset].to_dict())

    def collect():
        messages.clear()
        session = research_ws.ExperimentSession(object())
        asyncio.run(session.run_single("interactive_repeat", "fixed", 303,
                                       noise_preset=preset, save_bundle=False))
        frames = [m for m in messages if m["type"] == "research_frame"]
        assert len(frames) == 160
        assert messages[-1]["type"] == "experiment_completed"
        # UUID render identifiers and wall-clock experiment IDs are not deterministic.
        return [{k: frame[k] for k in ("step", "signal", "metrics", "policy", "uncertainty", "runtime")}
                for frame in frames]

    first, second = collect(), collect()
    assert first == second
    assert first[0]["runtime"]["audited_headless_parity"] is False
    assert FAULT_PRESETS[preset].to_dict() == profile_before
