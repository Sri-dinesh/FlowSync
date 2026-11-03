"""New ledger panel contracts; constructed outcomes are never traffic evidence."""
from copy import deepcopy
from dataclasses import asdict
import math
from types import SimpleNamespace

import pytest

from research.audits.sumo_branch_feasibility import Signal
from research.analysis.sumo_service_ledger_metrics import mean, seed_interval
from research.experiments import sumo_service_watchdog as watchdog
from research.pilots import run_sumo_service_ledger_panel as study
from research.pilots.run_sumo_switching_panel import digest
from research.policies.sumo_classical import Clock, Counts
from research.policies.sumo_service_watchdog import WATCHDOG_TICKS, after_execution, propose

AXES = [0, 1, 0, 1]
DELAY = "mean_stopped_wait_per_requested_vehicle_s"


def packet(ns=10, ew=1):
    return Counts((ns, 0, ew, 0), (0, 0, 0, 0), (0, 0, 0, 0))


def test_watchdog_requires_observed_demand_and_actual_green_to_reset():
    ages = (0, WATCHDOG_TICKS)
    selected = propose(packet(), Clock(0, "green", 300), ages)
    assert selected["reference"] == 0 and selected["proposal"] == 1 and selected["watchdog_due"]
    assert not propose(packet(), Clock(0, "green", 79), ages)["watchdog_due"]
    assert not propose(packet(), Clock(0, "yellow", 10), ages)["watchdog_due"]
    assert not propose(packet(10, 0), Clock(0, "green", 300), ages)["watchdog_due"]
    assert after_execution(packet(), Clock(0, "yellow", 0), ages) == (1, WATCHDOG_TICKS+1)
    assert after_execution(packet(), Clock(1, "green", 0), ages) == (1, 0)
    assert after_execution(packet(10, 0), Clock(0, "red", 0), ages) == (1, 0)
    assert not propose(packet(), Clock(0, "green", 300), (0, WATCHDOG_TICKS-1))["watchdog_due"]


@pytest.mark.parametrize("ages", [[0, 0], (0, True), (-1, 0), (0,), (0, math.inf)])
def test_watchdog_rejects_malformed_state(ages):
    with pytest.raises(ValueError): propose(packet(), Clock(0, "green", 100), ages)


def install_fake_advance(monkeypatch, runtime):
    active = []
    def advance(conn, signal, axes, tick, requested, backlog, first_action):
        if tick % 20 == 0:
            assert type(first_action) is int and first_action in (0, 1)
            signal.request(first_action)
        active.extend([[a[2], a[1]+"_in", 1., 0.] for a in requested])
        row = dict(tick=tick, fsm=asdict(signal), lamps=signal.lamps(axes), vehicles=deepcopy(active),
            requested=requested, pending=[], inserted=[a[2] for a in requested], arrived=[],
            wait_vehicle_seconds=round(len(active)/10, 6))
        signal.advance()
        return row, backlog
    monkeypatch.setattr(runtime, "advance", advance)
    return SimpleNamespace(simulation=SimpleNamespace(getTime=lambda:0), vehicle=SimpleNamespace(getIDList=lambda:[]))


def adapter_rows(monkeypatch, mode, phase=0, label="mixed"):
    method = mode+"_"+label
    runtime = study.pressure if mode == "max_pressure" else watchdog if mode == "watchdog" else study.ledger
    conn = install_fake_advance(monkeypatch, runtime)
    plan = dict(seed=83, steps=800, schedule=[[0, "n", "a"], [1, "e", "b"]])
    job = dict(seed=83, initial_phase=phase, method=method, kind="episode", repeat=0, steps=800)
    return list(study.episode(conn, AXES, plan, job, lambda:None)), plan, job


@pytest.mark.parametrize("phase", [0, 1])
@pytest.mark.parametrize("mode", study.MODES)
@pytest.mark.parametrize("label", ["clean", "mixed"])
def test_panel_adapters_reconstruct_delivered_policy_execution_and_waiting(monkeypatch, mode, phase, label):
    trace, plan, job = adapter_rows(monkeypatch, mode, phase, label)
    measured = study.measurements(trace, plan, job, AXES, True)
    assert set(measured) == {"40", "80"}
    assert measured["80"]["requested_vehicles"] == 2
    assert measured["80"]["diagnostics"]["green_ns_s"]+measured["80"]["diagnostics"]["green_ew_s"]+measured["80"]["diagnostics"]["clearance_s"] == 80
    if mode in ("ledger", "debt_batch"):
        assert measured["80"]["diagnostics"]["max_absolute_allocation_debt_s"] <= 16


