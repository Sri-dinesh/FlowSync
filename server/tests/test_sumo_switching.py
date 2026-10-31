"""Pure control and canonical phase/packet contracts; no native traffic here."""
from copy import deepcopy
from dataclasses import asdict
import random
from types import SimpleNamespace

import pytest

from research.audits.sumo_branch_feasibility import Signal
from research.experiments import sumo_switching as runtime
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import Clock, Counts, choose_action
from research.policies.sumo_switching import Method, propose

AXES = [0, 1, 0, 1]


def test_zero_margin_matches_frozen_pressure_for_counts_clocks_and_ties():
    rng = random.Random(19)
    method = runtime.method_for("pressure_clean")
    for _ in range(100):
        incoming = tuple(rng.randrange(10) for _ in range(4))
        packet = Counts(incoming, tuple(rng.randrange(5) for _ in range(4)), tuple(rng.randrange(q+1) for q in incoming))
        for phase in (0, 1):
            for stage, age in (("green", 0), ("green", 79), ("green", 80), ("green", 160), ("yellow", 0), ("red", 0)):
                clock = Clock(phase, stage, age)
                assert propose(method, packet, clock)["proposal"] == choose_action("max_pressure", packet, clock)


def test_margin_holds_one_count_advantage_but_releases_idle_phase_and_larger_advantage():
    method = runtime.method_for("pressure_margin1")
    clock = Clock(0, "green", 80)
    def packet(a, b): return Counts((a, 0, b, 0), (0, 0, 0, 0), (0, 0, 0, 0))
    held = propose(method, packet(1, 2), clock)
    assert held["raw_proposal"] == 1 and held["proposal"] == 0 and held["margin_held"]
    assert propose(method, packet(1, 3), clock)["proposal"] == 1
    assert propose(method, packet(0, 1), clock)["proposal"] == 1
    assert propose(method, packet(0, 0), clock)["proposal"] == 0
    assert propose(method, packet(1, 3), Clock(0, "green", 79))["proposal"] == 0


def test_fixed_never_reads_the_packet():
    class Forbidden:
        def __getattribute__(self, name): raise AssertionError("Fixed read a count packet")
    result = propose(runtime.method_for("fixed_clean"), Forbidden(), Clock(0, "green", 300))
    assert result["proposal"] == 1 and result["phase_pressures"] is None


@pytest.mark.parametrize("margin", [True, -1, .5])
def test_invalid_margin_is_rejected(margin):
    with pytest.raises(ValueError): Method("bad", "max_pressure", "clean", margin)


def fixture(plan, method, phase):
    fault = next(f for f in PRESETS if f.name == method.fault)
    sensor, signal, previous, active, frames = CountSensor(fault, plan["seed"]), Signal(phase=phase, pending=phase), [], [], []
    for tick in range(plan["steps"]):
        delivery = sensor.step(previous, tick)
        decision = None
        if tick % 20 == 0:
            selected = propose(method, None if method.controller == "fixed" else delivery.counts,
                               Clock(signal.phase, signal.stage, signal.age))
            decision = dict(packet=delivery.counts.to_dict(), before_fsm=asdict(signal), proposal=selected["proposal"], policy=selected)
            signal.request(selected["proposal"])
        requested = [r for r in plan["schedule"] if r[0] == tick]
        active += [[r[2], r[1]+"_in", 1., 0.] for r in requested]
        row = dict(tick=tick, fsm=asdict(signal), lamps=signal.lamps(AXES), vehicles=deepcopy(active),
                   requested=requested, pending=[], inserted=[r[2] for r in requested], arrived=[],
                   wait_vehicle_seconds=round(len(active)/10, 6), sensing=delivery.to_dict())
        if decision is not None: row["decision"] = decision
        frames.append(row)
        previous = row["vehicles"]
        signal.advance()
    return frames


@pytest.mark.parametrize("phase", [0, 1])
@pytest.mark.parametrize("name", ["pressure_clean", "pressure_mixed", "pressure_margin1", "fixed_clean"])
def test_delivered_packet_and_canonical_phase_replay(phase, name):
    plan = dict(seed=1360901, steps=800, schedule=[[0, "n", "a"], [1, "n", "b"], [500, "e", "later"]])
    method = runtime.method_for(name)
    frames = fixture(plan, method, phase)
    before = deepcopy(frames)
    measured = runtime.validate_trace(frames, plan, method, AXES, phase)
    assert measured["signal_samples"] == 800 and measured["requested_vehicles"] == 3
    assert frames == before and frames[0]["fsm"]["phase"] == phase
    assert frames[0]["lamps"] == ("GrGr" if phase == 0 else "rGrG")
    early = runtime.validate_trace(frames[:400], runtime.trim(plan, 400), method, AXES, phase)
    assert early["requested_vehicles"] == 2 and early["signal_samples"] == 400


@pytest.mark.parametrize("mutation", ["packet", "policy", "phase", "lamps", "wait", "clock", "length"])
def test_replay_rejects_corruption_without_clean_input_substitution(mutation):
    plan = dict(seed=1360901, steps=180, schedule=[[0, "n", "a"], [1, "n", "b"]])
    method = runtime.method_for("pressure_mixed")
    frames = fixture(plan, method, 1)
    if mutation == "packet": frames[20]["decision"]["packet"]["incoming"][0] += 1
    elif mutation == "policy": frames[80]["decision"]["policy"]["margin_held"] = True
    elif mutation == "phase": frames[0]["fsm"]["phase"] = 0
    elif mutation == "lamps": frames[0]["lamps"] = "GrGr"
    elif mutation == "wait": frames[-1]["wait_vehicle_seconds"] += 1
    elif mutation == "clock": frames[40]["sensing"]["source_tick"] = 40
    else: frames.pop()
    with pytest.raises(ValueError): runtime.validate_trace(frames, plan, method, AXES, 1)


@pytest.mark.parametrize("phase", [0, 1])
def test_live_offset_adapter_matches_canonical_direct_signal(monkeypatch, phase):
    plan = dict(seed=1360901, steps=180, schedule=[[0, "n", "a"], [1, "n", "b"]])
    active = []
    def advance(conn, signal, axes, tick, requested, backlog, first_action):
        if tick % 20 == 0:
            assert first_action is not None
            signal.request(first_action)
        active.extend([[r[2], r[1]+"_in", 1., 0.] for r in requested])
        row = dict(tick=tick, fsm=asdict(signal), lamps=signal.lamps(axes), vehicles=deepcopy(active),
                   requested=requested, inserted=[r[2] for r in requested], pending=[], arrived=[],
                   wait_vehicle_seconds=round(len(active)/10, 6))
        signal.advance()
        return row, backlog
    monkeypatch.setattr(runtime, "advance", advance)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda: 0), vehicle=SimpleNamespace(getIDList=lambda: []))
    method = runtime.method_for("pressure_clean")
    assert list(runtime.episode(conn, AXES, plan, method, phase, lambda: None)) == fixture(plan, method, phase)


def test_frozen_grid_keeps_traffic_roles_and_supplementary_mechanics_separate():
    full, smoke = runtime.jobs(), runtime.jobs(True)
    assert len(full) == 36 and sum(r["steps"] for r in full) == 129600
    assert len(smoke) == 28 and sum(r["steps"] for r in smoke) == 20000
    assert {j["seed"] for j in full}.isdisjoint({j["seed"] for j in smoke})
    assert {j["method"] for j in full} == {"pressure_clean", "pressure_mixed", "pressure_margin1"}
