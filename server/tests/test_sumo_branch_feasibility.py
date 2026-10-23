import json

import pytest

from research.audits.sumo_branch_feasibility import Signal, audit_signals, schedule


def trace(request_at=80, until=145):
    signal, result = Signal(), []
    for tick in range(until):
        if tick == request_at:
            signal.request(1)
        result.append(dict(lamps=signal.lamps([0, 0, 1, 1])))
        signal.advance()
    return result


def test_executed_lamps_include_full_green_yellow_and_red_intervals():
    rows = trace()
    assert [r["lamps"] for r in rows[:80]] == ["GGrr"]*80
    assert [r["lamps"] for r in rows[80:110]] == ["yyrr"]*30
    assert [r["lamps"] for r in rows[110:120]] == ["rrrr"]*10
    assert rows[120]["lamps"] == "rrGG"
    audit_signals(rows, [0, 0, 1, 1])
    assert all(row["lamps"] == "GGrr" for row in trace(request_at=79))


@pytest.mark.parametrize("mutation", ["conflict", "short_green", "short_yellow", "short_red", "skip_clearance"])
def test_independent_audit_rejects_executed_timing_and_conflicts(mutation):
    rows = trace()
    if mutation == "conflict":
        rows[0]["lamps"] = "GGGG"
    elif mutation == "short_green":
        rows.pop(0)
    elif mutation == "short_yellow":
        rows.pop(80)
    elif mutation == "short_red":
        rows.pop(110)
    else:
        rows = rows[:80]+rows[120:]
    with pytest.raises(ValueError):
        audit_signals(rows, [0, 0, 1, 1])


def test_future_schedules_are_deterministic_disjoint_and_pairable():
    first = schedule(108101, 600, 800)
    second = schedule(108102, 600, 800)
    assert first == schedule(108101, 600, 800)
    assert first != second
    assert not {a[2] for a in first} & {a[2] for a in second}
    assert all(600 <= a[0] < 800 for a in first+second)
    assert json.loads(json.dumps(first)) == first
