"""Count delivery and saved-data verification; fixtures do not simulate traffic."""
from copy import deepcopy
from dataclasses import asdict
import random
from types import SimpleNamespace

import pytest

from research.audits.sumo_branch_feasibility import Signal
from research.experiments import sumo_sensing as runtime
from research.observation.sumo_sensing import CountSensor, Delivery, EMPTY, Fault, PRESETS
from research.policies.sumo_classical import Clock, choose_action, observe

AXES = [0,1,0,1]


def trace_fixture(plan, controller="max_pressure", fault=PRESETS[0]):
    """Contract-only rows with explicit hand-controlled inventory, no kinematics."""
    sensor,signal,previous,active,rows = CountSensor(fault,plan["seed"]),Signal(),[],[],[]
    special = plan.get("special",False)
    for tick in range(plan["steps"]):
        delivery = sensor.step(previous,tick)
        decision = None
        if tick % 20 == 0:
            proposal = choose_action(controller,None if controller == "fixed" else delivery.counts,
                                     Clock(signal.phase,signal.stage,signal.age))
            decision = dict(packet=delivery.counts.to_dict(),before_fsm=asdict(signal),proposal=proposal)
            signal.request(proposal)
        requested = [r for r in plan["schedule"] if r[0] == tick]
        active += [[r[2],r[1]+"_in",1.,0.] for r in requested]
        arrived = ["n"] if special and tick == 90 else []
        active = [v for v in active if v[0] not in arrived]
        row = dict(tick=tick,fsm=asdict(signal),lamps=signal.lamps(AXES),vehicles=deepcopy(active),
            pending=[],requested=requested,inserted=[r[2] for r in requested],arrived=arrived,
            wait_vehicle_seconds=round(len(active)/10,6),sensing=delivery.to_dict())
        if decision is not None:
            row["decision"] = decision
        rows.append(row)
        previous = row["vehicles"]
        signal.advance()
    return rows


def special_plan():
    return dict(seed=7,family="fixture",steps=180,special=True,schedule=[[0,"n","n"],[80,"e","e"]])


def test_exact_capture_clock_missing_startup_and_first_delayed_delivery():
    clean, delayed = CountSensor(PRESETS[0],7),CountSensor(PRESETS[1],7)
    original = [["n","n_in",5.,0.]]
    for tick in range(42):
        vehicles = original if tick == 0 else [["e","e_in",5.,0.]]
        a,b = clean.step(vehicles,tick),delayed.step(vehicles,tick)
        assert a.source_tick == tick and a.to_dict()["age_ticks"] == 0
        if tick < 20:
            assert b.source_tick is None and b.counts == EMPTY
        else:
            assert b.source_tick == tick-20 and b.to_dict()["age_ticks"] == 20
            assert b.counts == observe(original if tick == 20 else vehicles)
    empty = CountSensor(PRESETS[1],7)
    for tick in range(21):
        packet = empty.step([],tick)
    assert packet.counts == EMPTY and packet.source_tick == 0  # Present empty, not missing.


def test_coherent_vehicle_misses_are_shared_across_latency_arms_and_rng_independent():
    vehicles = [[f"q{i}","n_in",5.,0.] for i in range(40)]+[[f"o{i}","s_out",5.,3.] for i in range(40)]
    initial = deepcopy(vehicles)
    state = random.getstate()
    miss,both = CountSensor(PRESETS[2],42),CountSensor(PRESETS[3],42)
    first = miss.step(vehicles,0)
    assert 0 < first.counts.incoming[0] < 40 and first.counts.halted == first.counts.incoming
    assert 0 < first.counts.outgoing[1] < 40
    for tick in range(21):
        packet = both.step(vehicles,tick)
    assert packet.counts == first.counts and packet.source_tick == 0
    assert random.getstate() == state and vehicles == initial
    assert CountSensor(Fault("all_missed",0,1.),42).step(vehicles,0).counts == EMPTY