@pytest.mark.parametrize("change", ["ages", "decision", "sensor", "clock", "lamps", "waiting", "offgate", "version", "bool_age"])
def test_watchdog_replay_rejects_corruption(monkeypatch, change):
    trace, plan, job = adapter_rows(monkeypatch, "watchdog")
    if change == "ages": trace[99]["watchdog"]["after"][0] += 1
    elif change == "bool_age": trace[0]["watchdog"]["before"][0] = False
    elif change == "decision": trace[80]["decision"]["proposal"] ^= 1
    elif change == "sensor": trace[30]["sensing"]["counts"]["incoming"][0] += 1
    elif change == "clock": trace[99]["fsm"]["age"] += 1
    elif change == "lamps": trace[99]["lamps"] = "rrrr"
    elif change == "waiting": trace[99]["wait_vehicle_seconds"] += 1
    elif change == "version": trace[99]["watchdog"]["version"] = "other"
    else: trace[99]["decision"] = deepcopy(trace[80]["decision"])
    with pytest.raises((KeyError, ValueError)):
        study.measurements(trace, plan, job, AXES, True)


def scientific_rows():
    frozen = {p["seed"]:p for p in study.plans()}
    result = []
    for job in study.jobs():
        plan = frozen[job["seed"]]
        value = 8 if job["method"].startswith("ledger_") else 10
        measured = {str(end//10):dict(requested_vehicles=len([a for a in plan["schedule"] if a[0] < end]),
            signal_samples=end, measured_signal_violations=0, mean_stopped_wait_per_requested_vehicle_s=value,
            p95_accumulated_wait_s=2*value, max_accumulated_wait_s=3*value, completed_trips=150-value,
            final_active=value, final_entry_backlog=value, endpoint_max_active_pending_wait_s=2*value,
            switch_onsets=3, diagnostics=dict(green_ns_s=end/25)) for end in (1800, 3600)}
        result.append(dict(**job, family=plan["family"], requested_arrival_sha256=digest(plan["schedule"]), measurements=measured))
    return result


def test_full_grid_fresh_development_seeds_and_bounded_mechanics_are_fixed():
    full, smoke = study.jobs(), study.jobs(True)
    assert len(full) == 144 and sum(j["steps"] for j in full) == 518400
    assert len(smoke) == 56 and sum(j["steps"] for j in smoke) == 35200
    assert {j["seed"] for j in full}.isdisjoint(j["seed"] for j in smoke)
    assert study.configuration()["session_cap_seconds"] == 900
    assert study.protocol()["max_sessions"] == 4


@pytest.mark.parametrize("change", ["method", "gate", "seed", "endpoint", "screen", "watchdog", "bool", "pins"])
def test_protocol_refuses_relaxed_controls_or_thresholds(tmp_path, monkeypatch, change):
    spec = study.protocol()
    if change == "method": spec["methods"][0]["mode"] = "debt_batch"
    elif change == "gate": spec["decision_ticks"] = 10
    elif change == "seed": spec["families"][0]["seeds"][0] = 1370001
    elif change == "endpoint": spec["full_steps"] = 1800
    elif change == "screen": spec["candidate_screen"]["minimum_delay_gain_fraction"] = 0
    elif change == "watchdog": spec["watchdog_ticks"] = 200
    elif change == "bool": spec["initial_phases"][0] = False
    else: spec["base_source_sha256"].pop(next(iter(spec["base_source_sha256"])))
    path = tmp_path/study.SPEC; path.parent.mkdir(parents=True); path.write_text(study.json.dumps(spec))
    monkeypatch.setattr(study, "ROOT", tmp_path)
    with pytest.raises(ValueError): study.protocol()


def test_exact_stratified_seed_inference_and_factorial_interaction():
    result = study.analyze(scientific_rows(), False)
    endpoint = result["endpoint_comparisons"]["360"]
    contrast = endpoint["contrasts"]["debt_priority_by_variable_budget_clean"]
    assert contrast["metrics"][DELAY]["mean"] == -2
    assert contrast["metrics"][DELAY]["interval"] == dict(lower=-2, upper=-2, ordered_draws=64)
    assert len(contrast["seed_rows"]) == 6 and len(contrast["context_rows"]) == 12
    assert len(result["candidate_screen"]["comparisons"]) == 10
    assert result["candidate_screen"]["continue_to_bounded_development"]
    assert not result["candidate_screen"]["automatic_promotion"]
    assert result["replication"]["prefix_endpoints_overlap"]
    assert mean([1e16, 1., -1e16]) == 1/3
    with pytest.raises(ValueError): seed_interval({1:0}, [dict(seed=1, family="only")])


