"""Synthetic packet histories and export corruption checks; no native traffic."""
from copy import deepcopy
from dataclasses import asdict
import gzip
import json

import pytest

from research.audits import audit_sumo_observation_timing as tool
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import Clock
from research.policies.sumo_switching import propose


def fixture(job):
    method = tool.method_for(job['method'])
    sensor = CountSensor(next(f for f in PRESETS if f.name == method.fault), job['seed'])
    previous, trace = [], []
    for tick in range(job['steps']):
        delivered = sensor.step(previous, tick)
        phase = job['initial_phase']
        vehicles = ([[f'n{i}', 'n_in', 1., 0.] for i in range(2)] if tick < 20 else
                    [[f'e{i}', 'e_in', 1., 0.] for i in range(3)] if tick < 40 else
                    [[f'n{i}', 'n_in', 1., 0.] for i in range(2)]+[[f'e{i}', 'e_in', 1., 0.] for i in range(3)])
        row = dict(tick=tick, vehicles=vehicles, sensing=delivered.to_dict())
        if tick % 20 == 0:
            clock = Clock(phase, 'green', 80)
            selected = propose(method, delivered.counts, clock)
            row['decision'] = dict(before_fsm={**asdict(clock), 'pending':phase},
                packet=delivered.counts.to_dict(), proposal=selected['proposal'], policy=selected)
        trace.append(row)
        previous = vehicles
    return trace


def job(method='pressure_mixed', phase=0, seed=7):
    return dict(seed=seed, initial_phase=phase, method=method, steps=120, repeat=0, kind='episode')


def test_previous_completed_step_and_delayed_capture_use_the_same_visited_history():
    source = job()
    trace = fixture(source)
    # The current step contradicts its previous completed step at this gate.
    trace[40]['vehicles'] = [[f'n{i}', 'n_in', 1., 0.] for i in range(2)]
    gate = next(g for g in tool.audit_trace(trace, source, 'balanced', 120) if g['tick'] == 40)
    assert gate['delivered']['clean']['counts']['incoming'] == [0,0,3,0]
    assert gate['delivered']['delay2s']['counts']['incoming'] == [2,0,0,0]
    assert gate['proposals']['clean'] == 1 and gate['proposals']['delay2s'] == 0
    assert gate['delivered']['clean']['source_tick'] == 40
    assert gate['delivered']['delay2s']['source_tick'] == 20


@pytest.mark.parametrize('method', ['pressure_clean','pressure_mixed','pressure_margin1'])
@pytest.mark.parametrize('phase', [0,1])
def test_actual_stream_and_proposals_reconstruct_in_each_method_and_start(method, phase):
    source = job(method, phase)
    gates = list(tool.audit_trace(fixture(source), source, 'balanced', 120))
    assert [g['tick'] for g in gates] == [0,20,40,60,80,100]
    assert gates[0]['delivered']['delay2s_miss30']['source_tick'] is None
    if phase == 0:
        # Current pressures 2:3 give a raw switch and a one-count margin hold.
        gate = gates[3]
        assert gate['proposals']['clean'] == 1 and gate['proposals']['margin1'] == 0
        assert gate['margin_held'] is True
    else:
        # Delayed sensing can add a switch rather than merely suppress one.
        assert gates[2]['proposals']['clean'] == 1 and gates[2]['proposals']['delay2s'] == 0


@pytest.mark.parametrize('stage,age', [('green',79), ('yellow',80), ('red',80)])
def test_ineligible_clock_blocks_every_probe(stage, age):
    source = job()
    gate = list(tool.audit_trace(fixture(source), source, 'balanced', 120))[2]
    result = tool.probe(Clock(0,stage,age), gate['delivered'])
    assert not result['eligible'] and set(result['proposals'].values()) == {0}


