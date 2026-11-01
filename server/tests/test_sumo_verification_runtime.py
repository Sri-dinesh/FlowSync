"""Runtime dispatch checks avoid changing any frozen study source or evidence."""
from types import SimpleNamespace
import json

import pytest

from research.audits import verify_sumo_panel as tool


def test_recorded_interpreter_selected_over_different_default(tmp_path,monkeypatch):
    current=tmp_path/'server/python'; current.parent.mkdir(); current.touch()
    producer=tmp_path/'results/runtime/sumo_1_24_0/bin/python'; producer.parent.mkdir(parents=True); producer.touch()
    monkeypatch.setattr(tool,'ROOT',tmp_path)
    monkeypatch.setattr(tool.sys,'executable',str(current))
    monkeypatch.setattr(tool.sys,'version','3.14.0 fixture')
    # The producer query is installed when the dispatcher starts probing runtimes.
    import subprocess
    monkeypatch.setattr(subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=0,stdout='3.11.15 fixture\n',stderr=''))
    assert tool.select_interpreter('3.11.15 fixture')==producer


def test_current_interpreter_is_used_when_it_matches_without_querying_others(tmp_path,monkeypatch):
    current=tmp_path/'python'; current.touch()
    monkeypatch.setattr(tool.sys,'executable',str(current)); monkeypatch.setattr(tool.sys,'version','3.11.15 fixture')
    monkeypatch.setattr(tool.subprocess,'run',lambda *a,**k:pytest.fail('no process needed'))
    assert tool.select_interpreter('3.11.15 fixture')==current


def test_wrong_explicit_interpreter_is_rejected_before_replay(tmp_path,monkeypatch):
    current=tmp_path/'python'; current.touch()
    monkeypatch.setattr(tool.sys,'executable',str(current)); monkeypatch.setattr(tool.sys,'version','3.14 fixture')
    monkeypatch.setattr(tool.subprocess,'run',lambda *a,**k:pytest.fail('no replay permitted'))
    with pytest.raises(ValueError,match='No interpreter matches'): tool.select_interpreter('3.11 fixture',current)


@pytest.fixture
def source(tmp_path):
    directory=tmp_path/'study'; directory.mkdir()
    manifest=dict(protocol=dict(version='sumo_history_v1'),runtime=dict(python_version='3.11 fixture'),
                  configuration=dict(smoke=False),planned_jobs=[dict(steps=40)])
    report=dict(complete=True,scientific_panel_complete=True,sessions=[{}])
    (directory/'manifest.json').write_text(json.dumps(manifest)); (directory/'report.json').write_text(json.dumps(report))
    return directory


def proof():
    return dict(verified=True,smoke=False,scientific_panel_complete=True,runs=1,signal_samples=40,sessions=1,
                completed_episode_checkpoints=True,independently_rerun_trajectories=0,publication_ready=False)


def test_dispatch_uses_only_the_recorded_interpreter_and_preserves_inputs(source,tmp_path,monkeypatch):
    selected=tmp_path/'producer'
    monkeypatch.setattr(tool,'select_interpreter',lambda *a:selected)
    calls=[]
    def run(command,**kwargs):
        calls.append((command,kwargs)); return SimpleNamespace(returncode=0,stdout=json.dumps(proof()),stderr='')
    monkeypatch.setattr(tool.subprocess,'run',run)
    before={p.name:p.read_bytes() for p in source.iterdir()}
    output=tmp_path/'receipt.json'
    receipt=tool.verify(source,output=output)
    assert receipt['verified'] and receipt['source_python_matches']
    assert calls[0][0]==[str(selected),'-m','research.pilots.run_sumo_history_panel','--verify',str(source)]
    assert calls[0][1]['env']['PYTHONDONTWRITEBYTECODE']=='1'
    assert before=={p.name:p.read_bytes() for p in source.iterdir()}
    assert json.loads(output.read_text())==receipt


@pytest.mark.parametrize('change',['failed','coverage','invalid_json','invalid_schema','changed_input','unsupported','incomplete'])
def test_verification_cannot_accept_failures_or_relabelled_receipts(source,tmp_path,monkeypatch,change):
    monkeypatch.setattr(tool,'select_interpreter',lambda *a:tmp_path/'producer')
    if change=='unsupported':
        path=source/'manifest.json'; data=json.loads(path.read_text()); data['protocol']['version']='arbitrary.module'; path.write_text(json.dumps(data))
    if change=='incomplete':
        path=source/'report.json'; data=json.loads(path.read_text()); data['complete']=False; path.write_text(json.dumps(data))
    def run(command,**kwargs):
        result=proof()
        if change=='coverage': result['runs']=2
        if change=='invalid_schema': result=[]
        if change=='changed_input': (source/'report.json').write_text('{}')
        return SimpleNamespace(returncode=1 if change=='failed' else 0,
            stdout='invalid' if change=='invalid_json' else json.dumps(result),stderr='strict failure')
    monkeypatch.setattr(tool.subprocess,'run',run)
    output=tmp_path/'receipt.json'
    with pytest.raises(ValueError): tool.verify(source,output=output)
    assert not output.exists()


def test_receipt_outputs_cannot_overwrite_or_mutate_frozen_inputs(source,tmp_path,monkeypatch):
    monkeypatch.setattr(tool,'select_interpreter',lambda *a:pytest.fail('reject before dispatch'))
    existing=tmp_path/'existing.json'; existing.write_text('keep')
    with pytest.raises(FileExistsError): tool.verify(source,output=existing)
    with pytest.raises(ValueError,match='outside'): tool.verify(source,output=source/'new_receipt.json')
    assert existing.read_text()=='keep' and not (source/'new_receipt.json').exists()
