import copy

import pytest

from research.evidence.export_sumo_future_evidence import tables


def panel():
    cases = [dict(source=1, family="a", baseline=0, gate=600),
             dict(source=2, family="b", baseline=1, gate=600)]
    rows = []
    for case in cases:
        for role, indices in (("single", (-1,)), ("fit", range(8)), ("check", range(8, 16))):
            for index in indices:
                base = case["baseline"]
                delay = 8. if case["source"] == 1 else 12.
                if role == "check":
                    delay = (5. if index < 12 else 15.) if case["source"] == 1 else 0.
                rows.append(dict(source=case["source"], role=role, index=index, **{
                    str(base): dict(delay=10., throughput=2, endpoint_wait=5.),
                    str(1-base): dict(delay=delay, throughput=2, endpoint_wait=5.)}))
    choices = {"1": dict(baseline=0, single=1, mean8=1), "2": dict(baseline=1, single=1, mean8=1)}
    return cases, rows, choices


def test_decimal_recomputation_keeps_selection_and_check_partitions_separate():
    cases, rows, choices = panel()
    futures, sources, arms = tables(cases, rows, choices)
    assert len(futures) == 34 and len(sources) == 2
    assert sources[0]["positive"] == sources[0]["negative"] == 4
    assert sources[1]["positive"] == 8 and not sources[1]["mean8_changed"]
    assert all(a["mean_delay_saved_vehicle_seconds"] == 0 for a in arms)
    assert arms[1]["changed_gates"] == 1 and arms[1]["harmful_cases"] == 4
    # Very favorable check outcomes cannot retroactively change the fit choice.
    changed = copy.deepcopy(choices)
    changed["2"]["mean8"] = 0
    with pytest.raises(ValueError, match="selection partition"):
        tables(cases, rows, changed)


@pytest.mark.parametrize("mutation", ["duplicate_future", "missing_future", "wrong_role", "duplicate_source"])
def test_export_rejects_changed_panel_membership(mutation):
    cases, rows, choices = panel()
    if mutation == "duplicate_future":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "missing_future":
        rows.pop()
    elif mutation == "wrong_role":
        rows[0]["role"] = "check"
    else:
        cases.append(copy.deepcopy(cases[0]))
    with pytest.raises(ValueError):
        tables(cases, rows, choices)
