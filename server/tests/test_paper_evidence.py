"""Paper output must be reproducible evidence, never historical literal arrays."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from research import build_paper_evidence as paper


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    rows = [dict(label=label, scenario_id="test_fixture", condition="clean", seed=81001,
                 training_seed=train, checkpoint_hash="weights" if train else "",
                 scenario_hash="scenario", safety_samples=10, num_steps=10, avg_delay=delay,
                 p95_delay=30., total_vehicles_passed=5, executed_conflict_violations=0,
                 executed_clearance_violations=0, arrival_trace_hash="arrivals")
            for label, train, delay in (("d3qn_shield_seed101", 101, 12.),
                                         ("max_pressure_shield", None, 11.))]
    source = b"# frozen simulation source\n"
    manifest = dict(matched_shield=True, planned_runs=2,
        choices=[dict(training_seed=101, sha256="weights")],
        scenario_hashes={"test_fixture": "scenario"},
        source_hashes={"fixture.py": hashlib.sha256(source).hexdigest()},
        jobs=[dict(label=r["label"], scenario_path="test_fixture.yaml", condition="clean",
                   seed=81001, training_seed=r["training_seed"]) for r in rows])
    (tmp_path / "protocol.md").write_text("Frozen protocol")
    manifest["protocol_sha256"] = paper.sha(tmp_path / "protocol.md")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "report.json").write_text('{"fixture": true}')
    (tmp_path / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (tmp_path / "postprocessing_source.py").write_text("# original exporter")
    with zipfile.ZipFile(tmp_path / "source_snapshot.zip", "w") as archive:
        archive.writestr("fixture.py", source)
    refresh_hashes(tmp_path)
    monkeypatch.setattr(paper, "summarize", lambda rows, matched_shield: {"fixture": True})
    return tmp_path


def refresh_hashes(directory):
    provenance = dict(input_sha256={name: paper.sha(directory / name)
        for name in ("manifest.json", "report.json", "runs.jsonl")},
        exporter_sha256=paper.sha(directory / "postprocessing_source.py"))
    (directory / "postprocessing_manifest.json").write_text(json.dumps(provenance))


def test_valid_bundle_is_read_only(bundle):
    before = {p.name: paper.sha(p) for p in bundle.iterdir()}
    _, _, rows = paper.load_evidence(bundle)
    assert len(rows) == 2
    assert before == {p.name: paper.sha(p) for p in bundle.iterdir()}


def test_tampered_report_rejected(bundle):
    (bundle / "report.json").write_text('{"invented_win": true}')
    with pytest.raises(ValueError, match="input changed"):
        paper.load_evidence(bundle)


@pytest.mark.parametrize("field,value,match", [
    ("checkpoint_hash", "wrong", "Checkpoint"),
    ("scenario_hash", "wrong", "Scenario"),
    ("training_seed", 202, "replicate"),
    ("safety_samples", 0, "coverage"),
    ("avg_delay", float("nan"), "Invalid metric"),
    ("p95_delay", -1., "Invalid metric"),
    ("arrival_trace_hash", "wrong", "arrival"),
])
def test_reject_bad_rows_even_with_refreshed_file_hashes(bundle, field, value, match):
    rows = [json.loads(line) for line in (bundle / "runs.jsonl").read_text().splitlines()]
    rows[0][field] = value
    (bundle / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    refresh_hashes(bundle)
    with pytest.raises(ValueError, match=match):
        paper.load_evidence(bundle)


def test_reject_duplicate_cells(bundle):
    row = (bundle / "runs.jsonl").read_text().splitlines()[0]
    (bundle / "runs.jsonl").write_text(row + "\n" + row)
    refresh_hashes(bundle)
    with pytest.raises(ValueError, match="planned cells"):
        paper.load_evidence(bundle)


def test_reject_unreproducible_statistics(bundle, monkeypatch):
    monkeypatch.setattr(paper, "summarize", lambda *args, **kwargs: {"different": True})
    with pytest.raises(ValueError, match="does not reproduce"):
        paper.load_evidence(bundle)


def test_reject_modified_source_archive(bundle):
    with zipfile.ZipFile(bundle / "source_snapshot.zip", "w") as archive:
        archive.writestr("fixture.py", "different implementation")
    with pytest.raises(ValueError, match="source mismatch"):
        paper.load_evidence(bundle)


def test_tables_keep_metric_and_scope_explicit(tmp_path):
    summary = [dict(controller="d3qn_shield", mean_delay_s=12.,
                    mean_within_run_p95_s=40., runs=600)]
    contrast = dict(mean_delay_saved_s=-.2, bootstrap_ci95_s=[-.9, .4], metric="p95_delay")
    paper.write_tables(tmp_path, summary, {"comparisons": {
        "d3qn_shield_vs_max_pressure_shield_p95_delay": contrast,
        "clean_d3qn_vs_fixed": {k: v for k, v in contrast.items() if k != "metric"}}})
    csv = (tmp_path / "contrasts.csv").read_text()
    assert "all condition cells,p95_delay" in csv
    assert "clean only,avg_delay" in csv
    assert "not pooled percentiles" in (tmp_path / "controllers.tex").read_text()


def test_existing_output_never_overwritten(tmp_path):
    with pytest.raises(FileExistsError):
        paper.build(tmp_path / "unused", tmp_path)


def test_legacy_script_cannot_regenerate_historical_figures(tmp_path):
    script = Path(__file__).resolve().parents[2] / "research/analysis/generate_paper_figures.py"
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "No figures written" in result.stderr
    assert not list(tmp_path.glob("*.png"))
