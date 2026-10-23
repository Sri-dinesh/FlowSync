import copy

import pytest

from research.analysis.analyze_sumo_classical_panel import (
    contrast_summary, decision_comparison, first_proposal_split, run, trace_measurements,
)


def decision(incoming=(10, 0, 4, 0), outgoing=(0, 0, 0, 0), halted=(0, 0, 4, 0), **clock):
    return dict(packet=dict(incoming=list(incoming), outgoing=list(outgoing), halted=list(halted)), proposal=1,
                before_fsm=dict(phase=0, stage="green", age=80, pending=0, **clock))


def test_moving_input_and_outgoing_counts_have_distinct_same_state_effects():
    moving = decision_comparison(decision())
    assert (moving["halted"], moving["total_incoming"], moving["max_pressure"]) == (1, 0, 0)
    assert moving["pattern"] == "total_and_pressure_agree"
    outgoing = decision_comparison(decision(outgoing=(0, 8, 0, 0), halted=(1, 0, 0, 0)))
    assert (outgoing["halted"], outgoing["total_incoming"], outgoing["max_pressure"]) == (0, 0, 1)
    assert outgoing["pattern"] == "halted_and_total_agree"
    cancellation = decision_comparison(decision(outgoing=(0, 8, 0, 0)))
    assert cancellation["pattern"] == "halted_and_pressure_agree"


@pytest.mark.parametrize("stage,age", [("green", 79), ("yellow", 20), ("red", 5)])
def test_ineligible_contexts_do_not_create_shadow_disagreements(stage, age):
    value = decision()
    value["before_fsm"].update(stage=stage, age=age)
    result = decision_comparison(value)
    assert not result["eligible"] and result["pattern"] == "all_agree"


def trace():
    # One stopped existing vehicle and one entry request; IDs carry no route semantics.
    return [dict(tick=0, fsm=dict(stage="green", phase=0), decision=decision(),
                 vehicles=[["arbitrary", "n_in", 0., 0.], ["moving", "s_out", 1., 2.]],
                 pending=[[0, "e", "queued"]], wait_vehicle_seconds=.2)]


def test_wait_partitions_and_proposals_keep_separate_units():
    values = trace_measurements(trace(), [[0, "n", "arbitrary"], [0, "e", "queued"], [0, "s", "moving"]])
    assert values["wait_vehicle_seconds"] == .2
    assert values["wait_by_origin"] == dict(n=.1, s=0., e=.1, w=0.)
    assert values["wait_by_location"] == dict(incoming=.1, outgoing=0., internal=0., entry_backlog=.1)
    assert values["decisions"]["eligible_decisions"] == 1
    assert values["decisions"]["halted_differs_pressure"] == 1
    assert values["signals"]["seconds"]["green"] == .1


@pytest.mark.parametrize("mutation", ["duplicate_wait", "unknown_origin", "wrong_wait"])
def test_invalid_wait_partitions_are_rejected(mutation):
    rows = trace()
    schedule = [[0, "n", "arbitrary"], [0, "e", "queued"]]
    if mutation == "duplicate_wait":
        rows[0]["pending"].append([0, "n", "arbitrary"])
    elif mutation == "unknown_origin":
        schedule.pop()
    else:
        rows[0]["wait_vehicle_seconds"] = 0.
    with pytest.raises(ValueError):
        trace_measurements(rows, schedule)


def test_first_split_requires_identical_preceding_history_packet_and_context():
    left = [dict(tick=0), dict(tick=20, decision=decision(), lamps="yryr")]
    right = copy.deepcopy(left)
    right[1]["decision"]["proposal"] = 0
    right[1]["lamps"] = "GrGr"
    split = first_proposal_split(left, right)
    assert split["tick"] == 20 and split["halted_proposal"] == 1 and split["pressure_proposal"] == 0
    assert first_proposal_split(left, left) is None
    right[0]["vehicles"] = []
    with pytest.raises(ValueError, match="before an observed proposal"):
        first_proposal_split(left, right)
    with pytest.raises(ValueError, match="horizons"):
        first_proposal_split(left, right[:1])


def test_better_mean_wait_does_not_hide_tail_or_trip_regressions():
    cases = [dict(seed=1, family="x", mean_wait_saved_s=1., p95_wait_saved_s=-1., completed_trips_gained=0),
             dict(seed=2, family="x", mean_wait_saved_s=2., p95_wait_saved_s=2., completed_trips_gained=-1),
             dict(seed=3, family="x", mean_wait_saved_s=3., p95_wait_saved_s=0., completed_trips_gained=1)]
    result = contrast_summary(cases)
    assert result["direction_counts"]["mean_wait_saved_s"]["improved"] == 3
    assert result["lower_mean_wait_without_p95_or_trip_loss"] == 1
    assert len(result["regression_cases"]) == 2 and result["mean"]["completed_trips_gained"] == 0
    with pytest.raises(ValueError):
        contrast_summary([])


def test_analysis_cannot_write_into_original_evidence(tmp_path):
    source = tmp_path/"original"
    source.mkdir()
    with pytest.raises(ValueError, match="outside the frozen"):
        run(source, source/"analysis")
    assert list(source.iterdir()) == []
