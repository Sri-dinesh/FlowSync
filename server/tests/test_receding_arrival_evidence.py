from copy import deepcopy

import pytest

from research.evidence.export_receding_arrival import service_events, support_summary


def trajectory():
    return dict(case={"case_id":"case"}, method="receding_window", frames=[dict(step=i,
        before={"phase":0}, after={"phase":0, "color":"GREEN" if i < 5 else "YELLOW"},
        capture=[dict(track_id=7, position=.5 if i >= 10 else .3)],
        policy=dict(gate=i in (0,1), reason="supported_extension" if i in (0,1) else "physical_lock", used_ids=[7]))
        for i in range(25)])


def test_witnesses_separate_repeated_credit_shortened_green_and_actual_crossing():
    events = service_events(trajectory())
    assert [e["contiguous_green_ticks"] for e in events] == [5,4]
    assert all(e["status"] == "crossed_within_option" and e["green_hold"] == "cut_short" for e in events)
    assert support_summary(events) == dict(support_events=2, distinct_case_track_pairs=1,
        service_status={"crossed_within_option":2}, green_hold={"cut_short":2}, crossed_after_current_green=2)
    full_green = trajectory()
    for frame in full_green["frames"]:
        frame["after"]["color"] = "GREEN"
    assert all(e["green_hold"] == "full_option" and not e["crossed_after_current_green"] for e in service_events(full_green))


def test_future_capture_changes_labels_without_changing_actions_and_censoring_is_explicit():
    original = trajectory()
    altered = deepcopy(original)
    for frame in altered["frames"]:
        frame["capture"][0]["position"] = .3
    assert [f["policy"] for f in original["frames"]] == [f["policy"] for f in altered["frames"]]
    assert all(e["status"] == "not_crossed_by_endpoint" for e in service_events(altered))
    censored = trajectory()
    censored["frames"] = censored["frames"][:3]
    assert all(e["status"] == "censored_horizon" and e["green_hold"] == "censored" for e in service_events(censored))
    censored["frames"][1]["step"] = 10
    with pytest.raises(ValueError, match="contiguous"):
        service_events(censored)
