"""Report interventions separately even when they use the same controller class."""
import csv
import hashlib
import json

import pytest

from research.evidence.export_evidence import controller_summary, export


def test_shield_only_is_not_merged_with_full_uq():
    rows = []
    for seed in (101, 202, 303):
        for label, delay in (("d3qn_shield", 8.), ("flowsync_uq", 12.)):
            rows.append({"controller_name": "flowsync_uq", "label": f"{label}_seed{seed}",
                         "training_seed": seed, "condition": "clean", "avg_delay": delay,
                         "p95_delay": delay*2, "total_vehicles_passed": 20})
    summaries = {s["controller"]: s for s in controller_summary(rows)}
    assert set(summaries) == {"d3qn_shield", "flowsync_uq"}
    assert summaries["d3qn_shield"]["mean_delay_s"] == 8
    assert summaries["flowsync_uq"]["mean_delay_s"] == 12
    assert all(s["runs"] == 3 for s in summaries.values())


def test_clean_subset_and_baseline_labels_remain_distinct():
    rows = [{"controller_name": "max_pressure", "label": "max_pressure_shield",
             "training_seed": None, "condition": condition, "avg_delay": delay,
             "p95_delay": delay*2, "total_vehicles_passed": 20}
            for condition, delay in (("clean", 10.), ("miss_30", 20.))]
    assert controller_summary(rows)[0]["mean_delay_s"] == 15
    clean = controller_summary(rows, clean_only=True)[0]
    assert clean["controller"] == "max_pressure_shield"
    assert clean["mean_delay_s"] == 10
    assert clean["runs"] == 1


def test_export_preserves_distinct_labels_and_postprocessing_provenance(tmp_path):
    rows = []
    for label, delay in (("d3qn_shield", 8.), ("flowsync_uq", 12.)):
        rows.append({"controller_name": "flowsync_uq", "label": f"{label}_seed101",
                     "training_seed": 101, "scenario_id": "test_fixture", "seed": 81001,
                     "condition": "clean", "avg_delay": delay, "p95_delay": delay*2,
                     "total_vehicles_passed": 20, "safety_samples": 100, "num_steps": 100,
                     "executed_conflict_violations": 0, "executed_clearance_violations": 0})
    (tmp_path / "runs.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    (tmp_path / "manifest.json").write_text(json.dumps({"planned_runs": 2, "matched_shield": True,
        "choices": [{"training_seed": 101, "path": "fixture.pt", "sha256": "fixture_hash"}],
        "traffic_seeds": [81001]}))
    (tmp_path / "report.json").write_text(json.dumps({"comparisons": {}, "arrival_traces_match": True,
        "condition_means": [{"scenario": "test_fixture", "condition": "clean", "label": r["label"],
                             "mean_delay": r["avg_delay"]} for r in rows]}))
    export(tmp_path)
    with (tmp_path / "all_condition_controller_summary.csv").open() as stream:
        summaries = {r["controller"]: float(r["mean_delay_s"]) for r in csv.DictReader(stream)}
    assert summaries == {"d3qn_shield": 8., "flowsync_uq": 12.}
    provenance = json.loads((tmp_path / "postprocessing_manifest.json").read_text())
    assert hashlib.sha256((tmp_path / "postprocessing_source.py").read_bytes()).hexdigest() == provenance["exporter_sha256"]
    for name, digest in provenance["input_sha256"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        export(tmp_path)
