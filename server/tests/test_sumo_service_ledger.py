"""Mechanics of an isolated pressure/fair-scheduling candidate, not traffic gains."""
from copy import deepcopy
from dataclasses import asdict, replace
from fractions import Fraction
import gzip
import hashlib
import json
import random
import shutil
from types import SimpleNamespace

import pytest

from research.audits.sumo_branch_feasibility import Signal
from research.audits import audit_sumo_service_ledger as mechanics
from research.experiments import sumo_service_ledger as runtime
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import Clock, Counts
from research.policies.sumo_service_ledger import (
    DECISION_TICKS, MAX_BATCH_TICKS, QUANTUM_TICKS, RULES, SHARE_SCALE,
    Rule, ServiceLedgerPolicy, _pressure_share,
)

AXES = [0, 1, 0, 1]


def packet(ns, ew):
    return Counts((ns, 0, ew, 0), (0, 0, 0, 0), (ns, 0, ew, 0))


def clock(signal):
    return Clock(signal.phase, signal.stage, signal.age)


def step(policy, signal, counts):
    proposal = policy.begin_interval(counts, clock(signal))
    if proposal.interval % DECISION_TICKS == 0:
        signal.request(proposal.phase)
    receipt = policy.finish_interval(proposal, clock(signal))
    signal.advance()
    return proposal, receipt


def prepared_history(skewed=False, initial_phase=0, mode="ledger"):
    policy = ServiceLedgerPolicy(RULES[mode])
    signal = Signal(phase=initial_phase, pending=initial_phase)
    for tick in range(240):
        ns, ew = (0, 0) if tick < 80 else (9 if skewed else 1, 1)
        if initial_phase:
            ns, ew = ew, ns
        step(policy, signal, packet(ns, ew))
    return policy, signal


@pytest.mark.parametrize('pressures', [(0, 0), (1, 1), (9, 1), (1, 9), (0, 3),
    (1, 2*SHARE_SCALE-1), (3, 2*SHARE_SCALE-3), (10**30, 7)])
def test_share_matches_independent_rational_rounding_and_phase_swap(pressures):
    share = _pressure_share(pressures)
    if sum(pressures) == 0:
        assert share is None
    else:
        assert share == round(Fraction(SHARE_SCALE*pressures[0], sum(pressures)))
        assert share + _pressure_share(pressures[::-1]) == SHARE_SCALE


@pytest.mark.parametrize('phase', [0, 1])
def test_continuously_positive_histories_with_same_timers_make_different_decisions(phase):
    balanced, first = prepared_history(initial_phase=phase)
    skewed, second = prepared_history(skewed=True, initial_phase=phase)
    assert asdict(first) == asdict(second)
    current = packet(9, 1) if phase == 0 else packet(1, 9)
    a = balanced.begin_interval(current, clock(first))
    b = skewed.begin_interval(current, clock(second))
    assert a.reference == b.reference == phase
    assert a.phase == 1-phase and b.phase == phase
    assert a.reason == 'allocation_debt'
    assert abs(a.debt_ns_units) == 80*SHARE_SCALE
    assert abs(b.debt_ns_units) < 80*SHARE_SCALE
    assert a.batch.budget == 160 and b.batch.budget == 80


@pytest.mark.parametrize('phase', [0, 1])
@pytest.mark.parametrize('later', ['reversal', 'empty', 'same_entitlement'])
def test_only_actual_green_retires_irrevocable_batch_not_debt(phase, later):
    policy, signal = prepared_history(initial_phase=phase)
    rows = []
    for tick in range(240, 440):
        counts = packet(9, 1) if phase == 0 else packet(1, 9)
        if tick > 240:
            ns, ew = (100, 0) if later == 'reversal' else (0, 0) if later == 'empty' else (0, 100)
            counts = packet(ns, ew) if phase == 0 else packet(ew, ns)
        rows.append(step(policy, signal, counts))
    assert all(r.credited_batch is None for _, r in rows[:40])
    assert sum(r.credited_batch is not None for _, r in rows) == 160
    assert rows[0][1].executed.stage == 'yellow'
    assert rows[40][1].executed == Clock(1-phase, 'green', 0)
    assert rows[120][0].phase == 1-phase  # minimum green elapsed, batch remains
    if later == 'reversal':
        assert rows[120][0].reference == phase
    assert rows[-1][1].completed.budget == rows[-1][1].completed.received == 160
    assert rows[-1][1].batch is None
    if later == 'empty':
        assert rows[120][1].debt_ns_units == 0  # zero debt did not cancel batch
    if later == 'same_entitlement':
        assert abs(rows[-1][1].debt_ns_units) == 80*SHARE_SCALE  # completion != repayment


