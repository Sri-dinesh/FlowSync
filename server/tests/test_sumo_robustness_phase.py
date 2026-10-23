import copy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from research.analysis.sumo_robustness_metrics import measurements, summarize
from research.audits.sumo_branch_feasibility import Signal
from research.experiments import sumo_observed_episode as base
from research.experiments import sumo_robustness as spec
from research.policies.sumo_classical import Clock, observe
from research.policies.sumo_total_count import policy_for

AXES = [0, 1, 0, 1]


def canonical_trace(schedule, steps, phase, controller="max_pressure"):
    """Synthetic inventory/phase contract fixture, not a traffic simulation."""
    signal = Signal(phase=phase, pending=phase)
    active, previous, trace = {}, [], []
    for tick in range(steps):
        requests = [a for a in schedule if a[0] == tick]
        frame = dict(tick=tick, requested=requests)
        if tick % 20 == 0:
            packet = observe(previous)
            proposal = policy_for(controller)(packet, Clock(signal.phase, signal.stage, signal.age))
            frame["decision"] = dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
            signal.request(proposal)
        active.update({a[2]: [a[2], a[1]+"_in", 100., 1.] for a in requests})
        frame.update(fsm=asdict(signal), lamps=signal.lamps(AXES), vehicles=list(active.values()),
                     pending=[], inserted=[a[2] for a in requests], arrived=[], wait_vehicle_seconds=0.)
        trace.append(frame)
        previous = frame["vehicles"]
        signal.advance()
    return trace


@pytest.mark.parametrize("phase", [0, 1])
def test_real_adapter_clocks_counts_and_ew_clearance_match_canonical_fsm(monkeypatch, phase):
    vehicles = [["one", "n_in", 30., 2.], ["two", "s_in", 40., 3.], ["three", "e_in", 20., 4.]]
    def step(conn, signal, axes, tick, arrivals, backlog, first_action):
        if tick % 20 == 0:
            assert first_action is not None
            signal.request(first_action)
        frame = dict(tick=tick, fsm=asdict(signal), lamps=signal.lamps(axes), vehicles=vehicles,
                     requested=[], pending=[], arrived=[], inserted=[], wait_vehicle_seconds=0.)
        signal.advance()
        return frame, backlog
    monkeypatch.setattr(base, "advance", step)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda: 0), vehicle=SimpleNamespace(getIDList=lambda: []))
    policy = policy_for("total_incoming")
    trace = list(spec.episode(conn, AXES, dict(steps=160, schedule=[]), policy, phase, lambda: None))
    signal, previous = Signal(phase=phase, pending=phase), []
    for frame in trace:
        if frame["tick"] % 20 == 0:
            packet = observe(previous)
            proposal = policy(packet, Clock(signal.phase, signal.stage, signal.age))
            assert frame["decision"] == dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
            signal.request(proposal)
        assert frame["fsm"] == asdict(signal) and frame["lamps"] == signal.lamps(AXES)
        previous = frame["vehicles"]
        signal.advance()
    if phase == 1:
        assert trace[0]["lamps"] == "rGrG"
        assert trace[80]["fsm"]["stage"] == "yellow" and trace[80]["lamps"] == "ryry"
        assert trace[110]["lamps"] == "rrrr" and trace[120]["lamps"] == "GrGr"


def test_relabelling_is_reversible_and_leaves_packets_vehicle_data_lamps_and_timers_intact():
    frame = canonical_trace([[0, "n", "a"]], 21, 1)[20]
    original = copy.deepcopy(frame)
    mapped = spec.relabel_frame(frame, 1)
    assert spec.relabel_frame(mapped, 1) == frame == original
    assert spec.relabel_frame(frame, 0) == frame
    for key in ("vehicles", "lamps", "requested", "pending", "wait_vehicle_seconds"):
        assert mapped[key] == frame[key]
    assert mapped["decision"]["packet"] == frame["decision"]["packet"]
    assert mapped["fsm"]["age"] == frame["fsm"]["age"]


