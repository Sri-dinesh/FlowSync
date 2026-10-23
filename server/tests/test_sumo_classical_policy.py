from dataclasses import asdict
import random
from types import SimpleNamespace

import numpy as np
import pytest

from research.experiments import sumo_classical_runtime as runtime
from research.policies.sumo_classical import Clock, Counts, choose_action, observe, phase_pressures
from server.app.controllers.base import ControllerContext
from server.app.controllers.max_pressure import MaxPressureController


EMPTY = Counts((0,)*4, (0,)*4, (0,)*4)


@pytest.mark.parametrize("values", [(-1, 0, 0, 0), (True, 0, 0, 0), (1., 0, 0, 0), (0, 0, 0)])
def test_delivered_counts_reject_invalid_schema(values):
    with pytest.raises(ValueError):
        Counts(values, (0,)*4, (0,)*4)
    with pytest.raises(ValueError, match="exceeds"):
        Counts((0,)*4, (0,)*4, (1, 0, 0, 0))


def test_observation_uses_delivered_edges_and_speed_without_id_semantics():
    vehicles = [["future_seed_label", "n_in", 10., 3.], ["two", "e_in", 20., .099999],
                ["three", "s_out", 1., 5.], ["four", ":c_0_0", 2., 0.]]
    packet = observe(vehicles)
    assert packet == Counts((1, 0, 1, 0), (0, 1, 0, 0), (0, 0, 1, 0))
    vehicles[0][0] = "arbitrary"
    assert observe(vehicles) == packet == Counts.from_dict(packet.to_dict())
    for bad in (["five", "unknown_edge", 0., 1.], ["five", "n_in", 0., float("nan")], vehicles[0]):
        with pytest.raises(ValueError):
            observe(vehicles+[bad])


@pytest.mark.parametrize("phase", [0, 1])
def test_minimum_green_clearance_ties_and_fixed_actual_green(phase):
    packet = Counts((10, 10, 20, 20), (0,)*4, (10, 10, 20, 20))
    for controller in ("fixed", "halted", "max_pressure"):
        for clock in (Clock(phase, "green", 79), Clock(phase, "yellow", 29), Clock(phase, "red", 9)):
            assert choose_action(controller, packet, clock) == phase
        if controller != "fixed":
            assert choose_action(controller, EMPTY, Clock(phase, "green", 500)) == phase
    assert choose_action("fixed", None, Clock(phase, "green", 299)) == phase
    assert choose_action("fixed", None, Clock(phase, "green", 300)) == 1-phase


def test_pressure_includes_moving_demand_and_pairs_destination_outgoing():
    packet = Counts((10, 0, 4, 0), (20, 1, 0, 0), (0, 0, 4, 0))
    assert phase_pressures(packet) == (9, 4)  # N subtracts S-out, not N-out.
    assert choose_action("max_pressure", packet, Clock(0, "green", 80)) == 0
    assert choose_action("halted", packet, Clock(0, "green", 80)) == 1


def test_pressure_matches_existing_controller_on_independent_random_packets():
    rng = random.Random(260103)
    controller = MaxPressureController(max_cap_in=1., max_cap_out=1.)
    directions = ("north", "south", "east", "west")
    for _ in range(100):
        incoming = tuple(rng.randrange(25) for _ in directions)
        outgoing = tuple(rng.randrange(25) for _ in directions)
        packet = Counts(incoming, outgoing, tuple(rng.randrange(v+1) for v in incoming))
        for phase in (0, 1):
            ctx = ControllerContext(timestep=80, current_phase=phase, can_switch_phase=True,
                movement_queues={d+"_straight": v for d, v in zip(directions, incoming)},
                outgoing_counts=dict(zip(directions, outgoing)))
            assert choose_action("max_pressure", packet, Clock(phase, "green", 80)) == controller.act(np.zeros(28), ctx)


def test_plans_are_paired_bounded_and_separate_from_closed_panel():
    full, smoke = runtime.plans(), runtime.plans(True)
    assert len(full) == 15 and len(smoke) == 1
    assert {p["seed"] for p in full}.isdisjoint({109001, 109002, 109101, 109102, 109201, 109202, smoke[0]["seed"]})
    assert runtime.configuration()["cap_seconds"] == 900
    assert runtime.configuration(True)["repeats"] == 2
    for plan in full+smoke:
        assert plan["schedule"] and all(0 <= a[0] < plan["steps"] for a in plan["schedule"])
    assert full == runtime.plans()


def test_runtime_supplies_fixed_proposals_at_every_decision(monkeypatch):
    supplied = []
    def step(conn, signal, axes, tick, arrivals, backlog, first_action):
        if tick % 20 == 0:
            supplied.append((tick, first_action))
            assert first_action is not None
            signal.request(first_action)
        row = dict(tick=tick, vehicles=[["waiting", "e_in", 10., 0.]], fsm=asdict(signal))
        signal.advance()
        return row, backlog
    monkeypatch.setattr(runtime, "advance", step)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda: 0), vehicle=SimpleNamespace(getIDList=lambda: []))
    trace = list(runtime.episode(conn, [0, 1, 0, 1], dict(steps=400, schedule=[]), "fixed", lambda: None))
    assert len(supplied) == 20 and supplied[0] == (0, 0)
    assert all(p == 0 for tick, p in supplied if tick < 300)
    assert dict(supplied)[300] == 1 and trace[300]["fsm"]["stage"] == "yellow"
    assert trace[340]["fsm"]["phase"] == 1 and trace[340]["fsm"]["age"] == 0