def test_idle_does_not_buy_empty_green_and_off_gate_demand_reenters_at_next_gate():
    policy, signal = ServiceLedgerPolicy(), Signal()
    for tick in range(85):
        proposal, _ = step(policy, signal, packet(0, 0))
        assert proposal.batch is None
    for tick in range(85, 100):
        proposal, _ = step(policy, signal, packet(0, 5))
        assert proposal.phase == 0 and proposal.batch is None
    proposal, receipt = step(policy, signal, packet(0, 5))
    assert proposal.phase == 1 and proposal.batch is not None
    assert receipt.executed.stage == 'yellow' and receipt.credited_batch is None


@pytest.mark.parametrize('phase',[0,1])
def test_idle_retains_subquantum_debt_then_arbitrates_off_gate_growth(phase):
    policy = ServiceLedgerPolicy()
    signal = Signal(phase=phase,pending=phase)
    demanded = packet(0,1) if phase == 0 else packet(1,0)
    for tick in range(80):
        step(policy,signal,packet(0,0) if tick == 0 else demanded)
    assert abs(policy.snapshot()['debt_ns_units']) == 79*SHARE_SCALE
    p,_ = step(policy,signal,packet(0,0))
    assert p.reason == 'idle' and p.batch is None
    for _ in range(19):
        step(policy,signal,demanded)
    assert abs(policy.snapshot()['debt_ns_units']) == 98*SHARE_SCALE
    p,_ = step(policy,signal,demanded)
    assert p.phase == 1-phase and p.reason == 'allocation_debt'
    assert p.batch.budget == 180


def test_failed_or_duplicate_transactions_cannot_credit_or_change_committed_state():
    policy, other = ServiceLedgerPolicy(), ServiceLedgerPolicy()
    before = policy.snapshot()
    for counts, value in ((None, Clock(0, 'green', 0)), (packet(1, 1), None),
                          (packet(1, 1), Clock(0, 'green', 80))):
        with pytest.raises(ValueError):
            policy.begin_interval(counts, value)
        assert policy.snapshot() == before
    proposal = policy.begin_interval(packet(1, 1), Clock(0, 'green', 0))
    opened = policy.snapshot()
    foreign = other.begin_interval(packet(1, 1), Clock(0, 'green', 0))
    for token, executed in ((replace(proposal), Clock(0, 'green', 0)),
                            (foreign, Clock(0, 'green', 0)),
                            (proposal, Clock(1, 'green', 0))):
        with pytest.raises(ValueError):
            policy.finish_interval(token, executed)
        assert policy.snapshot() == opened
    with pytest.raises(ValueError):
        policy.begin_interval(packet(1, 1), Clock(0, 'green', 0))
    policy.finish_interval(proposal, Clock(0, 'green', 0))
    finished = policy.snapshot()
    with pytest.raises(ValueError):
        policy.finish_interval(proposal, Clock(0, 'green', 0))
    with pytest.raises(ValueError):
        policy.begin_interval(packet(1, 1), Clock(0, 'green', 2))
    assert policy.snapshot() == finished


@pytest.mark.parametrize('mode', tuple(RULES))
@pytest.mark.parametrize('phase', [0, 1])
def test_abrupt_admissible_shares_keep_real_debt_bound_and_budgets(mode, phase):
    policy = ServiceLedgerPolicy(RULES[mode])
    signal = Signal(phase=phase, pending=phase)
    rng = random.Random(721)
    choices = [(0,0), (0,100), (100,0), (1,1), (9,1), (1,9), (1,10**9)]
    seen = set()
    for _ in range(4000):
        p, r = step(policy, signal, packet(*rng.choice(choices)))
        if p.batch is not None:
            assert 80 <= p.batch.budget <= MAX_BATCH_TICKS and p.batch.budget % 20 == 0
            assert 0 <= p.batch.received < p.batch.budget
        if RULES[mode].debt_priority:
            assert abs(r.debt_ns_units) <= 2*QUANTUM_TICKS*SHARE_SCALE
        if r.completed:
            assert r.completed.received == r.completed.budget
            assert r.completed.identifier not in seen
            seen.add(r.completed.identifier)


