from dataclasses import replace
import json

import numpy as np
import pytest

from research.audits.audit_arrival_reference_gap import require_anchor_match
from research.experiments.track_runtime import rollout_tracks, replay_tracks
from research.observation.arrival_tracks import Calibration, DeliveredState, Motion, Packet, Track
from research.pilots import run_arrival_window_panel as v1
from research.pilots.run_receding_arrival_panel import cases, comparison, METHODS, PRIMARY
from research.policies.arrival_extension import Timing
from research.policies.receding_arrival import CadencedArrival
from research.training.train_policy import RunBudget
from server.app.controllers.base import ControllerContext


def state(past=False):
    calibration = Calibration(dedicated_movement_lanes=True)
    current = Motion(Track(0, "north_straight", .5 if past else .32), "moving", (.11, .12, .12))
    opposing = tuple(Motion(Track(i+1, "east_straight", .42-.08*i), "stopped") for i in range(3))
    motions = (current,)+opposing
    return DeliveredState(Packet(100, 100, calibration.sha256, tuple(m.track for m in motions)), motions, calibration)


def test_receding_changes_commitment_clock_but_preserves_initial_rule_and_locks():
    context = ControllerContext(timestep=100, current_phase=0, time_in_phase=10., valid_action_mask=np.ones(4, bool))
    fixed, receding = CadencedArrival("window_2s", Timing()), CadencedArrival("receding_window", Timing())
    assert fixed.act(state(), context) == receding.act(state(), context) == 0
    assert fixed.diagnostics == receding.diagnostics
    assert fixed.act(state(past=True), replace(context, timestep=101)) == 0
    assert receding.act(state(past=True), replace(context, timestep=101)) == 1
    assert not fixed.diagnostics["gate"] and receding.diagnostics["gate"]
    assert receding.act(state(), replace(context, timestep=102, current_phase=2, is_decision_step=False)) == 2


@pytest.mark.parametrize("label,original", [("mp_all_native", "mp_all_native"), ("window_2s", "window_extension")])
def test_shared_runtime_preserves_original_native_and_two_second_bundles(label, original):
    case = v1.panel_cases(smoke=True)[0]
    case = {**case, "scenario": {**case["scenario"], "duration_steps": 150, "scenario_hash": ""}}
    old = v1.rollout(case, original, RunBudget(20))
    new = rollout_tracks(case, CadencedArrival(label, Timing()), RunBudget(20))
    require_anchor_match({**new, "method": original}, json.loads(json.dumps(old)))
    replay_tracks(json.loads(json.dumps(new)), CadencedArrival(label, Timing()))


def test_replay_rejects_changed_action_without_running_traffic_again():
    case = v1.panel_cases(smoke=True)[0]
    case = {**case, "scenario": {**case["scenario"], "duration_steps": 100, "scenario_hash": ""}}
    raw = rollout_tracks(case, CadencedArrival(PRIMARY, Timing()), RunBudget(20))
    raw["frames"][0]["proposed"] = 3
    with pytest.raises(ValueError, match="controller/shield"):
        replay_tracks(raw, CadencedArrival(PRIMARY, Timing()))


def test_receding_screen_cannot_replace_primary_with_point_ablation_or_incomplete_panel():
    rows = [dict(case_id=c["case_id"], method=method, delay=9. if method == PRIMARY else 10.,
        p95=30., passed=100, samples=1200, violations=0, arrival_trace_hash=c["case_id"])
        for c in cases() for method in METHODS]
    assert len(rows) == 198 and comparison(rows)["continue_to_fresh_development"]
    assert not comparison(rows[:-1])["primary_endpoint_complete"]
    for row in rows:
        if row["method"] == "receding_point":
            row["delay"] = 8.
    assert not comparison(rows)["continue_to_fresh_development"]


def test_new_traffic_seeds_are_disjoint_from_diagnostic_and_remain_train_only():
    new, old = cases(), v1.panel_cases()
    assert len(new) == 18 and new == cases()
    assert {c["seed"] for c in new} == set(range(1342001, 1342007))
    assert not {c["seed"] for c in new} & {c["seed"] for c in old}
    assert all(c["scenario"]["split"] == "train" and c["scenario"]["duration_steps"] == 1200 for c in new)
