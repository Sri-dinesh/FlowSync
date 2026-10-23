import copy

import pytest

from research.audits.verify_sumo_future_panel import same_numbers
from research.pilots.run_sumo_future_panel import arrivals, choose, future_seed, gain, outcome, summarize


def measurements(delay=10., throughput=2, wait=4.):
    return dict(delay=delay, throughput=throughput, endpoint_wait=wait)


def test_frozen_selector_requires_delay_throughput_and_wait_jointly():
    row = {"0": measurements(), "1": measurements(delay=8.)}
    assert choose([row], 0) == 1
    for candidate in (measurements(delay=9.), measurements(delay=8., throughput=1), measurements(delay=8., wait=6.)):
        assert choose([{"0": measurements(), "1": candidate}], 0) == 0
    assert gain(measurements(delay=10.0000000000001), measurements(delay=9.)) == [1., 0, 0.]


def test_future_mode_roles_and_source_keys_are_disjoint_and_reproducible():
    keys = {future_seed(source, role, i, smoke) for source in (109001, 109002)
            for role in ("single", "fit", "check") for i in range(16) for smoke in (False, True)}
    assert len(keys) == 2*3*16*2
    first = arrivals(future_seed(109001, "fit", 0, False), 600, 1000, .3, .1)
    assert first == arrivals(future_seed(109001, "fit", 0, False), 600, 1000, .3, .1)
    assert all(600 <= r[0] < 1000 for r in first)


def test_endpoint_wait_includes_source_history_but_delay_is_branch_increment():
    prefix = [dict(vehicles=[["v", "n_in", 1., 0.]], pending=[], wait_vehicle_seconds=.1, arrived=[]) for _ in range(20)]
    trace = [dict(vehicles=[["v", "n_in", 1., 0.]], pending=[[0, "s", "pending"]], wait_vehicle_seconds=.2, arrived=[])
             for _ in range(10)]
    result = outcome(prefix, trace)
    assert result["delay"] == 2. and result["endpoint_wait"] == 3. and result["throughput"] == 0
    trace[0]["pending"].append([0, "n", "v"])
    with pytest.raises(ValueError, match="both active and pending"):
        outcome(prefix, trace)


def test_source_weighted_summary_keeps_harmful_future_and_unchanged_choices():
    cases = [dict(source=109901, family="balanced", baseline=0)]
    rows = [dict(source=109901, role="check", index=i, **{"0": measurements(), "1": measurements(delay=d)})
            for i, d in ((8, 5.), (9, 15.))]
    choices = {"109901": dict(baseline=0, single=1, mean8=0)}
    report = summarize(cases, rows, choices, True)
    assert report["sign_counts"]["mixed_gates"] == 1
    assert report["arms"]["single"]["mean_gain"][0] == 0
    assert report["arms"]["single"]["harmful"] == 1
    assert report["arms"]["mean8"]["changed_gates"] == 0
    duplicate = copy.deepcopy(rows)
    duplicate[1]["index"] = 8
    with pytest.raises(ValueError, match="Incomplete/duplicate"):
        summarize(cases, duplicate, choices, True)


def test_verification_tolerates_only_floating_roundoff_and_preserves_counts():
    assert same_numbers({"x": [110.5]}, {"x": [110.49999999999996]})
    assert not same_numbers({"x": [110.5]}, {"x": [110.51]})
    assert not same_numbers(2, 3)
    assert not same_numbers(float("nan"), float("nan"))
    assert not same_numbers({"x": 0}, {})
