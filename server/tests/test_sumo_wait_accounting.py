import copy

import pytest

from research.analysis.analyze_sumo_wait_accounting import aggregate, analyse, decompose, run, window_cost


PLAN = dict(seed=1, family="ns_dominant", ns_rate=.3, ew_rate=.1)


def measurement(ns_count, ew_count, ns_wait, ew_wait):
    return dict(axes={a: dict(requested=n, wait_vehicle_seconds=w, mean_wait_s=w/n)
                     for a, n, w in (("ns", ns_count, ns_wait), ("ew", ew_count, ew_wait))},
                overall=dict(requested_vehicles=ns_count+ew_count,
                             total_stopped_wait_vehicle_seconds=ns_wait+ew_wait,
                             mean_stopped_wait_per_requested_vehicle_s=(ns_wait+ew_wait)/(ns_count+ew_count)))


def test_weighted_average_can_hide_lower_demand_harm_without_changing_any_outcome():
    pressure = measurement(90, 10, 900, 100)
    total = measurement(90, 10, 720, 200)
    result = decompose(total, pressure, PLAN)
    assert result["overall_mean_cost_s"] == pytest.approx(-.8)
    assert result["lower_demand_mean_cost_s"] == 10
    assert result["higher_demand_mean_cost_s"] == -2
    assert result["lower_demand_contribution_s"] == 1
    assert result["higher_demand_contribution_s"] == -1.8
    assert result["equal_axis_mean_cost_s"] == 4
    assert abs(result["identity_residual_s"]) < 1e-12


def test_roles_use_configured_rates_and_balanced_roles_remain_absent():
    pressure = measurement(9, 10, 90, 100)
    total = measurement(9, 10, 72, 200)
    # Actual random counts do not define which configured axis has lower demand.
    result = decompose(total, pressure, PLAN)
    assert result["ew_role"] == "lower_demand"
    assert result["lower_demand_requested_share"] == pytest.approx(10/19)
    balanced = decompose(total, pressure, dict(PLAN, ns_rate=.2, ew_rate=.2))
    assert balanced["lower_demand_mean_cost_s"] is None
    assert balanced["higher_demand_contribution_s"] is None
    assert balanced["overall_mean_cost_s"] == result["overall_mean_cost_s"]


@pytest.mark.parametrize("mutation", ["axis_count", "total_count", "total_wait", "mean", "nan"])
def test_changed_denominators_and_nonconserving_measurements_fail(mutation):
    pressure = measurement(90, 10, 900, 100)
    total = measurement(90, 10, 720, 200)
    if mutation == "axis_count":
        total = measurement(89, 11, 720, 200)
    elif mutation == "total_count":
        total["overall"]["requested_vehicles"] += 1
    elif mutation == "total_wait":
        total["overall"]["total_stopped_wait_vehicle_seconds"] += 1
    elif mutation == "mean":
        total["axes"]["ns"]["mean_wait_s"] += 1
    else:
        total["axes"]["ns"]["wait_vehicle_seconds"] = float("nan")
    with pytest.raises(ValueError):
        decompose(total, pressure, PLAN)


def test_disjoint_windows_subtract_integrals_not_changing_denominator_means():
    pressure = {"180": measurement(9, 1, 90, 10), "360": measurement(90, 10, 900, 100)}
    total = {"180": measurement(9, 1, 72, 20), "360": measurement(90, 10, 720, 200)}
    first = window_cost(total, pressure, 0, 180, PLAN)
    second = window_cost(total, pressure, 180, 360, PLAN)
    assert first["overall_wait_cost_vehicle_seconds"] == -8
    assert second["overall_wait_cost_vehicle_seconds"] == -72
    assert second["overall_average_waiting_inventory_cost"] == pytest.approx(-.4)
    assert second["lower_demand_average_waiting_inventory_cost"] == pytest.approx(.5)
    assert first["overall_wait_cost_vehicle_seconds"]+second["overall_wait_cost_vehicle_seconds"] == -80
    # The per-request means are unchanged between endpoints; subtracting them gives zero.
    assert total["180"]["overall"]["mean_stopped_wait_per_requested_vehicle_s"] == total["360"]["overall"]["mean_stopped_wait_per_requested_vehicle_s"]
    total["360"]["axes"]["ew"]["wait_vehicle_seconds"] = 1
    with pytest.raises(ValueError, match="decreased"):
        window_cost(total, pressure, 180, 360, PLAN)


def test_aggregation_preserves_seed_hierarchy_and_rejects_missing_or_duplicate_starts():
    rows = [dict(seed=s, initial_phase=p, family="balanced", cost=v)
            for s, p, v in ((1, 0, 0), (1, 1, 2), (2, 0, 8), (2, 1, 10))]
    result = aggregate(rows, ["cost"])
    assert result["traffic_seeds"] == 2 and result["paired_start_contexts"] == 4
    assert result["mean"]["cost"] == 5
    assert [r["cost"] for r in result["seed_results"]] == [1, 9]
    for invalid in (rows[:-1], rows+[rows[-1]]):
        with pytest.raises(ValueError, match="both initial phases"):
            aggregate(invalid, ["cost"])


def synthetic_panel():
    plans = [PLAN, dict(PLAN, seed=2, family="balanced", ns_rate=.2, ew_rate=.2)]
    rows = []
    for plan in plans:
        for phase in (0, 1):
            for controller in ("max_pressure", "total_incoming"):
                ns, ew = (90, 10) if controller == "max_pressure" else (72, 20)
                rows.append(dict(seed=plan["seed"], initial_phase=phase, controller=controller,
                                 measurements={"180": measurement(9, 1, ns, ew),
                                               "360": measurement(90, 10, ns*10, ew*10)}))
    return plans, rows


def test_analysis_keeps_balanced_cases_and_both_windows_without_counting_extra_seeds():
    plans, rows = synthetic_panel()
    result = analyse(rows, plans)
    assert len(result["endpoints"]) == len(result["windows"]) == 8
    assert result["endpoint_summary"]["360"]["all"]["traffic_seeds"] == 2
    assert result["endpoint_summary"]["360"]["asymmetric"]["traffic_seeds"] == 1
    assert result["endpoint_summary"]["360"]["balanced"]["traffic_seeds"] == 1
    assert result["window_summary"]["180-360"]["asymmetric_contexts_with_lower_demand_wait_increase"] == 2
    for invalid in (rows[:-1], rows+[copy.deepcopy(rows[-1])]):
        with pytest.raises(ValueError, match="paired runs"):
            analyse(invalid, plans)


def test_output_cannot_overwrite_or_nest_in_evidence(tmp_path):
    source = tmp_path/"frozen"
    source.mkdir()
    (source/"report.json").write_text("preserve")
    with pytest.raises(FileExistsError):
        run(source, source)
    with pytest.raises(ValueError, match="outside"):
        run(source, source/"analysis")
    assert (source/"report.json").read_text() == "preserve"
