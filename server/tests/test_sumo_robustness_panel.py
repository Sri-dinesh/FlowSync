import copy
import gzip
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import zipfile

import pytest

from research.analysis.sumo_robustness_metrics import check_mechanics, measurements, summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.audits.verify_sumo_future_panel import read_trace
from research.audits.verify_sumo_robustness import verify
from research.experiments import sumo_robustness as spec
from research.pilots import run_sumo_robustness_panel as runner
from server.tests.test_sumo_robustness_phase import AXES, canonical_trace


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+"\n")


def test_design_is_bounded_new_cases_with_both_starts_and_explicit_overlap():
    cfg, plans, tasks = spec.configuration(), spec.plans(), spec.jobs()
    assert len(plans) == 6 and len(tasks) == cfg["planned_runs"] == 24
    assert sum(t["steps"] for t in tasks) == cfg["planned_signal_samples"] == 86400
    assert cfg["endpoint_ticks"] == [1800, 3600] and cfg["cap_seconds"] == 900
    assert {t["initial_phase"] for t in tasks} == {0, 1}
    assert {p["seed"] for p in plans}.isdisjoint({110001, 110101, 110201, 112901})
    assert all(p["schedule"] for p in plans) and plans == spec.plans()
    assert len(spec.jobs(True)) == 10 and sum(t["steps"] for t in spec.jobs(True)) == 7200
    spec.check_pins()


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    output = tmp_path_factory.mktemp("synthetic_robustness")
    cfg, plans, tasks = spec.configuration(True), spec.plans(True), spec.jobs(True)
    write_json(output/"manifest.json", dict(configuration=cfg, planned_jobs=tasks,
        versions=dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0"),
        source_hashes={name: file_hash(spec.ROOT/name) for name in spec.SOURCE_FILES},
        known_demand_families=True, learned_policy_evaluated=False))
    write_json(output/"frozen_plans.json", plans)
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in spec.SOURCE_FILES:
            archive.write(spec.ROOT/name, name)
    for name in ("nodes.nod.xml", "edges.edg.xml", "connections.con.xml", "routes.rou.xml"):
        (output/name).write_text("synthetic contract test only")
    (output/"network.net.xml").write_text('<net>'+''.join(
        f'<connection tl="c" linkIndex="{i}" from="{d}_in"/>' for i, d in enumerate("nesw"))+'</net>')
    write_json(output/"sumo_command.json", ["sumo", "-n", str(output/"network.net.xml"), "-r", str(output/"routes.rou.xml"),
        "--step-length", ".1", "--seed", "110000", "--time-to-teleport", "-1", "--no-step-log", "true",
        "--duration-log.disable", "true", "--xml-validation", "never"])
    rows = []
    for task in tasks:
        plan = spec.trim_plan(plans[0], task["steps"])
        trace = canonical_trace(plan["schedule"], task["steps"], task["initial_phase"], task["controller"])
        name = spec.trace_name(task)
        with gzip.open(output/name, "wt") as stream:
            stream.writelines(json.dumps(r)+"\n" for r in trace)
        rows.append(dict(**task, family=plan["family"], trace=name,
            measurements=measurements(trace, plan, task, AXES, cfg),
            requested_arrival_sha256=digest(plan["schedule"]), semantic_trace_sha256=digest(trace),
            prefix_semantic_trace_sha256=digest(trace[:cfg["endpoint_ticks"][0]])))
    (output/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
    write_json(output/"report.json", dict(complete=True, robustness_complete=False, smoke=True,
        traffic_seeds=1, paired_start_contexts=2, runs=10, executed_signal_samples=7200,
        measurement_endpoints_seconds=[40, 80], primary_endpoint_seconds=80,
        prefix_measurements_overlap=True, mechanics=check_mechanics(rows, True),
        models_trained=0, policy_promoted=False, publication_ready=False, component_series_closed_on_completion=False,
        **summarize(rows, plans, cfg), output_hashes={p.name: file_hash(p) for p in output.iterdir()}))
    return output


def test_verifier_reconstructs_canonical_start_and_overlapping_measurements_without_sumo(saved):
    result = verify(saved)
    assert result["verified"] and result["smoke"] and not result["robustness_complete"]
    assert result["runs"] == 10 and result["executed_signal_samples"] == 7200
    assert result["traffic_seeds"] == 1 and result["paired_start_contexts"] == 2
    assert result["independently_rerun_trajectories"] == 0


@pytest.mark.parametrize("mutation", ["incomplete", "relabel", "duplicate", "coverage", "omitted_hash", "source_omission",
                                     "endpoint", "phase", "repeat", "prefix_replay", "extended"])
def test_tampered_or_partial_robustness_evidence_is_rejected(saved, tmp_path, mutation):
    output = tmp_path/"panel"
    shutil.copytree(saved, output)
    # Update paths after copying so command validation tests the intended mutation.
    command = json.loads((output/"sumo_command.json").read_text())
    command[2], command[4] = str(output/"network.net.xml"), str(output/"routes.rou.xml")
    write_json(output/"sumo_command.json", command)
    report = json.loads((output/"report.json").read_text())
    changed = ["sumo_command.json"]
    if mutation == "incomplete":
        report["complete"] = False
    elif mutation == "relabel":
        report["smoke"] = False
    elif mutation == "coverage":
        report["executed_signal_samples"] += 4000
    elif mutation == "omitted_hash":
        del report["output_hashes"]["frozen_plans.json"]
    elif mutation == "source_omission":
        manifest = json.loads((output/"manifest.json").read_text())
        manifest["source_hashes"].pop(next(iter(manifest["source_hashes"])))
        write_json(output/"manifest.json", manifest)
        changed.append("manifest.json")
    else:
        rows = [json.loads(line) for line in (output/"runs.jsonl").read_text().splitlines()]
        if mutation == "duplicate":
            rows.append(rows[0])
        elif mutation == "endpoint":
            rows[0]["measurements"]["40"]["overall"]["requested_vehicles"] += 1
        else:
            index = 1 if mutation == "repeat" else 8 if mutation == "prefix_replay" else 0
            trace = read_trace(output/rows[index]["trace"])
            if mutation == "phase":
                trace[0]["fsm"]["phase"] ^= 1
            elif mutation == "extended":
                trace.append(copy.deepcopy(trace[-1]))
            else:
                trace[-1]["vehicles"][0][2] += 1  # Counts/metrics remain valid; exact replay/repeat must fail.
            name = rows[index]["trace"]
            with gzip.open(output/name, "wt") as stream:
                stream.writelines(json.dumps(r)+"\n" for r in trace)
            rows[index]["semantic_trace_sha256"] = digest(trace)
            rows[index]["prefix_semantic_trace_sha256"] = digest(trace[:400])
            changed.append(name)
        (output/"runs.jsonl").write_text(''.join(json.dumps(r)+"\n" for r in rows))
        changed.append("runs.jsonl")
    for name in changed:
        report["output_hashes"][name] = file_hash(output/name)
    write_json(output/"report.json", report)
    with pytest.raises(ValueError):
        verify(output)


@pytest.mark.parametrize("failure", [TimeoutError, KeyboardInterrupt])
def test_interrupted_collection_preserves_partial_gzip_and_failure_status(tmp_path, monkeypatch, failure):
    import sys
    output = tmp_path/"partial"
    closed = []
    links = [((d+"_in_0", "x", "y"),) for d in "nesw"]
    conn = SimpleNamespace(load=lambda args: None, close=lambda: closed.append(True),
        trafficlight=SimpleNamespace(getControlledLinks=lambda _: links))
    monkeypatch.setitem(sys.modules, "traci", SimpleNamespace(start=lambda *a, **k: None, getConnection=lambda _: conn))
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda _: "1.24.0")
    monkeypatch.setattr(runner.shutil, "which", lambda name, **k: "/fake/"+name)
    monkeypatch.setattr(runner, "network", lambda *a: None)
    def stopped(*args):
        yield dict(tick=0)
        raise failure("test stop")
    monkeypatch.setattr(runner, "episode", stopped)
    with pytest.raises(failure):
        runner.run(output, True)
    report = json.loads((output/"report.json").read_text())
    assert not report["complete"] and not report["robustness_complete"] and closed
    assert read_trace(next(output.glob("trace_*.gz"))) == [dict(tick=0)]
    with pytest.raises(ValueError, match="Incomplete"):
        verify(output)


def test_existing_and_nested_artifacts_cannot_be_overwritten(tmp_path):
    artifact = tmp_path/"old"
    artifact.mkdir()
    (artifact/"report.json").write_text("preserve")
    with pytest.raises(FileExistsError):
        runner.run(artifact, True)
    with pytest.raises(ValueError, match="outside recorded"):
        runner.run(artifact/"new", True)
    assert (artifact/"report.json").read_text() == "preserve"
