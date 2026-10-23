"""Diagnostic integrity on synthetic fixtures, not performance evidence."""
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from research.audits.audit_spatial_inputs import audit_source, probe_networks, short_branches, weight_report
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import collect_episode
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import SPATIAL_KEY, SPATIAL_VERSION


class SpatialSensitiveNet(torch.nn.Module):
    def forward(self, x, valid_action_mask=None):
        return torch.stack((torch.ones_like(x[:,0]), 2*x[:,36], x[:,1]*0, x[:,1]*0), dim=1)


def test_same_state_ablation_changes_only_extension_and_respects_mask():
    model = SimpleNamespace(agent=SimpleNamespace(obs_version=SPATIAL_VERSION, online_net=SpatialSensitiveNet()))
    obs = np.zeros(28, np.float32)
    obs[0] = .8
    context = ControllerContext(100, valid_action_mask=np.array([True, True, False, False]),
        extra_telemetry={SPATIAL_KEY: [.8] + [0.] * 11})
    before = obs.copy()
    result = probe_networks({"spatial_90": model}, obs, context)["spatial_90"]
    assert result["natural"]["action"] == 1
    assert result["zero_spatial"]["action"] == 0
    assert result["valid_q_delta_range"] == pytest.approx(1.6)
    np.testing.assert_array_equal(obs, before)
    context.valid_action_mask[1] = False
    result = probe_networks({"spatial_90": model}, obs, context)["spatial_90"]
    assert result["natural"]["action"] == result["zero_spatial"]["action"] == 0
    assert result["natural"]["margin"] is None
    assert result["valid_q_delta_range"] == 0


@pytest.fixture
def spatial_model(tmp_path):
    torch.set_num_threads(1)
    torch.manual_seed(32)
    agent = DQNAgent(48, SPATIAL_VERSION)
    # A deterministic hold-biased fixture with nonzero new columns.
    with torch.no_grad():
        agent.online_net.advantage_stream[-1].bias[0] = 10.
    path = tmp_path/"spatial.pt"
    torch.save(agent.get_checkpoint_state(), path)
    return path, D3QNController(checkpoint_path=str(path))


@pytest.mark.parametrize("fault", [FaultProfile(), FaultProfile(miss_rate=.2, latency_ms=200, frame_drop_prob=.1)])
def test_probes_and_branches_preserve_natural_trajectory(spatial_model, fault):
    path, model = spatial_model
    scenario = ScenarioConfig("train_fixture", "train", "Fixture", duration_steps=1200)
    case = dict(role="online", index=1, seed=10201, fault=fault.to_dict(), scenario=scenario.to_dict(), acting="spatial")
    probed = audit_source(case, path, {"spatial_90": model})
    plain = audit_source(case, path, {"spatial_90": model}, branches=False)
    assert {k:v for k,v in probed.items() if k not in ("events", "missing_branch_windows")} == {
        k:v for k,v in plain.items() if k not in ("events", "missing_branch_windows")}
    assert [{k:v for k,v in e.items() if k not in ("branches", "branch_window")} for e in probed["events"]] == plain["events"]
    regular = ExperimentRunner().run(FlowSyncUQController(checkpoint_path=str(path), enable_fallback=False),
        scenario, 10201, record_trajectory=False, fault_injector=PerceptionFaultInjector(fault, seed=100201))
    assert probed["avg_delay"] == pytest.approx(regular.avg_delay, abs=.001)
    assert probed["arrival_trace_hash"] == regular.arrival_trace_hash
    assert probed["signal_samples"] == 1200 and probed["signal_violations"] == 0
    assert any("branches" in e for e in probed["events"])
    for event in probed["events"]:
        if "branches" not in event:
            continue
        outcomes = event["branches"]
        assert len({b["outcome"]["arrival_trace_hash"] for b in outcomes.values()}) == 1
        assert outcomes["policy"] == outcomes["zero_spatial"] or outcomes["policy"]["proposal"] != outcomes["zero_spatial"]["proposal"]
        assert all(b["outcome"]["signal_samples"] == 200 and b["outcome"]["signal_violations"] == 0 for b in outcomes.values())


