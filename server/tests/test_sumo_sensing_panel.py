"""Synthetic evidence contracts; real SUMO execution is the separate smoke."""
from copy import deepcopy
import json
import shutil
import zipfile

import pytest

from research.analysis.sumo_sensing_metrics import MEASURES, SUMMARY_MEASURES, seed_interval, summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.experiments.sumo_sensing import PLAN, configuration, physical_view, plans, validate_trace
from research.observation.sumo_sensing import PRESETS
from research.pilots.run_sumo_sensing_panel import (
    ROOT,SOURCES,SUMO_OPTIONS,case_table,read_trace,save_trace,trace_name,verify,write,write_csv,
)
from research.policies.sumo_classical import CONTROLLERS
from server.tests.test_sumo_sensing import AXES,trace_fixture


def test_scientific_grid_and_exact_seed_bootstrap_keep_correlated_frames_out():
    frozen = plans()
    assert len(frozen) == 6 and len({p["seed"] for p in frozen}) == 6
    assert configuration()["cap_seconds"] == 900 and configuration(True)["cap_seconds"] == 240
    assert {p["seed"] for p in frozen}.isdisjoint({p["seed"] for p in plans(True)})
    rows = []
    for p in frozen:
        for controller in CONTROLLERS:
            for fault in PRESETS:
                penalty = {"clean":0,"delay2s":1,"miss30":2,"delay2s_miss30":5}[fault.name]
                metrics = dict.fromkeys(SUMMARY_MEASURES,0.)
                metrics.update(dict(zip(MEASURES,(10.+penalty,20.+penalty,100.-penalty))))
                rows.append(dict(seed=p["seed"],controller=controller,fault=fault.name,repeat=0,metrics=metrics))
    report = summarize(rows,frozen,1)
    assert len(rows) == 72 and len(report["contrasts"]) == 20 and len(report["paired_contrasts"]) == 120
    effect = next(r for r in report["contrasts"] if r["kind"] == "fault_minus_clean" and r["fault"] == "delay2s")
    interval = effect["metrics"][MEASURES[0]]["interval"]
    assert interval == dict(lower=1.,upper=1.,ordered_draws=64)
    interaction = next(r for r in report["contrasts"] if r["kind"] == "factorial_interaction")
    assert interaction["metrics"][MEASURES[0]]["mean"] == 2.
    assert seed_interval({1350901:10.},plans(True)) is None
    with pytest.raises(ValueError,match="Incomplete/duplicate"):
        summarize(rows[:-1],frozen,1)
    repeated = deepcopy(rows)
    for row in repeated:
        row["repeat"] = 1
        row["metrics"][MEASURES[0]] += 1000
    assert summarize(rows+repeated,frozen,2) == report


