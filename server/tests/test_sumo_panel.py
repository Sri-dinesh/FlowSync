"""Generic episode checkpoint contracts with explicitly synthetic native stubs."""
from copy import deepcopy
import json
import shutil
import sys
from types import SimpleNamespace

import pytest

from research.experiments.sumo_panel import Panel,base,ROOT


def fake_study():
    source='research/experiments/sumo_panel.py'
    sources=(source,)
    jobs=[dict(seed=7,initial_phase=0,method=m,repeat=0,kind='episode',steps=40) for m in ('a','b','c')]
    spec=dict(version='synthetic_panel',base_source_sha256={source:base.file_hash(ROOT/source)},smoke_pause_after_jobs=2)
    def episode(conn,axes,plan,job,budget):
        for tick in range(job['steps']):
            budget()
            row=dict(tick=tick,value=ord(job['method']),vehicles=[],fsm={})
            if tick%20==0: row['decision']=dict(before_fsm=dict(phase=0,stage='green',age=tick),proposal=0,policy={})
            yield row
    def measured(trace,plan,job,axes,smoke):
        if len(trace)!=40 or any(r['tick']!=i or r['value']!=ord(job['method']) for i,r in enumerate(trace)):
            raise ValueError('Synthetic trace is invalid')
        return {'2':dict(signal_samples=20),'4':dict(signal_samples=40)}
    def analyze(rows,smoke):
        if len(rows)!=3: raise ValueError('Synthetic grid is incomplete')
        return dict(candidate_screen=None,mechanics=dict(scope='synthetic fixture, not native science'))
    return SimpleNamespace(SOURCES=sources,protocol=lambda:deepcopy(spec),
        configuration=lambda smoke:dict(smoke=smoke,steps=40,endpoint_ticks=[20,40],session_cap_seconds=360,max_sessions=4),
        jobs=lambda smoke:deepcopy(jobs),plans=lambda smoke:[dict(seed=7,family='balanced',steps=40,schedule=[[0,'n','a']])],
        episode=episode,measurements=measured,analyze=analyze)


@pytest.fixture(scope='module')
def completed(tmp_path_factory,request):
    patch=pytest.MonkeyPatch(); request.addfinalizer(patch.undo)
    output=tmp_path_factory.mktemp('synthetic_panel')/'batch'
    environment=dict(python_version='synthetic fixture',versions=dict.fromkeys(('eclipse-sumo','traci','sumolib'),'1.24.0'),
        native_binary_sha256=dict.fromkeys(('sumo','netconvert'),'0'*64),
        binary_versions=dict.fromkeys(('sumo','netconvert'),'synthetic Version 1.24.0'))
    patch.setattr(base,'runtime',lambda:({'sumo':'synthetic','netconvert':'synthetic'},environment))
    patch.setattr(base.subprocess,'check_output',lambda command,**kw:'0'*40 if 'rev-parse' in command else '')
    def network(directory,binary):
        for name in base.STATIC-{'frozen_plans.json','source_snapshot.zip','sumo_command.json','network.net.xml'}:
            (directory/name).write_text('synthetic fixture')
        (directory/'network.net.xml').write_text('<net>'+''.join(
            f'<connection tl="c" linkIndex="{i}" from="{d}_in"/>' for i,d in enumerate('nesw'))+'</net>')
    patch.setattr(base,'network',network)
    conn=SimpleNamespace(load=lambda _:None,close=lambda:None,
        trafficlight=SimpleNamespace(getControlledLinks=lambda _: [[(d+'_in_0','out','via')] for d in 'nesw']))
    patch.setitem(sys.modules,'traci',SimpleNamespace(start=lambda *a,**kw:None,getConnection=lambda _:conn))
    study=fake_study(); original=study.episode; calls=0
    def interrupted(*args):
        nonlocal calls
        calls+=1
        if calls==3:
            yield next(iter(original(*args)))
            raise KeyboardInterrupt('synthetic explicit interruption')
        yield from original(*args)
    study.episode=interrupted
    panel=Panel(study)
    with pytest.raises(KeyboardInterrupt): panel.collect(output,smoke=True)
    old={folder.name:base.hashes(folder) for folder in (output/'sessions').glob('session_*')}
    assert len(list((output/'sessions').glob('session_*/record_*.json')))==2
    study.episode=original
    assert panel.run(output,smoke=True,resume=True)['complete']
    assert old=={name:base.hashes(output/'sessions'/name) for name in old}
    return panel,output


