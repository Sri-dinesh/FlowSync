import copy
from dataclasses import asdict
import random
from types import SimpleNamespace

import pytest

from research.analysis.sumo_classical_metrics import validate_trace as validate_classical
from research.experiments import sumo_observed_episode as runtime
from research.policies.sumo_classical import Clock, Counts, choose_action
from research.policies.sumo_total_count import choose_total_count, policy_for
from server.tests.test_sumo_classical_panel import AXES, trace_rows, waiting_fixture


def test_total_counts_see_moving_traffic_and_ignore_outgoing_and_halted_components():
    packet = Counts((10, 0, 4, 0), (0, 8, 0, 0), (0, 0, 4, 0))
    clock = Clock(0, "green", 80)
    assert choose_total_count(packet, clock) == 0
    assert choose_action("halted", packet, clock) == choose_action("max_pressure", packet, clock) == 1
    changed = Counts(packet.incoming, (99, 99, 99, 99), (10, 0, 0, 0))
    assert choose_total_count(changed, clock) == 0


@pytest.mark.parametrize("phase", [0, 1])
def test_ties_and_physical_lockouts_hold_current_phase(phase):
    packet = Counts((0, 0, 10, 10), (0,)*4, (0,)*4)
    for clock in (Clock(phase, "green", 79), Clock(phase, "yellow", 29), Clock(phase, "red", 9)):
        assert choose_total_count(packet, clock) == phase
    assert choose_total_count(Counts((1, 2, 2, 1), (0,)*4, (0,)*4), Clock(phase, "green", 80)) == phase
    assert choose_total_count(Counts((0,)*4, (0,)*4, (0,)*4), Clock(phase, "green", 500)) == phase


def test_total_counts_equal_pressure_with_zero_outgoing_on_generated_states():
    rng = random.Random(231010)
    for _ in range(100):
        incoming = tuple(rng.randrange(30) for _ in range(4))
        packet = Counts(incoming, (0,)*4, tuple(rng.randrange(v+1) for v in incoming))
        for phase in (0, 1):
            clock = Clock(phase, "green", 80)
            assert choose_total_count(packet, clock) == choose_action("max_pressure", packet, clock)
    with pytest.raises(ValueError, match="Unknown"):
        policy_for("unknown")


def test_new_runtime_supplies_total_policy_at_every_decision(monkeypatch):
    calls = []
    def step(conn, signal, axes, tick, arrivals, backlog, first_action):
        if tick % 20 == 0:
            calls.append((tick, first_action))
            assert first_action is not None
            signal.request(first_action)
        row = dict(tick=tick, fsm=asdict(signal), vehicles=[["moving", "e_in", 10., 3.]])
        signal.advance()
        return row, backlog
    monkeypatch.setattr(runtime, "advance", step)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda: 0), vehicle=SimpleNamespace(getIDList=lambda: []))
    trace = list(runtime.episode(conn, AXES, dict(schedule=[], steps=160), choose_total_count, lambda: None))
    assert len(calls) == 8 and dict(calls)[0] == 0 and dict(calls)[80] == 1
    assert trace[80]["fsm"]["stage"] == "yellow"
    assert trace[120]["fsm"]["stage"] == "green" and trace[120]["fsm"]["phase"] == 1


@pytest.mark.parametrize("proposal", [True, 2, -1, 1.])
def test_invalid_policy_results_cannot_reach_physical_step(proposal):
    with pytest.raises(ValueError, match="valid integer"):
        runtime.proposal_for(lambda packet, clock: proposal, Counts((0,)*4, (0,)*4, (0,)*4), runtime.Signal())


def test_request_denominator_and_unfinished_backlog_wait_match_frozen_metrics():
    schedule, trace = waiting_fixture()
    actual = runtime.validate_trace(trace, schedule, choose_total_count, AXES, 41)
    assert actual == validate_classical(trace, schedule, "halted", AXES, 41)
    assert actual["mean_stopped_wait_per_requested_vehicle_s"] == 1.5
    assert actual["total_stopped_wait_vehicle_seconds"] == 4.5 and actual["p95_accumulated_wait_s"] == 3.65


@pytest.mark.parametrize("controller", ["halted", "fixed", "max_pressure"])
def test_callback_checker_matches_frozen_checker_for_all_reference_policies(controller):
    schedule = [[0, "n", "a"], [1, "e", "b"], [2, "w", "c"]]
    trace = trace_rows(schedule, 800, controller)
    assert runtime.validate_trace(trace, schedule, policy_for(controller), AXES, 800) == validate_classical(
        trace, schedule, controller, AXES, 800)


@pytest.mark.parametrize("mutation", ["packet", "policy", "pending", "wait", "lamps", "missing", "nonfinite"])
def test_new_trace_checker_rejects_inconsistent_raw_measurements(mutation):
    schedule, original = waiting_fixture()
    trace = copy.deepcopy(original)
    if mutation == "packet":
        trace[0]["decision"]["packet"]["incoming"][0] = 1
    elif mutation == "policy":
        trace[20]["decision"]["proposal"] = 1
    elif mutation == "pending":
        trace[1]["pending"] = []
    elif mutation == "wait":
        trace[1]["wait_vehicle_seconds"] = 0.
    elif mutation == "lamps":
        trace[1]["lamps"] = "GGGG"
    elif mutation == "missing":
        trace.pop()
    else:
        trace[-1]["vehicles"][0][3] = float("nan")
    with pytest.raises(ValueError):
        runtime.validate_trace(trace, schedule, choose_total_count, AXES, 41)