@pytest.mark.parametrize("bad", [True, -1, 2, .0])
def test_rejected_clock_does_not_advance_receiver(bad):
    sensor = CountSensor(PRESETS[0],1)
    with pytest.raises(ValueError):
        sensor.step([],bad)
    assert sensor.step([],0).source_tick == 0
    with pytest.raises(ValueError):
        sensor.step([],0)
    assert sensor.step([],1).source_tick == 1


def test_bad_source_cannot_disappear_through_total_misses_or_mutate_receiver():
    sensor = CountSensor(Fault("all",0,1.),1)
    with pytest.raises(ValueError):
        sensor.step([["v","n_in",0.,float("nan")]],0)
    assert sensor.step([],0).counts == EMPTY
    with pytest.raises(ValueError):
        Delivery(1,2,EMPTY)
    with pytest.raises(ValueError):
        Delivery(1,None,observe([["v","n_in",0.,0.]]))


def test_faulted_policy_and_accounting_use_delivered_counts_when_clean_disagrees():
    plan = special_plan()
    clean,delayed = trace_fixture(plan),trace_fixture(plan,fault=PRESETS[1])
    assert clean[100]["decision"]["proposal"] == 1 and delayed[100]["decision"]["proposal"] == 0
    original = deepcopy(delayed)
    metrics = runtime.validate_trace(delayed,plan,"max_pressure",PRESETS[1],AXES)
    assert delayed == original
    assert metrics["sensing"]["mean_age_s"] == 2. and metrics["sensing"]["missing_decisions"] == 1
    assert metrics["sensing"]["source_corruption_count_feature_mae"] == 0.
    assert metrics["sensing"]["contemporary_count_feature_mae"] > 0.


@pytest.mark.parametrize("mutation", ["source","counts","proposal","clock","lamps","wait","fifo","missing","off_cadence","last_nan"])
def test_replay_rejects_changed_evidence_instead_of_cleaning_the_action(mutation):
    plan = special_plan()
    trace = trace_fixture(plan,fault=PRESETS[1])
    if mutation == "source": trace[100]["sensing"]["source_tick"] = 100
    elif mutation == "counts": trace[100]["decision"]["packet"]["incoming"][0] = 50
    elif mutation == "proposal": trace[100]["decision"]["proposal"] = 1
    elif mutation == "clock": trace[100]["decision"]["before_fsm"]["age"] = 1
    elif mutation == "lamps": trace[100]["lamps"] = "GGGG"
    elif mutation == "wait": trace[100]["wait_vehicle_seconds"] = 0.
    elif mutation == "fifo": trace[100]["pending"] = [[0,"n","n"]]
    elif mutation == "missing": trace.pop()
    elif mutation == "off_cadence": trace[101]["decision"] = trace[100]["decision"]
    else: trace[-1]["vehicles"][0][3] = float("nan")
    with pytest.raises(ValueError):
        runtime.validate_trace(trace,plan,"max_pressure",PRESETS[1],AXES)


def test_live_runtime_supplies_every_proposal_and_fixed_never_receives_counts(monkeypatch):
    supplied,seen = [],[]
    original = runtime.choose_action
    def policy(controller, packet, clock):
        seen.append(packet)
        return original(controller,packet,clock)
    def step(conn,signal,axes,tick,requests,backlog,first_action):
        if tick % 20 == 0:
            assert type(first_action) is int
            supplied.append(tick)
            signal.request(first_action)
        row = dict(tick=tick,vehicles=[],fsm=asdict(signal))
        signal.advance()
        return row,backlog
    monkeypatch.setattr(runtime,"choose_action",policy)
    monkeypatch.setattr(runtime,"advance",step)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda:0),vehicle=SimpleNamespace(getIDList=lambda:[]))
    list(runtime.episode(conn,AXES,dict(seed=7,steps=400,schedule=[]),"fixed",PRESETS[3],lambda:None))
    assert supplied == list(range(0,400,20)) and all(v is None for v in seen)
