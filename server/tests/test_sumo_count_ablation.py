import gzip
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import zipfile

import pytest

from research.analysis.sumo_count_metrics import summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.audits.verify_sumo_count_ablation import verify
from research.audits.verify_sumo_future_panel import read_trace
from research.experiments import sumo_count_ablation as spec
from research.experiments.sumo_classical_runtime import plans
from research.experiments.sumo_observed_episode import validate_trace
from research.pilots import run_sumo_count_ablation as runner
from research.policies.sumo_total_count import policy_for
from server.tests.test_sumo_classical_panel import AXES, saved_panel, write_json


def test_frozen_full_budget_and_jobs_add_only_one_arm_to_consumed_cases():
    cfg = spec.configuration()
    tasks = spec.jobs(plans(), False)
    assert cfg["cap_seconds"] == 360 and cfg["steps"] == 1800
    assert cfg["reused_development_cases"] and len(tasks) == 15
    assert {t["controller"] for t in tasks} == {"total_incoming"}
    assert [t["seed"] for t in tasks] == [p["seed"] for p in plans()]
    smoke = spec.jobs(plans(True), True)
    assert [(t["controller"], t["repeat"]) for t in smoke] == [("max_pressure", 0), ("total_incoming", 0), ("total_incoming", 1)]
    assert spec.configuration(True)["cap_seconds"] == 120


@pytest.fixture
def reference(saved_panel, tmp_path, monkeypatch):
    # Explicitly synthetic contract fixture; real hash pins stay unchanged in source.
    directory = tmp_path/"reference"
    shutil.copytree(saved_panel, directory)
    write_json(directory/"sumo_command.json", ["sumo", "-n", str(directory/"network.net.xml"), "-r",
        str(directory/"routes.rou.xml"), "--step-length", ".1", "--seed", "110000"])
    report = json.loads((directory/"report.json").read_text())
    report["output_hashes"]["sumo_command.json"] = file_hash(directory/"sumo_command.json")
    write_json(directory/"report.json", report)
    monkeypatch.setitem(spec.REFERENCE_REPORT_HASHES, True, file_hash(directory/"report.json"))
    return directory


