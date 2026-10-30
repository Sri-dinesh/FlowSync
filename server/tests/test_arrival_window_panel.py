import pytest

from research.pilots.run_arrival_window_panel import (
    METHODS, PRIMARY, panel_cases, compare, rollout, RunBudget, wait_metrics,
)


def rows():
    cases = panel_cases()
    return cases, [dict(case_id=case["case_id"], method=method, delay=9. if method == PRIMARY else 10.,
        p95=30., passed=100, samples=1200, violations=0, arrival_trace_hash=case["case_id"])
        for case in cases for method in METHODS]


def test_screen_requires_every_case_reference_and_component_ablation():
    cases, data = rows()
    assert len(cases) == 18 and len(data) == 180
    assert compare(data, cases)["continue_to_fresh_development"]
    assert not compare(data[:-1], cases)["primary_endpoint_complete"]
    for row in data:
        if row["method"] == "point_extension":
            row["delay"] = 8.
    result = compare(data, cases)
    assert not result["checks"]["delay_gain_vs_point_extension"]
    assert not result["continue_to_fresh_development"]


def test_aggregate_gain_cannot_hide_harmful_case_or_unpaired_arrivals():
    cases, data = rows()
    next(r for r in data if r["method"] == PRIMARY)["delay"] = 11.
    result = compare(data, cases)
    assert result["means"][PRIMARY]["delay"] < 10.
    assert not result["checks"]["no_case_over_five_percent_loss_vs_age_gated_advanced_mp"]
    assert not result["continue_to_fresh_development"]
    data[0]["arrival_trace_hash"] = "unpaired"
    assert not compare(data, cases)["checks"]["paired_arrivals"]


def test_smoke_does_not_apply_scientific_performance_selection():
    cases, data = rows()
    result = compare(data, cases, mechanics_only=True)
    assert result["mechanics_only"] and result["mechanics_pass"]
    assert not result["continue_to_fresh_development"]
    assert not any(key.startswith("delay_gain") for key in result["checks"])


def test_actual_rollout_is_deterministic_and_packets_exclude_simulator_motion_fields():
    case = panel_cases(smoke=True)[0]
    case = {**case, "scenario": {**case["scenario"], "duration_steps": 150, "scenario_hash": ""}}
    first = rollout(case, "window_extension", RunBudget(30))
    repeated = rollout(case, "window_extension", RunBudget(30))
    assert first == repeated
    assert first["result"]["samples"] == 150 and first["result"]["violations"] == 0
    assert first["frames"][0]["packet"]["source_tick"] is None
    for frame in first["frames"]:
        for sample in frame["packet"]["tracks"]:
            assert set(sample) == {"track_id", "movement", "position"}
    reference = rollout(case, "age_gated_advanced_mp", RunBudget(30))
    assert first["result"]["arrival_trace_hash"] == reference["result"]["arrival_trace_hash"]


def test_wait_population_includes_unfinished_and_rejects_nonconservation():
    assert wait_metrics([0., 10., 20.], 1, 3)["delay"] == 10.
    with pytest.raises(ValueError, match="conserve"):
        wait_metrics([0., 10.], 1, 3)


def test_frozen_plan_has_no_validation_or_test_access():
    cases = panel_cases()
    assert cases == panel_cases()
    assert {c["seed"] for c in cases} == set(range(1341001, 1341007))
    assert all(c["scenario"]["split"] == "train" and c["scenario"]["duration_steps"] == 1200 for c in cases)
