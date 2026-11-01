"""Finite causal pressure filtering and observed-runtime contracts, without SUMO."""
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from research.audits.sumo_branch_feasibility import Signal
from research.experiments import sumo_history as runtime
from research.observation.sumo_sensing import CountSensor, Counts, Delivery, PRESETS
from research.policies.sumo_classical import Clock, choose_action
from research.policies.sumo_history import Method, PressureHistory, propose

AXES = [0,1,0,1]


def frame(tick, north, east, south_out=0):
    return Delivery(tick,tick,Counts((north,0,east,0),(0,south_out,0,0),(0,0,0,0)))


def test_mean_uses_exact_window_endpoints_and_clips_each_frame_before_averaging():
    memory = PressureHistory(1)
    memory.push(frame(0,0,0,2)); memory.push(frame(1,2,0))
    state = memory.state('mean')
    assert state['score_numerators']==[2,0] and state['score_divisor']==2
    # Averaging counts before clipping would instead give pressure zero.
    memory.push(frame(2,4,0))
    assert memory.state('mean')['score_numerators']==[6,0]
    assert memory.state('mean')['oldest_control_tick']==1


def test_two_second_history_is_21_frames_and_lag_is_exactly_20_ticks():
    memory = PressureHistory(20)
    for tick in range(20): memory.push(frame(tick,tick,0))
    assert not memory.state('lag')['lag_ready'] and memory.state('lag')['score_numerators']==[0,0]
    memory.push(frame(20,20,0))
    assert memory.state('mean')['buffered_frames']==21 and memory.state('mean')['score_numerators']==[210,0]
    assert memory.state('lag')['score_numerators']==[0,0] and memory.state('lag')['lag_ready']
    memory.push(frame(21,21,0))
    assert memory.state('lag')['score_numerators']==[1,0]


@pytest.mark.parametrize('phase',[0,1])
def test_zero_span_and_current_estimator_preserve_original_pressure(phase):
    memory = PressureHistory(0)
    for tick in range(30):
        delivered = frame(tick,tick%4,(tick+2)%5)
        memory.push(delivered)
        for estimator in ('current','lag','mean'):
            result = propose(Method('test','clean',estimator),memory,Clock(phase,'green',80))
            assert result['proposal']==choose_action('max_pressure',delivered.counts,Clock(phase,'green',80))


@pytest.mark.parametrize('stage,age',[('green',79),('yellow',90),('red',90)])
def test_physical_guards_and_ties_keep_current_phase(stage,age):
    memory=PressureHistory(1)
    memory.push(frame(0,0,10)); memory.push(frame(1,0,10))
    assert propose(Method('mean','clean','mean'),memory,Clock(0,stage,age))['proposal']==0
    memory.push(frame(2,20,0))
    assert propose(Method('mean','clean','mean'),memory,Clock(1,'green',80))['proposal']==0
    tied=PressureHistory(0); tied.push(frame(0,2,2))
    assert propose(Method('mean','clean','mean'),tied,Clock(1,'green',80))['proposal']==1


def test_invalid_push_does_not_change_history_and_missing_frames_are_explicit():
    memory=PressureHistory(20)
    empty=Counts((0,)*4,(0,)*4,(0,)*4)
    memory.push(Delivery(0,None,empty))
    before=memory.state('mean')
    for delivered in (Delivery(0,None,empty),Delivery(2,2,empty),None):
        with pytest.raises(ValueError): memory.push(delivered)
        assert memory.state('mean')==before
    assert before['missing_frames']==1 and before['oldest_source_tick'] is None
    assert PressureHistory(20).next_tick==0


@pytest.mark.parametrize('span',[-1,True,1.5])
def test_invalid_window_is_rejected(span):
    with pytest.raises(ValueError): PressureHistory(span)