def test_validated_resume_preserves_prior_bytes_and_completed_resume_adds_no_work(completed):
    panel,output=completed
    proof=panel.verify(output)
    assert proof['verified'] and proof['sessions']==3 and proof['runs']==3 and proof['signal_samples']==120
    before=base.hashes(output)
    panel.run(output,smoke=True,resume=True)
    assert base.hashes(output)==before


def test_completed_evidence_cannot_be_resealed(completed,tmp_path):
    panel,source=completed; output=tmp_path/'copy'; shutil.copytree(source,output)
    original=(output/'report.json').read_bytes()
    (output/'external.txt').write_text('external change')
    with pytest.raises(ValueError,match='Sealed'): panel.run(output,smoke=True,resume=True)
    assert (output/'report.json').read_bytes()==original


def test_existing_output_and_concurrent_access_are_rejected(completed):
    panel,output=completed
    with pytest.raises(FileExistsError): panel.run(output,smoke=True)
    with base.exclusive(output):
        with pytest.raises(ValueError,match='holds'): panel.verify(output)


@pytest.mark.parametrize('change',['summary','record','trace','source','archive','cap','duplicate','runtime'])
def test_tampering_is_rejected(completed,tmp_path,change):
    panel,source=completed; output=tmp_path/'copy'; shutil.copytree(source,output)
    if change=='summary':
        path=output/'report.json'; data=json.loads(path.read_text()); data['completed_runs']+=1
    elif change=='source':
        path=output/'manifest.json'; data=json.loads(path.read_text()); data['source_sha256']={}
    elif change=='runtime':
        path=output/'manifest.json'; data=json.loads(path.read_text()); data['runtime']['versions']['traci']='wrong'
    elif change=='cap':
        path=output/'sessions/session_0000/started.json'; data=json.loads(path.read_text()); data['cap_seconds']+=1
    elif change=='archive':
        (output/'source_snapshot.zip').write_bytes(b'invalid archive')
        with pytest.raises(ValueError): panel.verify(output)
        return
    else:
        path=next((output/'sessions/session_0000').glob('record_*.json')); data=json.loads(path.read_text())
        if change=='duplicate':
            shutil.copyfile(path,output/'sessions/session_0001'/path.name)
            with pytest.raises(ValueError): panel.verify(output)
            return
        if change=='record': data['measurements']['4']['signal_samples']+=1
        else:
            trace_path=output/data['trace']; trace=base.read_trace(trace_path); trace[-1]['value']+=1
            trace_path.unlink(); base.save_trace(trace_path,trace); data['trace_sha256']=base.file_hash(trace_path)
    base.atomic_json(path,data,replace=True)
    with pytest.raises(ValueError): panel.verify(output)


def test_budget_auto_continuation_does_not_swallow_other_errors(tmp_path,monkeypatch):
    study=fake_study(); panel=Panel(study); calls=[]
    base.atomic_json(tmp_path/'manifest.json',dict(configuration=study.configuration(True)))
    monkeypatch.setattr(panel,'history',lambda *args:[{}])
    def run(output,smoke,mechanics,resume):
        calls.append(resume)
        if len(calls)==1: raise base.SessionBudgetExceeded('cap')
        return dict(complete=True)
    monkeypatch.setattr(panel,'run',run)
    assert panel.collect(tmp_path,smoke=True)['complete'] and calls==[False,True]
    def fail(*args): raise ValueError('invalid sensor')
    monkeypatch.setattr(panel,'run',fail)
    with pytest.raises(ValueError,match='sensor'): panel.collect(tmp_path,smoke=True)