@pytest.mark.parametrize("change", ["missing", "duplicate", "order", "denominator", "arrivals", "signal", "samples", "nan"])
def test_grid_accounting_signal_and_finite_measurements_are_required(change):
    rows = scientific_rows()
    if change == "missing": rows.pop()
    elif change == "duplicate": rows[-1] = deepcopy(rows[0])
    elif change == "order": rows[0], rows[1] = rows[1], rows[0]
    elif change == "denominator": rows[0]["measurements"]["180"]["requested_vehicles"] += 1
    elif change == "arrivals": rows[0]["requested_arrival_sha256"] = "0"*64
    elif change == "signal": rows[0]["measurements"]["180"]["measured_signal_violations"] = 1
    elif change == "samples": rows[0]["measurements"]["180"]["signal_samples"] -= 1
    else: rows[0]["measurements"]["180"][DELAY] = math.nan
    with pytest.raises(ValueError): study.analyze(rows, False)


@pytest.mark.parametrize("change", ["bad_seed", "bad_start", "bad_tail", "bad_trips", "mixed_loss", "matched_budget_tie"])
def test_aggregate_gain_cannot_hide_harm_or_substitute_a_weaker_control(change):
    rows = scientific_rows()
    for row in rows:
        m = row["measurements"]["360"]
        if row["method"] == "ledger_clean":
            if change == "bad_seed" and row["seed"] == 1380001: m[DELAY] = 10.2
            if change == "bad_start": m[DELAY] = 10.5 if row["initial_phase"] == 0 else 5
            if change == "bad_tail": m["p95_accumulated_wait_s"] = 21
            if change == "bad_trips": m["completed_trips"] = 139
        if change == "mixed_loss" and row["method"] == "ledger_mixed": m[DELAY] = 11
        if change == "matched_budget_tie" and row["method"] == "pressure_budget_clean": m[DELAY] = 8
    screen = study.analyze(rows, False)["candidate_screen"]
    assert not screen["continue_to_bounded_development"]
    key = dict(bad_seed="seed_loss_ledger_vs_max_pressure_clean", bad_start="start_group_loss_ledger_vs_max_pressure_clean",
        bad_tail="p95_ledger_vs_max_pressure_clean", bad_trips="throughput_ledger_vs_max_pressure_clean",
        mixed_loss="mean_wait_ledger_vs_max_pressure_mixed", matched_budget_tie="mean_wait_ledger_vs_pressure_budget_clean")[change]
    assert key in screen["failures"]


def smoke_rows():
    plan = study.plans(True)[0]
    rows = []
    for job in study.jobs(True):
        key = str(job["initial_phase"])+job["method"]
        rows.append(dict(**job, requested_arrival_sha256=digest([a for a in plan["schedule"] if a[0] < job["steps"]]),
            semantic_trace_sha256="prefix"+key if job["kind"] == "prefix" else key, prefix_trace_sha256="prefix"+key,
            measurements={str(end//10):dict(signal_samples=end, measured_signal_violations=0,
                allocation=dict(credited_green_ticks=60, completed_batches=1)) for end in (400, 800) if end <= job["steps"]}))
    return rows


def test_smoke_is_execution_only_and_cannot_promote_a_controller():
    proof = study.analyze(smoke_rows(), True)
    assert proof["mechanics"]["all_prefix_replays_verified"]
    assert proof["candidate_screen"] is None and proof["performance_evaluated"] is False
    assert proof["endpoint_comparisons"] == {}


@pytest.mark.parametrize("change", ["repeat", "watchdog_repeat", "prefix", "no_credit", "no_completion"])
def test_smoke_requires_native_repeat_prefix_and_primary_receipt_coverage(change):
    rows = smoke_rows()
    if change in ("repeat", "watchdog_repeat"):
        row = next(r for r in rows if r["repeat"] == 1 and r["method"].startswith("watchdog" if change == "watchdog_repeat" else "ledger"))
        row["semantic_trace_sha256"] = "changed"
    elif change == "prefix": next(r for r in rows if r["kind"] == "prefix")["semantic_trace_sha256"] = "changed"
    else: rows[0]["measurements"]["80"]["allocation"]["credited_green_ticks" if change == "no_credit" else "completed_batches"] = 0
    with pytest.raises(ValueError): study.analyze(rows, True)