def test_branch_preserves_hold_schedule_and_deduplicates(monkeypatch):
    from research.audits import audit_spatial_inputs as module
    import copy
    context = ControllerContext(200, time_in_phase=10., valid_action_mask=np.ones(4, bool))
    from server.app.controllers.safety_shield import SafetyShield
    controller = SimpleNamespace(d3qn=SimpleNamespace(_held_action=0, _next_decision_step=220), safety_shield=SafetyShield())
    monkeypatch.setattr(module, "fork_state", lambda *state: copy.deepcopy(state))
    seen = []
    def rollout(state, scenario, step, horizon, first):
        seen.append((state[3].d3qn._held_action, state[3].d3qn._next_decision_step))
        return dict(arrival_trace_hash="same")
    monkeypatch.setattr(module, "rollout_branch", rollout)
    result = short_branches(None, None, None, controller, context, None, 200, dict(policy=0, zero_spatial=0, teacher=1))
    assert seen == [(0, 220), (1, 220)]
    assert result["policy"] == result["zero_spatial"]
    assert controller.d3qn._held_action == 0 and controller.safety_shield.total_evaluations == 0


def test_teacher_sources_reproduce_recorded_collection(spatial_model):
    path, model = spatial_model
    scenario = ScenarioConfig("train_fixture", "train", "Fixture", duration_steps=1200)
    fault = FaultProfile(miss_rate=.2, latency_ms=200)
    agent = DQNAgent(48, SPATIAL_VERSION)
    original = collect_episode(agent, scenario, 10201, fault, 0, teacher=MaxPressureController(),
                               learn=False, train_with_shield=True)
    case = dict(role="demo", index=1, seed=10201, fault=fault.to_dict(), scenario=scenario.to_dict(), expected_demo=original)
    result = audit_source(case, path, {"spatial_90": model})
    assert result["demo_replay_verified"]
    assert result["avg_delay"] == original["avg_delay"]
    assert all(e["proposal"] == e["teacher_proposals"]["historical_mp"] for e in result["events"])


@pytest.mark.parametrize("split", ["validation", "test"])
def test_nontraining_input_is_rejected(split):
    with pytest.raises(ValueError, match="training scenarios"):
        audit_source(dict(scenario=ScenarioConfig("other", split, "Other").to_dict()), "unused", {})


def test_nonzero_control_columns_fail_weight_integrity(spatial_model):
    _, model = spatial_model
    with pytest.raises(ValueError, match="Initial/control spatial"):
        weight_report({"control_initial": model})


def test_artifact_verifier_checks_scores_beyond_updated_hashes(tmp_path, spatial_model, monkeypatch):
    import hashlib
    import json
    import zipfile
    from research.audits import verify_spatial_input_audit as verifier
    from research.audits.audit_spatial_inputs import ARMS, STAGES, summarize
    from research.training.train_policy import file_hash
    _, model = spatial_model
    with torch.no_grad():
        model.agent.online_net.feature_layer[0].weight[:,36:] = 0.
    batch = tmp_path/"batch"
    cp = batch/"spatial_seed_101/checkpoint_90.pt"
    cp.parent.mkdir(parents=True)
    torch.save(model.agent.get_checkpoint_state(), cp)
    models = {f"{arm}_{stage}": model for arm in ARMS for stage in STAGES}
    scenario = ScenarioConfig("train_fixture", "train", "Fixture", duration_steps=1200)
    case = dict(role="online", index=1, seed=10201, fault=FaultProfile().to_dict(),
                scenario=scenario.to_dict(), acting="spatial")
    row = dict(audit_source(case, cp, models, branches=False), training_seed=101)
    artifact = tmp_path/"artifact"
    artifact.mkdir()
    (artifact/"weights.json").write_text(json.dumps({str(s):weight_report(models) for s in (101,202,303)}))
    source = b"frozen fixture source"
    with zipfile.ZipFile(artifact/"source_snapshot.zip", "w") as archive:
        archive.writestr("fixture.py", source)
    (artifact/"manifest.json").write_text(json.dumps(dict(batch=str(batch), cases={"control_101":[case]},
        input_hashes={str(cp):file_hash(cp)}, source_hashes={"fixture.py":hashlib.sha256(source).hexdigest()})))
    def save_outputs():
        (artifact/"sources.jsonl").write_text(json.dumps(row)+"\n")
        report = summarize([row])
        report["output_hashes"] = {n:file_hash(artifact/n) for n in ("weights.json", "sources.jsonl", "source_snapshot.zip")}
        (artifact/"report.json").write_text(json.dumps(report))
    save_outputs()
    monkeypatch.setattr(verifier, "D3QNController", lambda **kw: model)
    assert verifier.verify(artifact)["verified"]
    # Updating the raw file, its hash and aggregate summary cannot hide a bad Q.
    row["events"][0]["probes"]["spatial_90"]["natural"]["q_values"][0] += 1.
    save_outputs()
    with pytest.raises(ValueError, match="network score"):
        verifier.verify(artifact)