@pytest.fixture(scope="module")
def saved_panel(tmp_path_factory):
    output = tmp_path_factory.mktemp("sensing_contract_only")
    cfg,frozen,rows = configuration(True),plans(True),[]
    write(output/"manifest.json",dict(plan=PLAN,configuration=cfg,
        runtime=dict(python_version="synthetic contract fixture",versions=dict.fromkeys(("eclipse-sumo","traci","sumolib"),"1.24.0"),
            native_binary_sha256=dict.fromkeys(("sumo","netconvert"),"0"*64),
            binary_versions=dict.fromkeys(("sumo","netconvert"),"synthetic Version 1.24.0")),git_commit="0"*40,
        source_hashes={n:file_hash(ROOT/n) for n in SOURCES},mechanics=None))
    write(output/"frozen_plans.json",frozen)
    with zipfile.ZipFile(output/"source_snapshot.zip","w") as archive:
        for name in SOURCES:
            archive.write(ROOT/name,name)
    for name in ("nodes.nod.xml","edges.edg.xml","connections.con.xml","routes.rou.xml"):
        (output/name).write_text("synthetic contract fixture, no SUMO dynamics")
    (output/"network.net.xml").write_text('<net>'+''.join(
        f'<connection tl="c" linkIndex="{i}" from="{d}_in"/>' for i,d in enumerate("nesw"))+'</net>')
    write(output/"sumo_command.json",["sumo","-n","network.net.xml","-r","routes.rou.xml",*SUMO_OPTIONS])
    plan = frozen[0]
    anchor = [{k:v for k,v in r.items() if k != "sensing"} for r in trace_fixture(plan)]
    save_trace(output/"clean_anchor.jsonl.gz",anchor)
    for controller in CONTROLLERS:
        for fault in PRESETS:
            trace = trace_fixture(plan,controller,fault)
            for repeat in range(2):
                name = trace_name(plan["seed"],controller,fault.name,repeat)
                save_trace(output/name,trace)
                rows.append(dict(seed=plan["seed"],family=plan["family"],controller=controller,fault=fault.name,repeat=repeat,
                    metrics=validate_trace(trace,plan,controller,fault,AXES),trace=name,
                    semantic_trace_sha256=digest(trace),requested_arrival_sha256=digest(plan["schedule"])))
    (output/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
    summary = summarize(rows,frozen,2)
    write_csv(output/"cases.csv",case_table(rows))
    write_csv(output/"aggregate.csv",summary["aggregate"])
    write_csv(output/"paired_contrasts.csv",summary["paired_contrasts"])
    write(output/"report.json",dict(complete=True,scientific_panel_complete=False,smoke=True,policy_promoted=False,
        publication_ready=False,cases=1,runs=24,signal_samples=19200,mechanics_anchor_runs=1,
        mechanics_anchor_signal_samples=800,fixed_invariance_verified=True,repeat_mechanics_verified=True,
        clean_anchor_verified=True,summary=summary,output_hashes={p.name:file_hash(p) for p in output.iterdir()}))
    return output


def test_full_saved_smoke_replay_needs_no_sumo_installation(saved_panel):
    report = verify(saved_panel)
    assert report["verified"] and report["smoke"] and not report["scientific_panel_complete"]
    assert report["runs"] == 24 and report["signal_samples"] == 19200
    assert report["independently_rerun_trajectories"] == 0


@pytest.mark.parametrize("mutation",["relabel","missing_cell","packet_rehash","source_omission","runtime_omission","extra_output","summary","command"])
def test_hash_repair_cannot_hide_changed_packets_cells_or_scope(saved_panel,tmp_path,mutation):
    output = tmp_path/"panel"
    shutil.copytree(saved_panel,output)
    report = json.loads((output/"report.json").read_text())
    if mutation == "relabel":
        report["scientific_panel_complete"] = True
    elif mutation in ("missing_cell","packet_rehash"):
        rows = [json.loads(line) for line in (output/"runs.jsonl").read_text().splitlines()]
        if mutation == "missing_cell":
            rows.pop()
        else:
            target = output/rows[0]["trace"]
            trace = read_trace(target)
            trace[0]["sensing"]["source_tick"] = None
            target.unlink()
            save_trace(target,trace)
            rows[0]["semantic_trace_sha256"] = digest(trace)
            report["output_hashes"][target.name] = file_hash(target)
        (output/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
        report["output_hashes"]["runs.jsonl"] = file_hash(output/"runs.jsonl")
    elif mutation in ("source_omission","runtime_omission"):
        manifest = json.loads((output/"manifest.json").read_text())
        if mutation == "source_omission":
            manifest["source_hashes"].pop(next(iter(manifest["source_hashes"])))
        else:
            manifest["runtime"].pop("native_binary_sha256")
        write(output/"manifest.json",manifest)
        report["output_hashes"]["manifest.json"] = file_hash(output/"manifest.json")
    elif mutation == "extra_output":
        (output/"unexpected").write_text("unrecorded")
    elif mutation == "summary":
        report["summary"]["aggregate"][0][MEASURES[0]] += 1.
    else:
        command = json.loads((output/"sumo_command.json").read_text())
        command[command.index("--step-length")+1] = ".2"
        write(output/"sumo_command.json",command)
        report["output_hashes"]["sumo_command.json"] = file_hash(output/"sumo_command.json")
    write(output/"report.json",report)
    with pytest.raises(ValueError):
        verify(output)


def test_fixed_trace_is_invariant_even_when_observation_counts_differ():
    plan = plans(True)[0]
    clean,faulted = trace_fixture(plan,"fixed"),trace_fixture(plan,"fixed",PRESETS[3])
    assert physical_view(clean) == physical_view(faulted)
    assert clean != faulted
