from copy import deepcopy
from dataclasses import asdict, replace
import json

import numpy as np
import pytest

from research.analysis.arrival_reference_gap import analyze_run, service_witness
from research.audits.audit_arrival_reference_gap import AllVisiblePressure, rollout, require_anchor_match
from research.observation.arrival_tracks import Track, TrackFaults, TrackSensor
from research.pilots import run_arrival_window_panel as panel
from research.policies.arrival_extension import ArrivalExtension, Timing
from research.training.train_policy import RunBudget
from server.app.controllers.base import ControllerContext
from server.app.simulation.traffic_signal import TrafficSignal


def frames(positions):
    return [dict(capture=[] if position is None else [dict(track_id=1, movement="north_straight", position=position)],
                 before=dict(phase=0, color="GREEN"), after=dict(phase=0, color="GREEN")) for position in positions]


def test_crossing_at_option_endpoint_is_included_with_a_measurement_interval():
    result = service_witness(frames([.3]*20+[.43]), 0, 1)
    assert result["status"] == "crossed_within_option"
    assert result["crossing_after_s_lower"] == pytest.approx(1.9)
    assert result["crossing_after_s_upper"] == 2.
    assert result["green_ticks"] == 20 and result["endpoint_complete"]


def test_already_discharged_and_missing_tracks_are_not_new_service():
    assert service_witness(frames([.5]*21), 0, 1)["status"] == "already_postline_at_gate"
    assert service_witness(frames([None]*21), 0, 1)["status"] == "missing_at_gate"
    assert service_witness(frames([.3]*21), 0, 1)["status"] == "not_crossed_by_endpoint"


def test_censored_horizon_is_not_a_failed_service_and_observed_success_stays_success():
    assert service_witness(frames([.3]*15), 0, 1)["status"] == "censored_horizon"
    assert service_witness(frames([.3]*5+[.5]*5), 0, 1)["status"] == "crossed_within_option"
    assert service_witness(frames([.3]+[None]*20), 0, 1)["status"] == "lost_before_observed_crossing"


def toy_primary():
    timing = Timing()
    sensor = TrackSensor(panel.CALIBRATION, TrackFaults(), 17)
    policy, protection, signal = ArrivalExtension("window_extension", timing), panel.shield(timing), TrafficSignal()
    waits, result = dict.fromkeys(range(4), 0.), []
    for step in range(120):
        captured = [Track(i+3, "east_straight", .42-.08*i) for i in range(3)]
        if step >= 60:
            captured.append(Track(0, "north_straight", .08+.012*(step-60)))
        state = sensor.replay(tuple(captured), step)
        before = panel.feedback(signal)
        context, waits = panel.build_context(state, before, step, waits, timing)
        proposed = policy.act(state, context)
        decision = protection.filter_context(proposed, context)
        signal.tick(.1, requested_phase=decision.executed_action)
        result.append(dict(step=step, capture=[asdict(t) for t in captured], packet=state.packet.to_dict(),
            before=before, after=panel.feedback(signal), proposed=proposed, executed=decision.executed_action,
            policy=policy.diagnostics.copy(), shield=decision.to_dict()))
    return dict(case=dict(case_id="constructed_service", scenario=dict(red_duration=3.)), method="window_extension", frames=result)


def test_future_truth_can_change_service_labels_but_not_reconstructed_decisions():
    raw = toy_primary()
    original = analyze_run(raw)
    assert original["counts"]["extension_gates"] == 1
    assert original["service_witnesses"][0]["status"] == "crossed_within_option"
    gate = original["service_witnesses"][0]["gate"]
    altered = deepcopy(raw)
    for frame in altered["frames"][gate+1:]:
        for track in frame["capture"]:
            if track["track_id"] == 0:
                track["position"] = .3
    changed = analyze_run(altered)
    assert changed["counts"] == original["counts"]
    assert changed["disagreements"] == original["disagreements"]
    assert changed["service_witnesses"][0]["status"] == "not_crossed_by_endpoint"


def test_trace_diagnosis_rejects_changed_primary_action():
    raw = toy_primary()
    raw["frames"][81]["proposed"] = 3
    with pytest.raises(ValueError, match="do not reconstruct"):
        analyze_run(raw)


def test_cadence_wrapper_changes_only_cache_duration_and_keeps_physical_lock():
    sensor = TrackSensor(panel.CALIBRATION, TrackFaults(), 3)
    first = sensor.replay((Track(0, "north_straight", .2),), 0)
    more = sensor.replay((Track(0, "north_straight", .2), Track(1, "east_straight", .2),
                          Track(2, "east_straight", .3)), 1)
    context = ControllerContext(timestep=100, current_phase=0, time_in_phase=10., valid_action_mask=np.ones(4, bool))
    native, matched = AllVisiblePressure(Timing(), 1), AllVisiblePressure(Timing(), 20)
    assert native.act(first, context) == matched.act(first, context) == 0
    assert native.act(more, replace(context, timestep=101)) == 1
    assert matched.act(more, replace(context, timestep=101)) == 0
    assert matched.act(more, replace(context, timestep=102, is_decision_step=False, current_phase=2)) == 2
    with pytest.raises(ValueError, match="declared"):
        AllVisiblePressure(Timing(), 5)


def test_audit_native_loop_matches_original_real_simulation_exactly():
    case = panel.panel_cases(smoke=True)[0]
    case = {**case, "scenario": {**case["scenario"], "duration_steps": 150, "scenario_hash": ""}}
    original = panel.rollout(case, "mp_all_native", RunBudget(20))
    anchor = rollout(case, 1, RunBudget(20))
    assert anchor == original
    matched = rollout(case, 20, RunBudget(20))
    assert matched["method"] == "mp_all_2s"
    assert matched["result"]["arrival_trace_hash"] == original["result"]["arrival_trace_hash"]
    assert matched["result"]["violations"] == 0


def test_native_anchor_compares_json_representation_and_rejects_real_changes():
    live = dict(frames=[dict(packet=dict(tracks=(dict(track_id=0, position=.3),)))], result=dict(delay=2.34567))
    saved = json.loads(json.dumps(live))
    require_anchor_match(live, saved)
    changed_position = deepcopy(saved)
    changed_position["frames"][0]["packet"]["tracks"][0]["position"] += .00001
    with pytest.raises(ValueError, match="Native anchor"):
        require_anchor_match(live, changed_position)
    changed_metric = deepcopy(saved)
    changed_metric["result"]["delay"] += .00001
    with pytest.raises(ValueError, match="Native anchor"):
        require_anchor_match(live, changed_metric)
