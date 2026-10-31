"""Recovery orchestration uses synthetic rows; no native SUMO traffic is run here."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from research.pilots import recover_sumo_sensing as tool
from research.pilots import run_sumo_sensing_panel as original
from server.tests.test_sumo_sensing import trace_fixture
from server.tests.test_sumo_sensing_panel import saved_panel


@pytest.fixture(scope="module")
def recovery_fixture(saved_panel, tmp_path_factory, request):
    root = tmp_path_factory.mktemp("synthetic_sensing_recovery")
    patch = pytest.MonkeyPatch()
    request.addfinalizer(patch.undo)
    original_configuration, original_plans = tool.configuration, tool.plans
    real_verify = original.verify
    smoke_verification = real_verify(saved_panel)
    def verified(directory):
        # The shared smoke is immutable; mutated prefixes and full collections still replay.
        return deepcopy(smoke_verification) if Path(directory) == saved_panel else real_verify(directory)
    patch.setattr(tool, "verify_collection", verified)
    patch.setattr(original, "verify", verified)
    small = [{**p, "steps": 180, "schedule": [[0, "n", f"fixture_{p['seed']}"]]} for p in original_plans()]
    def configuration(smoke=False):
        return original_configuration(True) if smoke else {**original_configuration(), "steps": 180}
    def plans(smoke=False):
        return original_plans(True) if smoke else deepcopy(small)
    for module in (tool, original):
        patch.setattr(module, "configuration", configuration)
        patch.setattr(module, "plans", plans)
    environment = json.loads((saved_panel / "manifest.json").read_text())["runtime"]
    patch.setattr(tool, "runtime", lambda: ({"sumo": "synthetic", "netconvert": "synthetic"}, environment))
    patch.setattr(tool.subprocess, "check_output", lambda command, **kwargs: "0" * 40 if "rev-parse" in command else "")
    conn = SimpleNamespace(load=lambda _: None, close=lambda: None,
        trafficlight=SimpleNamespace(getControlledLinks=lambda _: [[(d + "_in_0", "out", "via")] for d in "nesw"]))
    patch.setitem(sys.modules, "traci", SimpleNamespace(start=lambda *args, **kwargs: None, getConnection=lambda _: conn))
    patch.setattr(tool, "episode", lambda conn, axes, plan, controller, fault, budget:
                  iter(trace_fixture(plan, controller, fault)))
    prefix = root / "prefix"
    prefix.mkdir()
    for name in tool.BASE_FILES:
        shutil.copyfile(saved_panel / name, prefix / name)
    manifest = json.loads((prefix / "manifest.json").read_text())
    manifest.update(configuration=configuration(), mechanics=dict(directory=str(saved_panel),
                    report_sha256=tool.file_hash(saved_panel / "report.json")))
    tool.write(prefix / "manifest.json", manifest)
    tool.write(prefix / "frozen_plans.json", plans())
    first = tool.jobs()[0]
    plan = small[0]
    trace = trace_fixture(plan, first["controller"], tool.PRESETS[0])
    name = tool.trace_name(**first)
    tool.save_trace(prefix / name, trace)
    row = dict(**first, family=plan["family"], trace=name,
               metrics=tool.validate_trace(trace, plan, first["controller"], tool.PRESETS[0], [0, 1, 0, 1]),
               semantic_trace_sha256=tool.digest(trace), requested_arrival_sha256=tool.digest(plan["schedule"]))
    (prefix / "runs.jsonl").write_text(json.dumps(row) + "\n")
    pending = tool.jobs()[1]
    interrupted = trace_fixture(plan, pending["controller"], next(f for f in tool.PRESETS if f.name == pending["fault"]))
    tool.save_trace(prefix / tool.trace_name(**pending), interrupted[:5])
    report = dict(complete=False, scientific_panel_complete=False, smoke=False, policy_promoted=False,
                  publication_ready=False, completed_runs=1, active_job=tool.jobs()[1], elapsed_seconds=900.1,
                  error="TimeoutError: Frozen sensing collection cap exceeded", output_hashes=tool.inventory(prefix))
    tool.write(prefix / "report.json", report)
    recovered = root / "recovery"
    before = tool.inventory(prefix) | {"report.json": tool.file_hash(prefix / "report.json")}
    result = tool.recover(prefix, recovered)
    assert before == tool.inventory(prefix) | {"report.json": tool.file_hash(prefix / "report.json")}
    yield SimpleNamespace(prefix=prefix, recovered=recovered, root=root, result=result)
    patch.undo()


def refresh(directory):
    report = json.loads((directory / "report.json").read_text())
    report["output_hashes"] = tool.inventory(directory)
    tool.write(directory / "report.json", report)


def test_completed_recovery_keeps_all_frozen_cells_and_explicit_budget_deviation(recovery_fixture):
    record = recovery_fixture
    checked = tool.verify(record.recovered)
    assert checked["verified"] and checked["panel_runs"] == 72
    assert checked["reused_runs"] == 1 and checked["newly_collected_runs"] == 71
    assert checked["parity_anchor_runs"] == 1
    assert checked["original_attempt_budget_met"] is False and checked["execution_budget_amended"]
    assert checked["independently_rerun_trajectories"] == 0
    assert json.loads((record.prefix / "report.json").read_text())["complete"] is False
    first = json.loads((record.prefix / "runs.jsonl").read_text())
    assert (record.prefix / first["trace"]).read_bytes() == (record.recovered / "collection" / first["trace"]).read_bytes()
    assert len(list((record.recovered / "collection").glob("trace_*.gz"))) == 72


@pytest.mark.parametrize("mutation", ["relabel", "runtime", "source", "row_identity", "row_metrics", "active_job", "missing_file", "extra_file"])
def test_prefix_corruption_is_rejected_even_after_hash_repair(recovery_fixture, tmp_path, mutation):
    prefix = tmp_path / "prefix"
    shutil.copytree(recovery_fixture.prefix, prefix)
    report = json.loads((prefix / "report.json").read_text())
    if mutation == "relabel":
        report["complete"] = True
        tool.write(prefix / "report.json", report)
    elif mutation in {"runtime", "source"}:
        manifest = json.loads((prefix / "manifest.json").read_text())
        if mutation == "runtime": manifest["runtime"]["python_version"] = "different"
        else: manifest["source_hashes"].pop(next(iter(manifest["source_hashes"])))
        tool.write(prefix / "manifest.json", manifest)
        refresh(prefix)
    elif mutation in {"row_identity", "row_metrics"}:
        row = json.loads((prefix / "runs.jsonl").read_text())
        if mutation == "row_identity": row["seed"] += 1
        else: row["metrics"]["completed_trips"] += 1
        (prefix / "runs.jsonl").write_text(json.dumps(row) + "\n")
        refresh(prefix)
    elif mutation == "active_job":
        report["active_job"] = tool.jobs()[2]
        tool.write(prefix / "report.json", report)
    elif mutation == "missing_file":
        (prefix / "frozen_plans.json").unlink()
        refresh(prefix)
    else:
        (prefix / "extra").write_text("unexpected")
        refresh(prefix)
    with pytest.raises((ValueError, FileNotFoundError)):
        tool.audit_prefix(prefix)


@pytest.mark.parametrize("mutation", ["budget", "new_count", "anchor", "reuse_bytes", "summary", "source_archive", "missing_prefix_hash"])
def test_recovery_verification_checks_lineage_and_numerics_after_rehash(recovery_fixture, tmp_path, mutation):
    output = tmp_path / "recovery"
    shutil.copytree(recovery_fixture.recovered, output)
    report = json.loads((output / "report.json").read_text())
    if mutation in {"budget", "new_count"}:
        report["recovery_elapsed_seconds" if mutation == "budget" else "new_runs"] = 601
        tool.write(output / "report.json", report)
    elif mutation == "anchor":
        target = output / "parity_anchor.jsonl.gz"
        rows = tool.read_trace(target)
        rows[0]["wait_vehicle_seconds"] = 1
        target.unlink()
        tool.save_trace(target, rows)
        refresh(output)
    elif mutation == "reuse_bytes":
        row = json.loads((recovery_fixture.prefix / "runs.jsonl").read_text())
        with (output / "collection" / row["trace"]).open("ab") as stream:
            stream.write(b"tampered gzip bytes")
        refresh(output)
    elif mutation == "summary":
        canonical = json.loads((output / "collection/report.json").read_text())
        canonical["summary"]["aggregate"][0]["completed_trips"] += 1
        tool.write(output / "collection/report.json", canonical)
        refresh(output)
    elif mutation == "source_archive":
        (output / "recovery_source_snapshot.zip").write_bytes(b"changed")
        refresh(output)
    else:
        manifest = json.loads((output / "manifest.json").read_text())
        manifest["prefix_sha256"].pop("report.json")
        tool.write(output / "manifest.json", manifest)
        refresh(output)
    with pytest.raises((ValueError, tool.zipfile.BadZipFile)):
        tool.verify(output)


def test_existing_or_nested_output_never_overwrites_evidence(recovery_fixture):
    before = tool.inventory(recovery_fixture.recovered)
    with pytest.raises(FileExistsError):
        tool.recover(recovery_fixture.prefix, recovery_fixture.recovered)
    with pytest.raises(ValueError, match="outside"):
        tool.recover(recovery_fixture.prefix, recovery_fixture.prefix / "new")
    assert before == tool.inventory(recovery_fixture.recovered)


def test_interrupted_recovery_stays_incomplete_and_preserves_original_prefix(recovery_fixture, tmp_path, monkeypatch):
    prefix = recovery_fixture.prefix
    before = tool.inventory(prefix)
    count = 0
    def stop(conn, axes, plan, controller, fault, budget):
        nonlocal count
        count += 1
        rows = trace_fixture(plan, controller, fault)
        if count == 1:
            yield from rows
        else:
            yield rows[0]
            raise TimeoutError("Recovery collection cap exceeded")
    monkeypatch.setattr(tool, "episode", stop)
    output = tmp_path / "partial_recovery"
    with pytest.raises(TimeoutError):
        tool.recover(prefix, output)
    report = json.loads((output / "report.json").read_text())
    assert report["complete"] is False and report["new_runs"] == 0
    assert report["output_hashes"] == tool.inventory(output)
    assert before == tool.inventory(prefix)
    with pytest.raises(ValueError, match="incomplete"):
        tool.verify(output)