def fixture(plan,method,phase,window=20):
    sensor=CountSensor(next(f for f in PRESETS if f.name==method.fault),plan['seed'])
    memory,signal,previous,active,rows=PressureHistory(window),Signal(phase=phase,pending=phase),[],[],[]
    for tick in range(plan['steps']):
        delivered=sensor.step(previous,tick); memory.push(delivered)
        decision=None
        if tick%20==0:
            selected=propose(method,memory,Clock(signal.phase,signal.stage,signal.age))
            decision=dict(packet=delivered.counts.to_dict(),before_fsm=asdict(signal),proposal=selected['proposal'],policy=selected)
            signal.request(selected['proposal'])
        requested=[r for r in plan['schedule'] if r[0]==tick]
        active += [[r[2],r[1]+'_in',1.,0.] for r in requested]
        row=dict(tick=tick,fsm=asdict(signal),lamps=signal.lamps(AXES),vehicles=deepcopy(active),
                 requested=requested,pending=[],inserted=[r[2] for r in requested],arrived=[],
                 wait_vehicle_seconds=round(len(active)/10,6),sensing=delivered.to_dict())
        if decision is not None: row['decision']=decision
        rows.append(row); previous=row['vehicles']; signal.advance()
    return rows


@pytest.mark.parametrize('phase',[0,1])
@pytest.mark.parametrize('estimator,fault',[('current','clean'),('current','delay2s_miss30'),('lag','clean'),('mean','clean'),('mean','delay2s_miss30')])
def test_each_method_reconstructs_only_delivered_history(phase,estimator,fault):
    plan=dict(seed=9,steps=180,schedule=[[0,'n','n'],[1,'e','e'],[2,'w','w']])
    method=Method('test',fault,estimator)
    rows=fixture(plan,method,phase)
    assert runtime.validate_trace(rows,plan,method,AXES,phase,20)['requested_vehicles']==3


@pytest.mark.parametrize('change',['packet','mean','divisor','source_age','proposal','canonical_phase','lamps','wait','length'])
def test_corruption_is_rejected_without_clean_replacement(change):
    plan=dict(seed=9,steps=180,schedule=[[0,'n','n'],[1,'e','e']])
    method=Method('test','delay2s_miss30','mean'); rows=fixture(plan,method,1)
    if change=='packet': rows[80]['decision']['packet']['incoming'][0]+=1
    elif change=='mean': rows[80]['decision']['policy']['history']['score_numerators'][0]+=1
    elif change=='divisor': rows[80]['decision']['policy']['history']['score_divisor']+=1
    elif change=='source_age': rows[80]['decision']['policy']['history']['oldest_source_tick']+=1
    elif change=='proposal': rows[80]['decision']['proposal']=1-rows[80]['decision']['proposal']
    elif change=='canonical_phase': rows[80]['fsm']['phase']=0
    elif change=='lamps': rows[80]['lamps']='GrGr'
    elif change=='wait': rows[-1]['wait_vehicle_seconds']+=1
    else: rows.pop()
    with pytest.raises(ValueError): runtime.validate_trace(rows,plan,method,AXES,1,20)


@pytest.mark.parametrize('phase',[0,1])
def test_live_canonical_adapter_matches_direct_physical_fixture(monkeypatch,phase):
    plan=dict(seed=9,steps=180,schedule=[[0,'n','n'],[1,'e','e']])
    active=[]
    def advance(conn,signal,axes,tick,requested,backlog,first_action):
        if tick%20==0: signal.request(first_action)
        active.extend([[r[2],r[1]+'_in',1.,0.] for r in requested])
        row=dict(tick=tick,fsm=asdict(signal),lamps=signal.lamps(axes),vehicles=deepcopy(active),
                 requested=requested,pending=[],inserted=[r[2] for r in requested],arrived=[],
                 wait_vehicle_seconds=round(len(active)/10,6))
        signal.advance(); return row,backlog
    monkeypatch.setattr(runtime,'advance',advance)
    conn=SimpleNamespace(simulation=SimpleNamespace(getTime=lambda:0),vehicle=SimpleNamespace(getIDList=lambda:[]))
    method=Method('test','clean','mean')
    assert list(runtime.episode(conn,AXES,plan,method,phase,20,lambda:None))==fixture(plan,method,phase)