def test_ablation_separates_arbitration_and_extended_budget():
    expected = {'ledger':(1,160), 'pressure_budget':(0,80), 'pressure_batch':(0,80), 'debt_batch':(1,80)}
    for mode, (target, budget) in expected.items():
        policy, signal = prepared_history(mode=mode)
        p = policy.begin_interval(packet(9,1), clock(signal))
        assert (p.phase, p.batch.budget) == (target, budget)


@pytest.mark.parametrize('values', [(1, True), (True, None)])
def test_invalid_rule_is_rejected(values):
    with pytest.raises(ValueError):
        Rule(*values)


def test_batch_induction_extreme_regions_include_both_sides_of_each_ceiling():
    cases = mechanics.budget_certificate()
    assert len(cases) == 19
    assert cases[0]['selected_debt_units'] == -80*SHARE_SCALE+1
    assert cases[-1]['selected_debt_units'] == 160*SHARE_SCALE
    assert max(c['budget_ticks'] for c in cases) == 240
    assert min(c['minimum_possible_end_debt_units'] for c in cases) >= -160*SHARE_SCALE


@pytest.fixture(scope='module')
def mechanics_artifact(tmp_path_factory):
    directory = tmp_path_factory.mktemp('ledger-mechanics')/'new'
    report = mechanics.create(directory)
    assert report['input_sequences'] == 20 and report['controller_intervals'] == 8800
    assert not report['performance_evaluated'] and report['native_traffic_runs'] == 0
    return directory


def test_mechanics_export_reexecutes_cases_and_preserves_existing_inputs(mechanics_artifact):
    before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in mechanics_artifact.iterdir()}
    receipt = mechanics.verify(mechanics_artifact)
    assert receipt['verified'] and receipt['input_sequences'] == 20
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in mechanics_artifact.iterdir()} == before
    with pytest.raises(FileExistsError):
        mechanics.create(mechanics_artifact)
    with pytest.raises(ValueError,match='existing evidence'):
        mechanics.create(mechanics_artifact/'nested')