@pytest.mark.parametrize('change', ['sensor','packet','proposal','policy','off_cadence','tick','short','long'])
def test_raw_audit_rejects_corruption(change):
    source = job()
    trace = fixture(source)
    if change == 'sensor': trace[40]['sensing']['counts']['incoming'][0] += 1
    elif change == 'packet': trace[40]['decision']['packet']['outgoing'][0] += 1
    elif change == 'proposal': trace[40]['decision']['proposal'] = 1-trace[40]['decision']['proposal']
    elif change == 'policy': trace[40]['decision']['policy']['margin_held'] = True
    elif change == 'off_cadence': trace[41]['decision'] = trace[40]['decision']
    elif change == 'tick': trace[40]['tick'] = 39
    elif change == 'short': trace.pop()
    else: trace.append(deepcopy(trace[-1]))
    with pytest.raises(ValueError): list(tool.audit_trace(trace, source, 'balanced', 120))


def test_counts_use_eligible_denominators_and_keep_both_change_directions():
    gates = [dict(eligible=True, clock=dict(phase=0), proposals=dict(clean=1, delay2s=0)),
             dict(eligible=True, clock=dict(phase=0), proposals=dict(clean=0, delay2s=1)),
             dict(eligible=False, clock=dict(phase=0), proposals=dict(clean=0, delay2s=0))]
    result = tool.compare(gates, 'delay2s', 'clean')
    assert result == dict(scheduled_gates=3, eligible_gates=2, changed_proposals=2,
        suppressed_switch_requests=1, added_switch_requests=1, changed_fraction_of_eligible=1.)
    assert tool.compare(gates[-1:], 'delay2s','clean')['changed_fraction_of_eligible'] is None


def test_joint_action_patterns_preserve_interaction_and_margin_disagreement():
    gates = [dict(eligible=True, proposals=dict(clean=0, delay2s=a, miss30=b, delay2s_miss30=1, margin1=0))
             for a,b in [(0,0),(0,1),(1,0),(1,1)]]
    assert tool.pattern(gates) == dict(mixed_changed=4, delay_only_matches=1, misses_only_matches=1,
                                     both_match=1, neither_matches=1, margin_matches=0)


@pytest.fixture
def gate_grid():
    jobs = [job(method,phase) for phase in (0,1) for method in ('pressure_clean','pressure_mixed','pressure_margin1')]
    gates = [g for j in jobs for g in tool.audit_trace(fixture(j),j,'balanced',120)]
    return gates, dict(planned_jobs=jobs), [dict(seed=7,family='balanced')]


@pytest.mark.parametrize('change', ['missing','duplicate','order','clock','probe','pressure','actual','family'])
def test_saved_gate_checks_reject_relabelled_or_changed_evidence(gate_grid,change):
    gates, manifest, frozen = deepcopy(gate_grid)
    if change == 'missing': gates.pop()
    elif change == 'duplicate': gates.append(deepcopy(gates[-1]))
    elif change == 'order': gates[0],gates[1] = gates[1],gates[0]
    elif change == 'clock': gates[2]['delivered']['delay2s']['source_tick'] += 1
    elif change == 'probe': gates[2]['proposals']['clean'] = 1-gates[2]['proposals']['clean']
    elif change == 'pressure': gates[2]['pressures']['clean'][0] += 1
    elif change == 'actual': gates[2]['recorded_proposal'] = 1-gates[2]['recorded_proposal']
    else: gates[2]['family'] = 'unrecorded'
    with pytest.raises(ValueError): tool.tables(gates,manifest,frozen)


def test_tables_retain_visited_method_start_and_overlapping_endpoint(gate_grid):
    tables = tool.tables(*gate_grid)
    assert len(tables['summary']) == 36
    assert len(tables['contexts']) == 72
    assert len(tables['patterns']) == 12
    assert {r['method'] for r in tables['summary']} == {'pressure_clean','pressure_mixed','pressure_margin1'}
    assert {r['initial_phase'] for r in tables['contexts']} == {0,1}