@pytest.fixture
def ablation(reference, tmp_path):
    output = tmp_path/"ablation"
    output.mkdir()
    old = spec.load_reference(reference, True)
    tasks = spec.jobs(old["plans"], True)
    write_json(output/"manifest.json", dict(configuration=spec.configuration(True), planned_jobs=tasks,
        versions=old["manifest"]["versions"], reference_input_sha256=old["hashes"],
        reference_manifest_sha256=file_hash(reference/"manifest.json"),
        source_hashes={name: file_hash(spec.ROOT/name) for name in spec.SOURCE_FILES},
        learned_policy_evaluated=False, reused_development_cases=True))
    for name in ("frozen_plans.json", "network.net.xml", "routes.rou.xml"):
        shutil.copyfile(reference/name, output/name)
    write_json(output/"sumo_command.json", spec.command_for(old, output, "sumo"))
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in spec.SOURCE_FILES:
            archive.write(spec.ROOT/name, name)
    anchor = next(r for r in old["rows"] if r["controller"] == "max_pressure" and r["repeat"] == 0)
    trace = read_trace(reference/anchor["trace"])
    rows = []
    for task in tasks:
        name = spec.trace_name(task)
        shutil.copyfile(reference/anchor["trace"], output/name)
        row = dict(**task, family=old["plans"][0]["family"], trace=name,
            metrics=validate_trace(trace, old["plans"][0]["schedule"], policy_for(task["controller"]), AXES, 800),
            semantic_trace_sha256=digest(trace), requested_arrival_sha256=digest(old["plans"][0]["schedule"]))
        rows.append(row)
    (output/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
    write_json(output/"report.json", dict(complete=True, comparison_complete=False, smoke=True, cases=1,
        new_runs=3, new_signal_samples=2400, reference_runs=6, reference_signal_samples=4800,
        anchor_replay_verified=True, total_repeat_verified=True, models_trained=0,
        policy_promoted=False, reused_development_cases=True, controller_means={}, comparisons=[],
        output_hashes={p.name: file_hash(p) for p in output.iterdir()}))
    return output


def test_artifact_verifier_checks_new_and_reused_evidence_without_sumo(ablation, reference):
    result = verify(ablation, reference)
    assert result["verified"] and result["anchor_replay_verified"] and result["total_repeat_verified"]
    assert result["new_signal_samples"] == 2400 and result["reference_signal_samples"] == 4800
    assert result["independently_rerun_trajectories"] == 0 and not result["comparison_complete"]


@pytest.mark.parametrize("mutation", ["incomplete", "relabel", "duplicate", "hash_omission", "source_omission",
                                     "network", "command", "packet", "anchor", "repeat", "reference"])
def test_tampering_partial_cells_and_reference_substitution_are_rejected(ablation, reference, mutation):
    report = json.loads((ablation/"report.json").read_text())
    changed_files = []
    if mutation == "incomplete":
        report["complete"] = False
    elif mutation == "relabel":
        report["comparison_complete"] = True
    elif mutation == "hash_omission":
        del report["output_hashes"]["runs.jsonl"]
    elif mutation == "reference":
        with (reference/"report.json").open("a") as stream:
            stream.write("\n")
    elif mutation == "source_omission":
        manifest = json.loads((ablation/"manifest.json").read_text())
        manifest["source_hashes"].pop(next(iter(manifest["source_hashes"])))
        write_json(ablation/"manifest.json", manifest)
        changed_files = ["manifest.json"]
    elif mutation == "network":
        with (ablation/"network.net.xml").open("a") as stream:
            stream.write("\n")
        changed_files = ["network.net.xml"]
    elif mutation == "command":
        command = json.loads((ablation/"sumo_command.json").read_text())
        command[command.index("--seed")+1] = "999"
        write_json(ablation/"sumo_command.json", command)
        changed_files = ["sumo_command.json"]
    else:
        rows = [json.loads(line) for line in (ablation/"runs.jsonl").read_text().splitlines()]
        if mutation == "duplicate":
            rows.append(rows[0])
        else:
            index = 2 if mutation == "repeat" else 0
            target = ablation/rows[index]["trace"]
            trace = read_trace(target)
            if mutation == "packet":
                trace[0]["decision"]["packet"]["incoming"][0] += 1
            else:
                trace[-1]["vehicles"][0][2] += 1  # Valid counts/wait; violates exact anchor/repeat trajectory equality.
            with gzip.open(target, "wt") as stream:
                stream.writelines(json.dumps(r)+"\n" for r in trace)
            rows[index]["semantic_trace_sha256"] = digest(trace)
            changed_files.append(target.name)
        (ablation/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
        changed_files.append("runs.jsonl")
    for name in changed_files:
        report["output_hashes"][name] = file_hash(ablation/name)
    write_json(ablation/"report.json", report)
    with pytest.raises(ValueError):
        verify(ablation, reference)


def metrics(wait, trips):
    return dict(requested_vehicles=10, mean_stopped_wait_per_requested_vehicle_s=wait,
        p95_accumulated_wait_s=wait*2, max_accumulated_wait_s=wait*3, completed_trips=trips,
        final_active=10-trips, final_entry_backlog=0, endpoint_max_active_pending_wait_s=wait, switch_onsets=3)


def test_full_comparison_keeps_all_regressions_and_component_contrasts():
    frozen = [dict(seed=1, family="a"), dict(seed=2, family="b")]
    old = [dict(seed=p["seed"], family=p["family"], controller=c, repeat=0, metrics=metrics(5 if p["seed"] == 1 else 7, 8))
           for p in frozen for c in ("halted", "fixed", "max_pressure")]
    new = [dict(seed=p["seed"], family=p["family"], controller="total_incoming", repeat=0,
                metrics=metrics(6, 7 if p["seed"] == 1 else 9)) for p in frozen]
    result = summarize(new, old, frozen, False)
    assert len(result["comparisons"]) == 3
    primary = result["comparisons"][0]
    assert primary["primary"] and primary["reference"] == "max_pressure"
    assert primary["mean"]["mean_wait_saved_s"] == 0
    assert primary["direction_counts"]["mean_wait_saved_s"] == dict(improved=1, equal=0, worsened=1)
    assert len(primary["regression_cases"]) == 1 and len(primary["case_results"]) == 2
    assert set(primary["by_family"]) == {"a", "b"}
    with pytest.raises(ValueError, match="Incomplete/duplicate"):
        summarize(new[:1], old, frozen, False)
    with pytest.raises(ValueError, match="Incomplete/duplicate"):
        summarize(new, old+old[:1], frozen, False)


@pytest.mark.parametrize("failure", [TimeoutError, KeyboardInterrupt])
def test_collection_failure_preserves_partial_trace_and_marks_incomplete(reference, tmp_path, monkeypatch, failure):
    import sys
    output = tmp_path/"partial"
    state = dict(closed=False)
    links = [((d+"_in_0", "x", "y"),) for d in "nesw"]
    conn = SimpleNamespace(load=lambda args: None,
        trafficlight=SimpleNamespace(getControlledLinks=lambda _: links),
        close=lambda: state.update(closed=True))
    monkeypatch.setitem(sys.modules, "traci", SimpleNamespace(start=lambda *a, **k: None, getConnection=lambda _: conn))
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda _: "1.24.0")
    monkeypatch.setattr(runner.shutil, "which", lambda *a, **k: "/fake/sumo")
    def interrupted(*args):
        yield dict(tick=0)
        raise failure("test stop")
    monkeypatch.setattr(runner, "episode", interrupted)
    with pytest.raises(failure):
        runner.run(reference, output, True)
    report = json.loads((output/"report.json").read_text())
    assert not report["complete"] and not report["comparison_complete"] and state["closed"]
    assert report["completed_runs"] == 0
    assert read_trace(next(output.glob("trace_*.gz"))) == [dict(tick=0)]
    with pytest.raises(ValueError, match="Incomplete"):
        verify(output, reference)


def test_existing_evidence_cannot_be_an_output_directory(tmp_path):
    reference = tmp_path/"original"
    reference.mkdir()
    with pytest.raises(ValueError, match="outside the frozen"):
        runner.run(reference, reference/"nested", True)
    with pytest.raises(FileExistsError):
        runner.run(reference, reference, True)
    assert list(reference.iterdir()) == []
