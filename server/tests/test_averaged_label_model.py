import copy
import io
import json
from types import SimpleNamespace

import numpy as np
import pytest

from research.audit_arrival_label_stability import future_seed, replace_future_rng
from research.averaged_label_model import (
    cells, configuration, fit_models, predict_source, selected_steps, summarize,
)
from research.run_averaged_label_model_pilot import collect_source


PARENTS = {"101": {"sha256": "fixture"}}


def branches(delays, trace):
    return [dict(proposal=a, first_execution=a, outcome=dict(
        incremental_delay_vehicle_seconds=d, vehicles_passed=3, upstream_max_wait_s=10.,
        signal_samples=400, signal_violations=0, arrival_trace_hash=trace))
        for a, d in enumerate(delays)]


def row(seed, role="fit"):
    indices = configuration(True)[f"{role}_ids"]
    record = dict(split="train", data_role=role, training_seed=101, scenario="fixture", seed=seed,
                  fault=dict(name="clean"), checkpoint_hash="fixture", selected_steps=[200, 400],
                  signal_samples=1200, signal_violations=0, events=[])
    for step in (200, 400):
        record["events"].append(dict(step=step, phase=0, phase_age=20., policy_proposal=0,
            policy_observation=np.linspace(0., 1., 36).tolist(), q_values=[1., 2., 3., 4.],
            mask=[True, True, True, False], horizon_steps=400,
            all_action_branches=branches((100., 80., 95.), "original"),
            branch_diagnostic=[dict(replicate=i, arrival_seed=future_seed(101, "fixture", seed, step, i),
                                   branches=branches((100., 110., 70.), str(i))) for i in indices]))
    return record


def fit():
    return fit_models([row(96901), row(96902)], configuration(True), ["fixture"], PARENTS)


def test_plan_separates_roles_and_smoke_and_selection_is_outcome_blind():
    full, smoke = configuration(), configuration(True)
    assert len(cells(full, [str(i) for i in range(6)], "fit")) == 72
    assert len(cells(full, [str(i) for i in range(6)], "probe")) == 36
    assert not set(full["fit_seeds"]) & set(full["probe_seeds"])
    assert not (set(full["fit_seeds"]) | set(full["probe_seeds"])) & (set(smoke["fit_seeds"]) | set(smoke["probe_seeds"]))
    source = row(96901)
    before = selected_steps(source, 101)
    source["avg_delay"] = 1e9
    for e in source["events"]:
        e["all_action_branches"] = "unreadable labels"
    assert selected_steps(source, 101) == before
    source["split"] = "test"
    with pytest.raises(ValueError, match="Training"):
        selected_steps(source, 101)


def test_fitting_is_deterministic_role_bound_and_matched_between_arms():
    models = fit()
    assert models == fit()
    single, mean = models[(101, "single")], models[(101, "mean8")]
    assert single["scale"] == mean["scale"]
    assert single["fit_seeds"] == mean["fit_seeds"] == [96901, 96902]
    assert single["point"] != mean["point"]
    altered = [row(96901), row(96902)]
    for r in altered:
        for e in r["events"]:
            for f in e["branch_diagnostic"]:
                f["branches"][1]["outcome"]["incremental_delay_vehicle_seconds"] += 30.
    changed = fit_models(altered, configuration(True), ["fixture"], PARENTS)
    assert changed[(101, "single")] == single
    assert changed[(101, "mean8")]["point"] != mean["point"]
    wrong = [row(96901), row(96902)]
    wrong[0]["data_role"] = "probe"
    with pytest.raises(ValueError, match="Wrong fitting role"):
        fit_models(wrong, configuration(True), ["fixture"], PARENTS)
    with pytest.raises(ValueError, match="Incomplete"):
        fit_models([row(96901)], configuration(True), ["fixture"], PARENTS)
    with pytest.raises(ValueError, match="Incomplete"):
        fit_models([row(96901), row(96903)], configuration(True), ["fixture"], PARENTS)


def test_predictions_ignore_outcomes_and_do_not_refit_models():
    models = fit()
    snapshot = copy.deepcopy(models)
    probe = row(96903, "probe")
    original = predict_source(probe, [200, 400], models)
    probe["avg_delay"] = 999999
    for e in probe["events"]:
        e["all_action_branches"] = None
        e["branch_diagnostic"] = None
    assert predict_source(probe, [200, 400], models) == original
    assert models == snapshot
    probe["checkpoint_hash"] = "wrong"
    with pytest.raises(ValueError, match="mismatch"):
        predict_source(probe, [200, 400], models)


def test_new_source_seeds_produce_distinct_arrival_streams():
    for i in range(8):
        assert future_seed(101, "fixture", 96301, 200, i) != future_seed(101, "fixture", 96401, 200, i)


def test_probe_choices_are_flushed_before_any_branch_outcomes(monkeypatch):
    import research.run_averaged_label_model_pilot as runner
    branched = row(96903, "probe")
    for k in ("training_seed", "data_role", "selected_steps"):
        branched.pop(k)
    source = copy.deepcopy(branched)
    for e in source["events"]:
        for k in ("horizon_steps", "all_action_branches", "branch_diagnostic"):
            e.pop(k)
    predictions = io.StringIO()
    calls = []
    def fake_audit(*args, **kwargs):
        calls.append(kwargs)
        if kwargs.get("branch_diagnostic") is not None:
            recorded = json.loads(predictions.getvalue())
            assert len(recorded) == 2
            return copy.deepcopy(branched)
        assert not predictions.getvalue()
        return copy.deepcopy(source)
    monkeypatch.setattr(runner, "audit_run", fake_audit)
    measured, choices = collect_source(101, None, 96903, "unused.pt", "probe", tuple(range(108, 116)),
                                       SimpleNamespace(check=lambda stage: None), fit(), predictions)
    assert len(calls) == 2 and measured["data_role"] == "probe"
    assert json.loads(predictions.getvalue()) == json.loads(json.dumps(choices))


def test_incomplete_or_smoke_cannot_pass_continuation():
    report = summarize([], configuration(), [str(i) for i in range(6)], 1, 0)
    assert not report["complete"] and not report["continue_to_full_rollout_pilot"]
    assert report["arms"]["mean8"]["mean_gain"] is None
    assert not report["dqn_retrained"] and not report["model_promoted"]
    source = dict(training_seed=101, scenario="fixture", seed=96903,
                  prediction_mae={a: [1., 1., 1.] for a in ("single", "mean8")}, arms={})
    for arm in ("parent", "single", "mean8"):
        source["arms"][arm] = dict(mean_gain=[1., 0., 0.] if arm == "mean8" else [0., 0., 0.],
            cases=16, changed_cases=8, executed_change_cases=8, qualified_cases=8, harmful_cases=0)
    report = summarize([source], configuration(True), ["fixture"], 2, 2)
    assert report["complete"] and not report["full_pilot_complete"]
    assert not report["continue_to_full_rollout_pilot"]
