import copy

import numpy as np
import pytest

from research.analysis.sumo_trace_metrics import gate_features, origin_map, signal_partition, wait_partition
from research.audits.audit_sumo_action_mechanism import paired_metrics, run
from server.app.controllers.base import ControllerContext
from server.app.controllers.max_pressure import MaxPressureController


def gate():
    return [dict(tick=79, fsm=dict(phase=0, stage="green", age=79), pending=[], requested=[], vehicles=[
        ["moving_a", "n_in", 80., 5.], ["moving_b", "n_in", 50., 10.],
        ["halted", "e_in", 95., 0.], ["outgoing", "w_out", 20., 8.]])]


def test_halted_counts_can_request_switch_while_more_incoming_traffic_is_moving():
    f = gate_features(gate(), {d+"_in": 100. for d in "nsew"})
    assert f["halted"] == [0, 1] and f["moving"] == [2, 0]
    assert f["halted_proposal"] == 1 and f["total_count_shadow_proposal"] == 0
    assert f["pressure_shadow_proposal"] == 0 and f["raw_pressure"] == [2, 0]
    assert f["geometric_eta_le_4s"] == [1, 0] and f["green_age_s"] == 8


def test_shadow_features_do_not_use_vehicle_id_encoding_or_external_backlog():
    before = gate()
    changed = copy.deepcopy(before)
    changed[-1]["vehicles"][0][0] = "different_seed_profile_future_label"
    changed[-1]["pending"] = [[0, "s", "external"]]
    changed[-1]["requested"] = [[999, "e", "not_a_feature"]]
    original = gate_features(before, {d+"_in": 100. for d in "nsew"})
    other = gate_features(changed, {d+"_in": 100. for d in "nsew"})
    assert other.pop("evaluation_only_entry_backlog") == 1
    original.pop("evaluation_only_entry_backlog")
    assert original == other
    for field, value in (("age", 78), ("stage", "yellow")):
        broken = gate()
        broken[-1]["fsm"][field] = value
        with pytest.raises(ValueError, match="eligible"):
            gate_features(broken, {d+"_in": 100. for d in "nsew"})


def test_shadow_pressure_matches_existing_controller_on_same_clean_counts():
    f = gate_features(gate(), {d+"_in": 100. for d in "nsew"})
    controller = MaxPressureController(max_cap_in=1., max_cap_out=1.)
    ctx = ControllerContext(timestep=80, current_phase=0, can_switch_phase=True,
        movement_queues={"north_straight": 2, "east_straight": 1}, outgoing_counts={"west": 1})
    assert controller.act(np.zeros(28), ctx) == f["pressure_shadow_proposal"]


def branch(include_future=True):
    rows = []
    for tick in range(400):
        vehicles = [["existing", "n_in", 10., 0.], ["future", ":junction", 1., 0. if include_future else 4.]]
        rows.append(dict(tick=80+tick, vehicles=vehicles, pending=[[70, "s", "entry"]],
                         wait_vehicle_seconds=.3 if include_future else .2))
    return rows


def test_wait_partitions_conserve_origin_location_cohort_and_prefixes():
    origins = {"existing": "n", "future": "e", "entry": "s"}
    values = wait_partition(branch(), origins, {"existing", "entry"})
    assert values["total"] == 120.
    assert values["by_origin"] == dict(n=40., s=40., e=40., w=0.)
    assert values["by_location"] == dict(incoming=40., outgoing=0., internal=40., entry_backlog=40.)
    assert values["by_cohort"] == dict(present_at_gate=80., arrived_after_gate=40.)
    assert sum(values["by_window"]) == values["total"]
    assert values["cumulative"][19] == 6.
    difference = paired_metrics(dict(waiting=values, signal=dict(seconds=dict.fromkeys(("green", "yellow", "red", "green_0", "green_1"), 0.))),
        dict(waiting=wait_partition(branch(False), origins, {"existing", "entry"}),
             signal=dict(seconds=dict.fromkeys(("green", "yellow", "red", "green_0", "green_1"), 0.))))
    assert difference["delay_saved"] == 40. and difference["by_origin.e"] == 40.
    assert difference["saved_until_2s"] == 2. and difference["saved_window_30_40s"] == 10.


@pytest.mark.parametrize("mutation", ["recorded_wait", "unknown_id", "duplicate", "missing_tick"])
def test_fabricated_or_incomplete_wait_trace_is_rejected(mutation):
    trace = branch()
    origins = {"existing": "n", "future": "e", "entry": "s"}
    if mutation == "recorded_wait":
        trace[0]["wait_vehicle_seconds"] = 99.
    elif mutation == "unknown_id":
        del origins["future"]
    elif mutation == "duplicate":
        trace[0]["pending"].append([70, "n", "existing"])
    else:
        trace[0]["tick"] += 1
    with pytest.raises(ValueError):
        wait_partition(trace, origins, {"existing", "entry"})


def test_signal_partition_and_origin_mapping_do_not_invent_clearance_savings():
    trace = [dict(tick=i, fsm=dict(stage=stage, phase=phase)) for i, (stage, phase) in enumerate(
        [("green", 0)]*200+[("yellow", 0)]*30+[("red", 0)]*10+[("green", 1)]*160)]
    result = signal_partition(trace)
    assert result["seconds"] == dict(green=36., yellow=3., red=1., green_0=20., green_1=16.)
    assert result["switch_onsets"] == 1 and len(result["runs"]) == 4
    assert origin_map([dict(requested=[[1, "n", "arbitrary_id"]])], [[80, "w", "another_id"]]) == {
        "arbitrary_id": "n", "another_id": "w"}
    with pytest.raises(ValueError, match="duplicate"):
        origin_map([dict(requested=[[1, "n", "arbitrary_id"]])], [[80, "w", "arbitrary_id"]])


def test_analysis_outputs_cannot_modify_the_frozen_input_directory(tmp_path):
    original = tmp_path/"original"
    original.mkdir()
    with pytest.raises(ValueError, match="outside the frozen input"):
        run(original, original/"new_analysis")
    assert list(original.iterdir()) == []
