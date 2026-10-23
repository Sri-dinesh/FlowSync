"""Shadow probes must not change the measured controller or use test scenarios."""
import json

import numpy as np
import pytest
import torch

from research.audits.audit_training_drift import EPISODES, ProbedPolicy, load_cases, score_actions, summarize
from research.pilots.compare_temporal_pilot import ARMS, SEEDS
from research.experiments.engine import ExperimentRunner
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import TEMPORAL_VERSION


def test_probe_respects_mask_and_single_action_margin():
    class Network:
        def __call__(self, *args, **kwargs):
            return torch.tensor([[100., 2., 2., -1.]])
    result = score_actions(Network(), np.zeros(64), np.array([False, True, True, False]))
    assert result["action"] == 1 and result["margin"] == 0
    assert score_actions(Network(), np.zeros(64), np.array([False, True, False, False]))["margin"] is None
    with pytest.raises(ValueError):
        score_actions(Network(), np.zeros(64), np.zeros(4, dtype=bool))


def test_cases_reject_test_split_and_duplicate_episodes(tmp_path):
    path = tmp_path / "training.jsonl"
    scenario = ScenarioConfig("test_forbidden", "test", "Forbidden").to_dict()
    rows = [dict(episode=e, executed_scenario=scenario, seed=1, fault={}) for e in EPISODES]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match="only replay training"):
        load_cases(path)
    path.write_text("\n".join(json.dumps(r) for r in rows + rows[:1]))
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)


def test_shadow_probe_does_not_change_trajectory_or_weights(tmp_path):
    torch.manual_seed(15)
    agent = DQNAgent(64, TEMPORAL_VERSION)
    checkpoints = {stage: tmp_path / f"{stage}.pt" for stage in ("initial", "final")}
    for path in checkpoints.values():
        torch.save(agent.get_checkpoint_state(), path)
    scenario = ScenarioConfig("train_probe", "train", "Probe", duration_steps=350)
    probed = ProbedPolicy(checkpoints, "initial")
    original = {k: v.clone() for k, v in probed.d3qn.agent.online_net.state_dict().items()}
    runner = ExperimentRunner()
    baseline = runner.run(FlowSyncUQController(checkpoint_path=str(checkpoints["initial"]),
        enable_shield=True, enable_fallback=False), scenario, 123, record_trajectory=True)
    result = runner.run(probed, scenario, 123, record_trajectory=True)
    assert result.trajectory == baseline.trajectory
    assert result.avg_delay == baseline.avg_delay
    assert result.total_reward == baseline.total_reward
    assert result.arrival_trace_hash == baseline.arrival_trace_hash
    assert probed.decision_probes
    assert all(e["initial"] == e["final"] for e in probed.decision_probes)
    assert all(torch.equal(v, original[k]) for k, v in probed.d3qn.agent.online_net.state_dict().items())


def test_summary_requires_complete_paired_covered_cells():
    rows = []
    for arm in ARMS:
        for seed in SEEDS:
            for episode in EPISODES:
                for acting in ("initial", "final"):
                    rows.append(dict(arm=arm, training_seed=seed, episode=episode, acting=acting,
                        probes=[dict(initial=dict(action=0, q_values=[0]*4), final=dict(action=0, q_values=[0]*4))],
                        result=dict(arrival_trace_hash=f"{seed}:{episode}", avg_delay=10., total_reward=-100.,
                        p95_delay=30., total_vehicles_passed=80, safety_samples=1200, num_steps=1200,
                        executed_conflict_violations=0, executed_clearance_violations=0)))
    report = summarize(rows)
    assert report["runs"] == 72 and report["paired_runs"] == 36
    assert all(r["delay_saved"] == 0 for r in report["by_group"])
    with pytest.raises(ValueError, match="Incomplete/duplicate"):
        summarize(rows[:-1])
    rows[1]["result"]["arrival_trace_hash"] = "wrong"
    with pytest.raises(ValueError, match="Unpaired"):
        summarize(rows)
    rows[1]["result"]["arrival_trace_hash"] = rows[0]["result"]["arrival_trace_hash"]
    rows[1]["result"]["safety_samples"] = 0
    with pytest.raises(ValueError, match="signal audit"):
        summarize(rows)
