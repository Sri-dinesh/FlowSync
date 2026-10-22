import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from research.audits.audit_arrival_label_stability import (
    REPLICATES, SOURCE_SEED, future_seed, replace_future_rng, resample_branches,
    summarize, summarize_event, verify_original,
)
from research.audits.audit_policy_decisions import audit_run
from research.noise.fault_injector import FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.rl.dqn_agent import DQNAgent
from server.app.simulation.spawner import PoissonSpawner


def test_rng_intervention_preserves_backlog_clock_and_source():
    spawner = PoissonSpawner()
    spawner.set_seed(10)
    spawner._clock = 42.
    spawner._pending["north_left"].append(3.)
    spawner.total_generated = 7
    state = (SimpleNamespace(intersection=SimpleNamespace(spawner=spawner)),)
    branch = copy.deepcopy(state)
    original = copy.deepcopy(spawner.__dict__)
    replace_future_rng(branch, 99)
    changed = branch[0].intersection.spawner
    for key, value in original.items():
        if key != "_rng":
            assert changed.__dict__[key] == value
    assert spawner._rng.bit_generator.state == original["_rng"].bit_generator.state
    assert changed._rng.bit_generator.state == np.random.default_rng(99).bit_generator.state


def test_future_seeds_are_repeatable_and_distinct():
    values = [future_seed(101, "train_fixture", SOURCE_SEED, 200, i) for i in range(REPLICATES)]
    assert len(set(values)) == REPLICATES
    assert values == [future_seed(101, "train_fixture", SOURCE_SEED, 200, i) for i in range(REPLICATES)]
    assert future_seed(202, "train_fixture", SOURCE_SEED, 200, 0) not in values


def branch(action, delay, trace="fixture"):
    return dict(proposal=action, first_execution=action, outcome=dict(
        incremental_delay_vehicle_seconds=delay, vehicles_passed=3,
        upstream_max_wait_s=10., arrival_trace_hash=trace,
        signal_samples=400, signal_violations=0))


def synthetic_event():
    return dict(step=200, policy_proposal=0,
                all_action_branches=[branch(0, 20.), branch(1, 10.)],
                branch_diagnostic=[dict(replicate=i, arrival_seed=i, branches=[
                    branch(0, 20., str(i)), branch(1, 10. if i < 4 else 30., str(i))])
                                   for i in range(REPLICATES)])


def test_report_excludes_original_from_future_estimates_and_counts_sign_flips():
    event = synthetic_event()
    report = summarize_event(event)
    alt = report["alternatives"][0]
    assert alt["mean_gain"] == [0., 0., 0.]
    assert alt["sample_sd"][0] == pytest.approx(np.std([10.] * 4 + [-10.] * 4, ddof=1))
    assert alt["delay_sign_flip"]
    assert alt["qualified_futures"] == 4 and alt["harmful_futures"] == 4
    assert report["original_choice"] == 1 and report["mean_choice"] == 0
    assert report["future_choices"] == [1] * 4 + [0] * 4
    row = dict(training_seed=101, scenario="train_fixture", seed=SOURCE_SEED,
               signal_samples=1200, signal_violations=0, events=[event])
    summary, _ = summarize([row], 18, False, "budget")
    assert not summary["complete"] and not summary["publication_ready"]
    assert summary["original_choice_future_cases"] == 8
    assert summary["source_and_branch_signal_samples"] == 8400
    json.dumps(summary, allow_nan=False)
    event["branch_diagnostic"].pop()
    with pytest.raises(ValueError, match="Incomplete"):
        summarize_event(event)


def test_replay_comparison_rejects_source_or_label_mutation():
    old = dict(events=[synthetic_event()], avg_delay=1.)
    old["events"][0].pop("branch_diagnostic")
    new = copy.deepcopy(old)
    new["events"][0]["branch_diagnostic"] = []
    verify_original(new, old)
    new["events"][0]["all_action_branches"][0]["outcome"]["vehicles_passed"] = 999
    with pytest.raises(ValueError, match="changed"):
        verify_original(new, old)


def test_replay_comparison_normalizes_json_keys_but_not_numeric_changes():
    live = dict(events=[dict(step=200, observed_phase_timers={0: 1.25, 1: 2.5})])
    stored = json.loads(json.dumps(live))
    verify_original(live, stored)
    live["events"][0]["observed_phase_timers"][0] += 1e-12
    with pytest.raises(ValueError, match="changed"):
        verify_original(live, stored)


def test_real_branches_pair_arrivals_and_do_not_mutate_source(tmp_path):
    torch.set_num_threads(1)
    path = tmp_path / "parent.pt"
    agent = DQNAgent()
    with torch.no_grad():
        for parameter in agent.online_net.parameters():
            parameter.zero_()
        agent.online_net.advantage_stream[-1].bias[0] = 1.
    torch.save(agent.get_checkpoint_state(), path)
    scenario = ScenarioConfig("train_fixture", "train", "Fixture", duration_steps=600)
    reference = audit_run(path, scenario, SOURCE_SEED, FaultProfile(), 40, 1, all_actions=True)
    steps = [e["step"] for e in reference["events"] if "all_action_branches" in e]
    assert len(steps) == 1
    def diagnostic(*args):
        return resample_branches(101, *args)
    measured = audit_run(path, scenario, SOURCE_SEED, FaultProfile(), 40, 1,
                         all_actions=True, branch_steps=steps, branch_diagnostic=diagnostic)
    verify_original(measured, reference)
    event = next(e for e in measured["events"] if "branch_diagnostic" in e)
    traces = []
    for future in event["branch_diagnostic"]:
        hashes = {b["outcome"]["arrival_trace_hash"] for b in future["branches"]}
        assert len(hashes) == 1
        traces.append(next(iter(hashes)))
        assert all(b["outcome"]["signal_samples"] == 40 and
                   b["outcome"]["signal_violations"] == 0 for b in future["branches"])
    assert len(set(traces)) > 1
    repeated = audit_run(path, scenario, SOURCE_SEED, FaultProfile(), 40, 1,
                        all_actions=True, branch_steps=steps, branch_diagnostic=diagnostic)
    assert repeated == measured