@pytest.mark.parametrize('change',['report','trace','trace_type','source'])
def test_mechanics_reconstruction_rejects_tampering_after_output_rehash(mechanics_artifact,tmp_path,change):
    directory = tmp_path/'changed'; shutil.copytree(mechanics_artifact,directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    if change == 'report':
        target = directory/'report.json'; data=json.loads(target.read_text())
        data['sequences'][0]['completed_batches'] += 1
        target.write_text(json.dumps(data))
    elif change in ('trace','trace_type'):
        target = directory/'trace.jsonl.gz'
        with gzip.open(target,'rt') as stream: rows=[json.loads(line) for line in stream]
        rows[0]['receipt']['debt_ns_units'] = 1 if change == 'trace' else False
        with gzip.open(target,'wt') as stream:
            for row in rows: stream.write(json.dumps(row)+'\n')
    else:
        manifest['source_sha256'][mechanics.SOURCES[0]] = '0'*64
        target = None
    if target is not None:
        manifest['output_sha256'][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (directory/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        mechanics.verify(directory)


def physical_fixture(plan, phase, mode='ledger', fault='clean'):
    sensor = CountSensor(next(p for p in PRESETS if p.name == fault), plan['seed'])
    policy, signal = ServiceLedgerPolicy(RULES[mode]), Signal(phase=phase, pending=phase)
    active, previous, rows = [], [], []
    for tick in range(plan['steps']):
        delivered = sensor.step(previous, tick)
        before = asdict(signal)
        p = policy.begin_interval(delivered.counts, clock(signal))
        if tick % 20 == 0:
            signal.request(p.phase)
        r = policy.finish_interval(p, clock(signal))
        requested = [a for a in plan['schedule'] if a[0] == tick]
        active += [[a[2], a[1]+'_in', 1., 0.] for a in requested]
        row = dict(tick=tick, fsm=asdict(signal), lamps=signal.lamps(AXES), vehicles=deepcopy(active),
            requested=requested, pending=[], inserted=[a[2] for a in requested], arrived=[],
            wait_vehicle_seconds=round(len(active)/10,6), sensing=delivered.to_dict(),
            allocation=dict(version=runtime.VERSION, mode=mode, proposal=runtime.record(p), receipt=runtime.record(r)))
        if tick % 20 == 0:
            row['decision'] = dict(packet=delivered.counts.to_dict(), before_fsm=before,
                proposal=p.phase, policy=runtime.record(p))
        rows.append(row); previous = row['vehicles']; signal.advance()
    return rows


@pytest.mark.parametrize('phase', [0,1])
@pytest.mark.parametrize('mode', tuple(RULES))
@pytest.mark.parametrize('fault', ['clean','delay2s_miss30'])
def test_real_delivery_and_physical_accounting_reconstruct(phase, mode, fault):
    plan = dict(seed=83, steps=500, schedule=[[0,'n','n'],[1,'e','e']])
    rows = physical_fixture(plan,phase,mode,fault)
    result = runtime.validate_trace(rows,plan,AXES,phase,mode=mode,fault=fault)
    assert result['requested_vehicles'] == 2
    assert result['allocation']['final_state']['interval'] == 500
    assert result['allocation']['endpoint_censored'] == (result['allocation']['final_state']['batch'] is not None)


@pytest.mark.parametrize('change', ['packet','debt','proposal','budget','receipt','clock','lamps','waiting',
                                  'length','gate','off_gate','mode','version','integer_type'])
def test_replay_rejects_corrupt_policy_sensor_service_and_accounting(change):
    plan = dict(seed=83,steps=300,schedule=[[0,'n','n'],[1,'e','e']])
    rows = physical_fixture(plan,0)
    if change == 'packet': rows[80]['sensing']['counts']['incoming'][0] += 1
    elif change == 'debt': rows[80]['allocation']['receipt']['debt_ns_units'] += 1
    elif change == 'proposal': rows[80]['decision']['proposal'] ^= 1
    elif change == 'budget': rows[80]['allocation']['proposal']['batch']['budget'] += 20
    elif change == 'receipt': rows[80]['allocation']['receipt']['batch']['received'] += 1
    elif change == 'clock': rows[80]['fsm']['age'] += 1
    elif change == 'lamps': rows[80]['lamps'] = 'rrrr'
    elif change == 'waiting': rows[-1]['wait_vehicle_seconds'] += 1
    elif change == 'length': rows.pop()
    elif change == 'gate': rows[80].pop('decision')
    elif change == 'off_gate': rows[81]['decision'] = deepcopy(rows[80]['decision'])
    elif change == 'mode': rows[80]['allocation']['mode'] = 'pressure_batch'
    elif change == 'version': rows[80]['allocation']['version'] = 'invented'
    else: rows[80]['allocation']['receipt']['batch']['received'] = True
    with pytest.raises((ValueError,KeyError)):
        runtime.validate_trace(rows,plan,AXES,0)


@pytest.mark.parametrize('phase',[0,1])
def test_live_adapter_matches_canonical_fixture_and_never_uses_raw_fallback(monkeypatch,phase):
    plan = dict(seed=83,steps=300,schedule=[[0,'n','n'],[1,'e','e']])
    active = []
    def advance(conn,signal,axes,tick,requested,backlog,first_action):
        assert type(first_action) is int and first_action in (0,1)
        if tick % 20 == 0: signal.request(first_action)
        active.extend([[a[2],a[1]+'_in',1.,0.] for a in requested])
        row = dict(tick=tick,fsm=asdict(signal),lamps=signal.lamps(axes),vehicles=deepcopy(active),
            requested=requested,pending=[],inserted=[a[2] for a in requested],arrived=[],
            wait_vehicle_seconds=round(len(active)/10,6))
        signal.advance()
        return row,backlog
    monkeypatch.setattr(runtime,'advance',advance)
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda:0),vehicle=SimpleNamespace(getIDList=lambda:[]))
    live = list(runtime.episode(conn,AXES,plan,phase,lambda:None,fault='delay2s_miss30'))
    assert live == physical_fixture(plan,phase,fault='delay2s_miss30')


@pytest.mark.parametrize('mode,fault', [([], 'clean'), ('ledger', []), ('missing','clean'), ('ledger','missing')])
def test_live_adapter_rejects_bad_mode_or_fault_before_stepping(mode,fault):
    conn = SimpleNamespace(simulation=SimpleNamespace(getTime=lambda:0),vehicle=SimpleNamespace(getIDList=lambda:[]))
    plan = dict(seed=83,steps=1,schedule=[])
    with pytest.raises(ValueError,match='mode or delivered sensing'):
        next(runtime.episode(conn,AXES,plan,0,lambda:None,mode=mode,fault=fault))
