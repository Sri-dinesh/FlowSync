import copy

import pytest

from research.audit_arrival_label_stability import future_seed, resample_branches
from research.evaluate_averaged_action_labels import (
    ARMS, EVAL_IDS, FIT_IDS, SMOKE_IDS, freeze_choices, score_source, summarize,
)


def branches(delays, trace):
    return [dict(proposal=a, first_execution=a, outcome=dict(
        incremental_delay_vehicle_seconds=d, vehicles_passed=3, upstream_max_wait_s=10.,
        signal_samples=400, signal_violations=0, arrival_trace_hash=trace))
            for a, d in enumerate(delays)]


def source(indices=FIT_IDS, delays=(100., 102., 80.)):
    row = dict(training_seed=101, scenario="train_fixture", seed=95001,
               data_role="fit", split="train", fault=dict(name="clean"), events=[])
    for step in (200, 400, 600):
        row["events"].append(dict(step=step, policy_proposal=0, mask=[True, True, True, False],
            all_action_branches=branches((100., 80., 95.), "original"),
            branch_diagnostic=[dict(replicate=i, arrival_seed=future_seed(101, "train_fixture", 95001, step, i),
                                    branches=branches(delays, str(i))) for i in indices]))
    return row


def test_choices_use_old_eight_means_not_original_or_new_outcomes():
    selection = source()
    frozen = freeze_choices([selection])
    assert len(frozen) == 3
    assert all(c["single"] == 1 and c["mean8"] == 2 and c["parent"] == 0 for c in frozen)
    before = copy.deepcopy(frozen)
    evaluated = source(EVAL_IDS, (100., 110., 90.))
    scores, rows = score_source(evaluated, frozen, EVAL_IDS)
    assert scores["arms"]["single"]["mean_gain"] == [-10., 0., 0.]
    assert scores["arms"]["mean8"]["mean_gain"] == [10., 0., 0.]
    assert scores["arms"]["parent"]["mean_gain"] == [0., 0., 0.]
    assert len(rows) == 72
    assert all(r["choice"] == 2 for r in rows if r["arm"] == "mean8")
    # Evaluation can become arbitrarily unfavorable without changing a choice.
    changed = source(EVAL_IDS, (100., 1., 1000.))
    _, altered = score_source(changed, frozen, EVAL_IDS)
    assert frozen == before
    assert all(r["choice"] == 2 for r in altered if r["arm"] == "mean8")
    assert all(r["harmful"] for r in altered if r["arm"] == "mean8")


def test_roles_and_future_splits_are_disjoint_and_enforced():
    sets = [{future_seed(101, "fixture", 95001, 200, i) for i in ids}
            for ids in (FIT_IDS, EVAL_IDS, SMOKE_IDS)]
    assert all(len(s) == 8 for s in sets)
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    with pytest.raises(ValueError, match="Wrong future split"):
        freeze_choices([source(EVAL_IDS)])
    with pytest.raises(ValueError, match="Wrong future split"):
        score_source(source(), freeze_choices([source()]), EVAL_IDS)
    row = source()
    row["split"] = "validation"
    with pytest.raises(ValueError, match="fitting sources"):
        freeze_choices([row])


def test_bad_seed_unpaired_arrivals_and_bad_audits_rejected():
    row = source()
    row["events"][0]["branch_diagnostic"][0]["arrival_seed"] += 1
    with pytest.raises(ValueError, match="seed mismatch"):
        freeze_choices([row])
    row = source()
    row["events"][0]["branch_diagnostic"][0]["branches"][1]["outcome"]["arrival_trace_hash"] = "wrong"
    with pytest.raises(ValueError, match="Unpaired"):
        freeze_choices([row])
    row = source()
    row["events"][0]["branch_diagnostic"][0]["branches"][1]["outcome"]["signal_violations"] = 1
    with pytest.raises(ValueError, match="Invalid branch"):
        freeze_choices([row])
    with pytest.raises(ValueError, match="Duplicate decision"):
        freeze_choices([source(), source()])


@pytest.mark.parametrize("indices", [range(7), [0] * 8, [-1, 0, 1, 2, 3, 4, 5, 6], [True, 1, 2, 3, 4, 5, 6, 7]])
def test_bad_replicate_indices_rejected_before_simulation(indices):
    with pytest.raises(ValueError, match="eight distinct"):
        resample_branches(101, None, None, None, None, None, None, 0, 400, 0,
                          replicate_indices=indices)


def scores():
    result = []
    for parent in (101, 202, 303):
        for scenario in range(6):
            arms = {}
            for arm in ARMS:
                arms[arm] = dict(mean_gain=[{"parent": 0., "single": -1., "mean8": 1.}[arm], 0., 0.],
                                 cases=24, changed_cases=0 if arm == "parent" else 16,
                                 executed_change_cases=0 if arm == "parent" else 16,
                                 qualified_cases=8 if arm == "mean8" else 0,
                                 harmful_cases=8 if arm == "single" else 0)
            result.append(dict(training_seed=parent, scenario=str(scenario), seed=95001, arms=arms))
    return result


def test_screen_requires_complete_active_beneficial_non_smoke_panel():
    rows = scores()
    report = summarize(rows, 18, False)
    assert report["continue_to_label_model_pilot"]
    assert report["arms"]["mean8"]["mean_gain"] == [1., 0., 0.]
    assert not report["model_trained"] and not report["publication_ready"]
    assert not summarize(rows[:1], 1, True)["continue_to_label_model_pilot"]
    assert not summarize(rows[:-1], 18, False)["continue_to_label_model_pilot"]
    assert summarize([], 18, False)["arms"]["mean8"]["mean_gain"] is None
    for r in rows:
        r["arms"]["mean8"].update(mean_gain=[0., 0., 0.], changed_cases=0,
                                  executed_change_cases=0, qualified_cases=0)
    report = summarize(rows, 18, False)
    assert not report["continue_to_label_model_pilot"]
    assert not report["checks"]["positive_delay_gain"]
    assert not report["checks"]["every_parent_nonnegative_active_beneficial"]


def test_screen_detects_risk_and_parent_regression():
    rows = scores()
    for r in rows:
        r["arms"]["mean8"]["harmful_cases"] = 16
    assert not summarize(rows, 18, False)["checks"]["harmful_fraction_not_higher"]
    rows = scores()
    for r in rows:
        if r["training_seed"] == 303:
            r["arms"]["mean8"]["mean_gain"][0] = -1.
    report = summarize(rows, 18, False)
    assert report["checks"]["positive_delay_gain"]
    assert not report["checks"]["every_parent_nonnegative_active_beneficial"]


def test_duplicate_source_cells_cannot_appear_complete():
    rows = scores()
    rows[-1] = copy.deepcopy(rows[0])
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(rows, 18, False)