@pytest.mark.parametrize("phase", [True, -1, 2, 0.])
def test_invalid_initial_labels_and_policy_actions_are_rejected(phase):
    with pytest.raises(ValueError, match="integer"):
        spec.phase_value(phase)
    selected = spec.relabel_policy(lambda packet, clock: phase, 1)
    with pytest.raises(ValueError, match="integer"):
        selected(observe([]), Clock(0, "green", 0))


@pytest.mark.parametrize("phase", [0, 1])
def test_endpoints_exclude_future_requests_and_preserve_canonical_phase(phase):
    cfg = spec.configuration(True)
    schedule = [[0, "n", "a"], [1, "s", "b"], [500, "e", "future"]]
    plan = dict(seed=112901, family="balanced", ns_rate=.2, ew_rate=.2, steps=800, schedule=schedule)
    task = dict(steps=800, controller="max_pressure", initial_phase=phase)
    trace = canonical_trace(schedule, 800, phase)
    measured = measurements(trace, plan, task, AXES, cfg)
    assert measured["40"]["overall"]["requested_vehicles"] == 2
    assert measured["80"]["overall"]["requested_vehicles"] == 3
    assert measured["40"]["axes"]["ew"]["requested"] == 0
    assert measured["80"]["axes"]["ew"]["requested"] == 1
    wrong = copy.deepcopy(trace)
    wrong[0]["fsm"]["phase"] ^= 1
    with pytest.raises(ValueError):
        measurements(wrong, plan, task, AXES, cfg)
    with pytest.raises(ValueError, match="extended"):
        measurements(trace+[trace[-1]], plan, task, AXES, cfg)


def synthetic_rows():
    rows = []
    for task in spec.jobs():
        windows = {}
        for seconds in (180, 360):
            pressure = task["controller"] == "max_pressure"
            wait = 10. if pressure else 9. if seconds == 180 else 8. if task["initial_phase"] == 0 else 14.
            overall = dict(requested_vehicles=20, mean_stopped_wait_per_requested_vehicle_s=wait,
                p95_accumulated_wait_s=wait*2, max_accumulated_wait_s=wait*3, completed_trips=8,
                final_active=12, final_entry_backlog=0, endpoint_max_active_pending_wait_s=wait, switch_onsets=3)
            axis = dict(requested=10, mean_wait_s=wait, p95_wait_s=wait*2, completed_trips=4)
            windows[str(seconds)] = dict(overall=overall, axes=dict(ns=axis.copy(), ew=axis.copy()))
        rows.append(dict(**task, measurements=windows))
    return rows


def test_hierarchy_keeps_six_traffic_seeds_and_reports_both_starts_and_horizons():
    result = summarize(synthetic_rows(), spec.plans(), spec.configuration())
    primary = result["endpoint_comparisons"]["360"]
    assert primary["primary"] and len(primary["case_results"]) == 12
    assert primary["aggregate"]["traffic_seeds"] == 6 and primary["aggregate"]["paired_start_contexts"] == 12
    assert primary["aggregate"]["mean"]["mean_wait_saved_s"] == -1.
    assert primary["aggregate"]["seed_direction_counts"]["lower_mean_wait_saved_s"]["traffic_seeds"] == 4
    assert primary["by_initial_phase"]["0"]["mean"]["mean_wait_saved_s"] == 2.
    assert primary["by_initial_phase"]["1"]["mean"]["mean_wait_saved_s"] == -4.
    assert len(primary["initial_phase_mean_wait_sign_changes"]) == 6
    assert len(result["sensitivity"]["seed_mean_wait_sign_changes_between_endpoints"]) == 6
    assert result["sensitivity"]["prefix_is_overlapping"]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unpaired_denominator"])
def test_full_summary_rejects_missing_duplicates_and_unpaired_requested_counts(mutation):
    rows = synthetic_rows()
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(rows[0])
    else:
        rows[0]["measurements"]["360"]["overall"]["requested_vehicles"] += 1
    with pytest.raises(ValueError):
        summarize(rows, spec.plans(), spec.configuration())
