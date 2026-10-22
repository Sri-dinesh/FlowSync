import copy

import pytest

from research.audit_averaged_model_choices import diagnose, flags


def test_constraint_boundaries_match_original_rule():
    assert flags([1., 0., -1.]) == dict(delay=False, throughput=True, endpoint_wait=True)
    assert flags([1.001, -.001, -1.001]) == dict(delay=True, throughput=False, endpoint_wait=False)
    with pytest.raises(ValueError, match="Invalid gain"):
        flags([float("nan"), 0., 0.])
    with pytest.raises(ValueError, match="Invalid gain"):
        flags([1., 0.])


def sample():
    event = dict(step=200, policy_proposal=0, branch_diagnostic=[dict(branches=[
        dict(proposal=0, outcome=dict(incremental_delay_vehicle_seconds=100., vehicles_passed=5, upstream_max_wait_s=10.)),
        dict(proposal=1, outcome=dict(incremental_delay_vehicle_seconds=97., vehicles_passed=5, upstream_max_wait_s=10.))])])
    row = dict(training_seed=101, scenario="fixture", seed=96301, data_role="fit", selected_steps=[200], events=[event])
    choice = dict(step=200, parent=0, single=0, mean8=0,
                  predictions={a: {1: [2., -.01, 0.]} for a in ("single", "mean8")})
    return row, choice


def test_audit_identifies_throughput_rejection_without_changing_choice(monkeypatch):
    import research.audit_averaged_model_choices as audit
    row, choice = sample()
    before = copy.deepcopy((row, choice))
    monkeypatch.setattr(audit, "predict_source", lambda *args: [choice])
    counters, details = diagnose([row], {})
    for arm in ("single", "mean8"):
        c = counters[arm]
        assert c["gates"] == 1 and c["changed_gates"] == 0
        assert c["gates_with_actual_mean_qualified_alternative"] == 1
        assert c["false_negative"] == 1 and c["true_positive"] == 0
        assert c["predicted_delay_pass_but_throughput_reject"] == 1
        assert c["missed_qualified_rejected_by_throughput"] == 1
        assert c["missed_qualified_rejected_by_delay"] == 0
        assert counters[f"101/{arm}"] == c
    assert len(details) == 2 and all(not r["predicted_qualified"] for r in details)
    assert (row, choice) == before


def test_opportunity_is_mean_label_not_any_lucky_future(monkeypatch):
    import research.audit_averaged_model_choices as audit
    row, choice = sample()
    other = copy.deepcopy(row["events"][0]["branch_diagnostic"][0])
    other["branches"][1]["outcome"]["incremental_delay_vehicle_seconds"] = 110.
    row["events"][0]["branch_diagnostic"].append(other)
    monkeypatch.setattr(audit, "predict_source", lambda *args: [choice])
    counters, _ = diagnose([row], {})
    assert counters["mean8"]["gates_with_actual_mean_qualified_alternative"] == 0
    assert counters["mean8"]["actual_mean_qualified"] == 0
    assert counters["mean8"]["true_negative"] == 1


def test_predicted_positive_is_not_automatically_a_true_benefit(monkeypatch):
    import research.audit_averaged_model_choices as audit
    row, choice = sample()
    choice["mean8"] = 1
    choice["predictions"]["mean8"][1] = [2., 0., 0.]
    row["events"][0]["branch_diagnostic"][0]["branches"][1]["outcome"]["vehicles_passed"] = 4
    monkeypatch.setattr(audit, "predict_source", lambda *args: [choice])
    counters, _ = diagnose([row], {})
    assert counters["mean8"]["changed_gates"] == 1
    assert counters["mean8"]["false_positive"] == 1
    assert counters["mean8"]["true_positive"] == 0
