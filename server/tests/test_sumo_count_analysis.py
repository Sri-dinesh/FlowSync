import copy

import pytest

from research.analysis.analyze_sumo_count_ablation import demand_role, paired_vehicles, profile, run


def fixture():
    schedule = [[0, "n", "arbitrary"], [0, "e", "queued"]]
    rows = [dict(tick=i, requested=schedule if i == 0 else [],
        vehicles=[["arbitrary", "n_in", 10., 0. if i == 0 else 2.]],
        pending=[[0, "e", "queued"]], arrived=[], wait_vehicle_seconds=.2 if i == 0 else .1,
        fsm=dict(stage="green" if i < 2 else "yellow" if i == 2 else "red", phase=0)) for i in range(4)]
    return schedule, rows


def test_wait_denominators_unfinished_entry_queue_and_phase_absence_are_distinct():
    schedule, rows = fixture()
    result = profile(rows, schedule)
    assert result["wait_vehicle_seconds"] == .5
    assert result["axes"]["ns"]["mean_wait_s"] == .1
    assert result["axes"]["ew"]["mean_wait_s"] == result["axes"]["ew"]["p95_wait_s"] == .4
    assert result["axes"]["ew"]["completed_trips"] == 0
    assert result["axes"]["ew"]["longest_green_absence_with_stopped_demand_s"] == .4
    assert result["axes"]["ns"]["longest_green_absence_s"] == .2
    assert result["axes"]["ns"]["longest_green_absence_with_stopped_demand_s"] == 0
    assert result["signal"]["seconds"]["yellow"] == .1


@pytest.mark.parametrize("mutation", ["wait", "duplicate", "unknown", "missing_tick", "nonfinite", "missing_arrivals"])
def test_invalid_attribution_inputs_are_rejected(mutation):
    schedule, original = fixture()
    rows = copy.deepcopy(original)
    if mutation == "wait":
        rows[0]["wait_vehicle_seconds"] = 0
    elif mutation == "duplicate":
        rows[0]["pending"].append([0, "n", "arbitrary"])
    elif mutation == "unknown":
        rows[0]["vehicles"][0][0] = "unknown"
    elif mutation == "missing_tick":
        rows[0]["tick"] = 1
    elif mutation == "nonfinite":
        rows[0]["vehicles"][0][3] = float("nan")
    else:
        rows[0]["requested"] = []
    with pytest.raises(ValueError):
        profile(rows, schedule)


def test_completed_vehicles_and_zero_wait_requests_stay_in_axis_denominator():
    schedule, rows = fixture()
    rows[0]["vehicles"][0][3] = 2.
    rows[0]["wait_vehicle_seconds"] = .1
    rows[1]["vehicles"] = []
    rows[1]["arrived"] = ["arbitrary"]
    for row in rows[2:]:
        row["vehicles"] = []
    result = profile(rows, schedule)
    assert result["axes"]["ns"]["requested"] == 1
    assert result["axes"]["ns"]["completed_trips"] == 1
    assert result["axes"]["ns"]["mean_wait_s"] == 0.


def test_demand_role_uses_declared_rates_not_ids_or_realized_outcomes():
    plan = dict(seed=1, family="any_label", ns_rate=.3, ew_rate=.1)
    assert demand_role(plan, "ns") == "higher_demand"
    assert demand_role(plan, "ew") == "lower_demand"
    plan.update(ns_rate=.1, ew_rate=.3)
    assert demand_role(plan, "ns") == "lower_demand"
    assert demand_role(dict(ns_rate=.2, ew_rate=.2), "ns") == "balanced"


def test_paired_wait_and_completed_trip_changes_preserve_same_vehicle_identity():
    a = {"id": dict(axis="ew", wait_s=4., completed=True)}
    b = {"id": dict(axis="ew", wait_s=2., completed=False)}
    result = paired_vehicles(a, b, dict(seed=1, family="x", ns_rate=.3, ew_rate=.1))[0]
    assert result["wait_saved_s"] == -2. and result["role"] == "lower_demand"
    assert result["total_completed"] and not result["pressure_completed"]
    with pytest.raises(ValueError, match="paired"):
        paired_vehicles(a, {}, {})
    b["id"]["axis"] = "ns"
    with pytest.raises(ValueError, match="origin changed"):
        paired_vehicles(a, b, {})


def test_analysis_outputs_cannot_modify_either_frozen_input_directory(tmp_path):
    count, reference = tmp_path/"count", tmp_path/"classical"
    count.mkdir()
    reference.mkdir()
    for original in (count, reference):
        with pytest.raises(ValueError, match="outside both frozen"):
            run(count, reference, original/"analysis")
    assert not list(count.iterdir()) and not list(reference.iterdir())