def test_existing_output_and_nested_input_are_rejected_before_source_verification(tmp_path,monkeypatch):
    existing = tmp_path/'existing'
    existing.mkdir()
    (existing/'keep').write_text('keep')
    monkeypatch.setattr(tool,'verify_collection',lambda _: pytest.fail('must reject first'))
    with pytest.raises(FileExistsError): tool.export(tmp_path/'absent',existing)
    assert (existing/'keep').read_text() == 'keep'
    source = tmp_path/'source'
    source.mkdir()
    (source/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='outside'): tool.export(source,source/'new')
    assert not (source/'new').exists()


def test_changed_source_pin_is_rejected_without_output(tmp_path):
    source = tmp_path/'source'
    source.mkdir()
    (source/'report.json').write_text('{}')
    output = tmp_path/'new'
    with pytest.raises(ValueError,match='pinned'): tool.export(source,output)
    assert not output.exists()


@pytest.fixture
def saved_audit(tmp_path,monkeypatch,gate_grid):
    gates, manifest, frozen = gate_grid
    source, mechanics, output = (tmp_path/p for p in ('source','mechanics','audit'))
    for path in (source,mechanics,output): path.mkdir()
    tool.write(source/'manifest.json',manifest)
    tool.write(source/'frozen_plans.json',frozen)
    tool.write(mechanics/'report.json',dict(smoke=True))
    paths = dict(collection=source,mechanics=mechanics)
    monkeypatch.setattr(tool,'input_paths',lambda _: paths)
    tables = tool.tables(gates,manifest,frozen)
    with gzip.open(output/'gates.jsonl.gz','wt') as stream:
        for row in gates: stream.write(json.dumps(row)+'\n')
    for name,rows in tables.items(): tool.csv_write(output/(name+'.csv'),rows)
    with tool.zipfile.ZipFile(output/'source_snapshot.zip','w') as archive:
        for name in tool.SOURCES: archive.write(tool.ROOT/name,name)
    tool.write(output/'report.json',dict(**tool.coverage(gates,manifest),audit_plan=tool.plan(),
        source_verification=dict(verified=True,smoke=False,scientific_panel_complete=True,runs=6,
            signal_samples=720,completed_episode_checkpoints=True,independently_rerun_trajectories=0,publication_ready=False),
        summary=tables['summary'],csv_rows={k:len(v) for k,v in tables.items()},elapsed_audit_seconds=1.))
    tool.write(output/'manifest.json',dict(complete=True,input_directories={k:str(v) for k,v in paths.items()},
        input_sha256={k:tool.hashes(v) for k,v in paths.items()},
        source_sha256={name:tool.file_hash(tool.ROOT/name) for name in tool.SOURCES},output_sha256=tool.hashes(output)))
    return output


@pytest.mark.parametrize('change',['csv','report','gate','input','receipt'])
def test_saved_verifier_reconstructs_after_output_manifest_rehash(saved_audit,change):
    assert tool.verify(saved_audit)['verified']
    if change == 'csv':
        path = saved_audit/'summary.csv'
        path.write_text(path.read_text().replace('pressure_clean','fake_method',1))
    elif change == 'report':
        path = saved_audit/'report.json'
        data = json.loads(path.read_text()); data['source_episodes'] += 1
        tool.write(path,data)
    elif change == 'gate':
        path = saved_audit/'gates.jsonl.gz'
        with gzip.open(path,'rt') as stream: rows = [json.loads(line) for line in stream]
        rows[2]['proposals']['delay2s'] = 1-rows[2]['proposals']['delay2s']
        with gzip.open(path,'wt') as stream:
            for row in rows: stream.write(json.dumps(row)+'\n')
    elif change == 'receipt':
        path = saved_audit/'report.json'
        data = json.loads(path.read_text()); data['source_verification']['verified'] = False
        tool.write(path,data)
    else:
        path = saved_audit.parent/'mechanics'/'report.json'
        path.write_text('{}')
    manifest = json.loads((saved_audit/'manifest.json').read_text())
    manifest['output_sha256'] = tool.hashes(saved_audit,('manifest.json',))
    tool.write(saved_audit/'manifest.json',manifest)
    with pytest.raises(ValueError): tool.verify(saved_audit)
