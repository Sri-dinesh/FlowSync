"""Seed hierarchy, atomic publication and restart contracts without native traffic."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from research.analysis import sumo_switching_metrics as analysis
from research.experiments import sumo_switching as runtime
from research.pilots import run_sumo_switching_panel as tool
from server.tests.test_sumo_switching import fixture


def synthetic_rows():
    rows = []
    for job in runtime.jobs():
        measured = {}
        for seconds in (180, 360):
            value = 10 if job["method"] == "pressure_clean" else 8 if job["method"] == "pressure_margin1" else 8 if job["initial_phase"] == 0 else 12
            measured[str(seconds)] = dict(requested_vehicles=100, signal_samples=seconds*10,
                mean_stopped_wait_per_requested_vehicle_s=value, p95_accumulated_wait_s=value*2,
                completed_trips=110-value, service=dict(green_ns_s=seconds*.4, green_ew_s=seconds*.4,
                clearance_s=seconds*.2, margin_held_gates=int(job["method"] == "pressure_margin1")), sensing={})
        plan = next(p for p in runtime.plans() if p["seed"] == job["seed"])
        rows.append(dict(**job, family=plan["family"], measurements=measured))
    return rows


def test_starts_average_within_seed_and_cis_keep_six_traffic_replicates():
    result = analysis.summarize(synthetic_rows(), runtime.plans())
    primary = result["endpoint_comparisons"]["360"]
    contrast = primary["contrasts"]["mixed_minus_clean"]
    metric = "mean_stopped_wait_per_requested_vehicle_s"
    assert contrast["metrics"][metric]["mean"] == 0
    assert contrast["metrics"][metric]["interval"] == dict(lower=0, upper=0, ordered_draws=64)
    assert contrast["by_initial_phase"]["0"][metric] == -2 and contrast["by_initial_phase"]["1"][metric] == 2
    assert len(contrast["seed_rows"]) == 6 and len(contrast["context_rows"]) == 12
    assert result["replication"]["prefix_endpoints_overlap"] and result["replication"]["independent_training_replicates"] == 0
    assert result["candidate_screen"]["continue_to_bounded_mechanism_development"]


def test_aggregate_gain_cannot_hide_a_bad_seed_in_the_frozen_screen():
    rows = synthetic_rows()
    seed = rows[0]["seed"]
    for row in rows:
        if row["seed"] == seed and row["method"] == "pressure_margin1":
            row["measurements"]["360"]["mean_stopped_wait_per_requested_vehicle_s"] = 11
    result = analysis.summarize(rows, runtime.plans())
    assert not result["candidate_screen"]["continue_to_bounded_mechanism_development"]
    assert "seed_mean_loss_vs_pressure_clean" in result["candidate_screen"]["failures"]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "order", "denominator"])
def test_invalid_grid_or_pairing_is_rejected(mutation):
    rows = synthetic_rows()
    if mutation == "missing": rows.pop()
    elif mutation == "duplicate": rows[-1] = deepcopy(rows[0])
    elif mutation == "order": rows[0], rows[1] = rows[1], rows[0]
    else: rows[0]["measurements"]["180"]["requested_vehicles"] = 99
    with pytest.raises(ValueError): analysis.summarize(rows, runtime.plans())


@pytest.fixture(scope="module")
def resumed_smoke(tmp_path_factory, request):
    patch = pytest.MonkeyPatch()
    request.addfinalizer(patch.undo)
    directory = tmp_path_factory.mktemp("synthetic_switching")/"batch"
    patch.setattr(runtime, "arrivals", lambda seed, *args: [[0, "n", f"n_{seed}"], [1, "e", f"e1_{seed}"], [2, "w", f"e2_{seed}"]])
    environment = dict(python_version="synthetic Python fixture", versions=dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0"),
        native_binary_sha256=dict.fromkeys(("sumo", "netconvert"), "0"*64),
        binary_versions=dict.fromkeys(("sumo", "netconvert"), "synthetic Version 1.24.0"))
    patch.setattr(tool, "runtime", lambda: ({"sumo":"synthetic", "netconvert":"synthetic"}, environment))
    patch.setattr(tool.subprocess, "check_output", lambda command, **kwargs: "0"*40 if "rev-parse" in command else "")
    def network(output, binary):
        for name in tool.STATIC - {"frozen_plans.json", "source_snapshot.zip", "sumo_command.json", "network.net.xml"}:
            (output/name).write_text("synthetic contract fixture; no native simulation")
        (output/"network.net.xml").write_text('<net>'+''.join(
            f'<connection tl="c" linkIndex="{i}" from="{d}_in"/>' for i, d in enumerate("nesw"))+'</net>')
    patch.setattr(tool, "network", network)
    conn = SimpleNamespace(load=lambda _: None, close=lambda: None,
        trafficlight=SimpleNamespace(getControlledLinks=lambda _: [[(d+"_in_0", "out", "via")] for d in "nesw"]))
    patch.setitem(sys.modules, "traci", SimpleNamespace(start=lambda *a, **kw: None, getConnection=lambda _: conn))
    calls = 0
    def interrupted(conn, axes, plan, method, phase, budget):
        nonlocal calls
        calls += 1
        rows = fixture(plan, method, phase)
        if calls == 4:
            yield rows[0]
            raise KeyboardInterrupt("simulated restart")
        yield from rows
    patch.setattr(tool, "episode", interrupted)
    with pytest.raises(KeyboardInterrupt): tool.collect(directory, smoke=True)
    old = {folder.name:tool.hashes(folder) for folder in (directory/"sessions").iterdir()}
    assert len(list((directory/"sessions").glob("session_*/record_*.json"))) == 3
    assert not json.loads((directory/"report.json").read_text())["complete"]
    patch.setattr(tool, "episode", lambda conn, axes, plan, method, phase, budget: iter(fixture(plan, method, phase)))
    def anchor(conn, axes, plan, controller, fault, budget):
        name = "pressure_clean" if fault.name == "clean" else "pressure_mixed"
        return iter(runtime.historical_view(fixture(plan, runtime.method_for(name), 0)))
    patch.setattr(tool, "anchor_episode", anchor)
    completed = tool.run(directory, smoke=True, resume=True)
    assert old == {name:tool.hashes(directory/"sessions"/name) for name in old}
    assert completed["complete"] and completed["completed_runs"] == 28
    yield directory


def test_resume_preserves_completed_episodes_and_skips_them(resumed_smoke):
    checked = tool.verify(resumed_smoke)
    assert checked["verified"] and checked["runs"] == 28 and checked["signal_samples"] == 20000
    assert checked["sessions"] == 3 and not checked["scientific_panel_complete"]
    report = json.loads((resumed_smoke/"report.json").read_text())
    assert report["analysis"]["mechanics"]["margin_held_gates"] > 0
    before = tool.hashes(resumed_smoke)
    tool.run(resumed_smoke, smoke=True, resume=True)
    assert before == tool.hashes(resumed_smoke)


def test_existing_directory_and_concurrent_collector_are_refused(resumed_smoke):
    with pytest.raises(FileExistsError): tool.run(resumed_smoke, smoke=True)
    with tool.exclusive(resumed_smoke):
        with pytest.raises(ValueError, match="holds"): tool.run(resumed_smoke, smoke=True, resume=True)


def test_completed_batch_cannot_be_resealed_after_external_change(resumed_smoke, tmp_path):
    target = tmp_path/"completed"
    shutil.copytree(resumed_smoke, target)
    original = (target/"report.json").read_bytes()
    (target/"unexpected.txt").write_text("external change")
    with pytest.raises(ValueError, match="sealed|changed"):
        tool.run(target, smoke=True, resume=True)
    assert (target/"report.json").read_bytes() == original


def test_completed_marker_is_atomic_and_never_replaced(tmp_path):
    target = tmp_path/"record.json"
    tool.atomic_json(target, dict(value=1))
    with pytest.raises(FileExistsError): tool.atomic_json(target, dict(value=2))
    assert json.loads(target.read_text()) == dict(value=1)


def test_session_is_registered_only_after_started_metadata_is_atomic(tmp_path, monkeypatch):
    (tmp_path/"sessions").mkdir()
    original = tool.atomic_json
    def interrupt(*args, **kwargs): raise OSError("interrupted registration")
    monkeypatch.setattr(tool, "atomic_json", interrupt)
    cfg = runtime.configuration(True)
    with pytest.raises(OSError): tool.start_session(tmp_path, 0, cfg, 0)
    assert tool.session_history(tmp_path, cfg) == []
    monkeypatch.setattr(tool, "atomic_json", original)
    tool.start_session(tmp_path, 0, cfg, 0)
    history = tool.session_history(tmp_path, cfg)
    assert len(history) == 1 and not history[0]["closed"] and history[0]["elapsed_seconds"] is None


@pytest.mark.parametrize("mutation", ["packet", "summary", "source", "session", "duplicate_marker", "record_metrics"])
def test_tampered_records_or_provenance_fail_after_hash_repair(resumed_smoke, tmp_path, mutation):
    target = tmp_path/"batch"
    shutil.copytree(resumed_smoke, target)
    if mutation == "summary":
        report = json.loads((target/"report.json").read_text())
        report["analysis"]["mechanics"]["margin_held_gates"] += 1
        tool.atomic_json(target/"report.json", report, replace=True)
    elif mutation == "source":
        manifest = json.loads((target/"manifest.json").read_text())
        manifest["source_sha256"].pop(next(iter(manifest["source_sha256"])))
        tool.atomic_json(target/"manifest.json", manifest, replace=True)
    elif mutation == "session":
        path = target/"sessions/session_0000/started.json"
        data = json.loads(path.read_text()); data["cap_seconds"] += 1
        tool.atomic_json(path, data, replace=True)
    else:
        marker = next((target/"sessions/session_0000").glob("record_*.json"))
        row = json.loads(marker.read_text())
        if mutation == "duplicate_marker":
            shutil.copyfile(marker, target/"sessions/session_0001"/marker.name)
        elif mutation == "record_metrics":
            row["measurements"]["80"]["completed_trips"] += 1
            tool.atomic_json(marker, row, replace=True)
        else:
            trace_path = target/row["trace"]
            trace = tool.read_trace(trace_path)
            trace[0]["sensing"]["source_tick"] = None
            trace_path.unlink()
            tool.save_trace(trace_path, trace)
            row["trace_sha256"] = tool.file_hash(trace_path)
            row["semantic_trace_sha256"] = tool.digest(trace)
            tool.atomic_json(marker, row, replace=True)
    with pytest.raises(ValueError): tool.verify(target)


def test_automatic_continuation_only_handles_its_explicit_session_budget(tmp_path, monkeypatch):
    calls = []
    def run(output, smoke, mechanics, resume):
        calls.append(resume)
        if len(calls) == 1: raise tool.SessionBudgetExceeded("cap")
        return dict(complete=True)
    monkeypatch.setattr(tool, "run", run)
    monkeypatch.setattr(tool, "session_history", lambda *args: [dict(closed=True)])
    assert tool.collect(tmp_path)["complete"] and calls == [False, True]
    def fail(*args): raise ValueError("Sensor corruption")
    monkeypatch.setattr(tool, "run", fail)
    with pytest.raises(ValueError, match="corruption"): tool.collect(tmp_path)
