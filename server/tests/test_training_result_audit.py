"""Artifact audit tests use tiny inert checkpoints; no training or torch loading."""
import hashlib
import json

import pytest

from research.audits.audit_training_results import audit_run


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def run(tmp_path):
    manifest = {"test_access": False, "arguments": {"seed": 101},
                "selection_controller": "d3qn_shield", "validation_scenarios": {"val": "hash"},
                "validation_seeds": [21001], "validation_faults": [{"name": "clean"}]}
    write(tmp_path / "manifest.json", manifest)
    checkpoint = tmp_path / "checkpoint_warmup.pt"
    checkpoint.write_bytes(b"inert checkpoint")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    row = {"scenario": "val", "seed": 21001, "fault": "clean", "controller": "d3qn_shield",
           "delay": 12., "p95": 30., "throughput": 40, "conflicts": 0,
           "clearance_violations": 0, "starvations": 0,
           "checkpoint_hash": digest, "arrivals_hash": "arrivals"}
    write(tmp_path / "validation_warmup.json", {"complete": True, "score": 12.,
          "selection_controller": "d3qn_shield", "rows": [row]})
    selection = {"path": str(checkpoint), "sha256": digest, "score": 12.,
                 "evaluation_controller": "d3qn_shield"}
    write(tmp_path / "selection.json", selection)
    write(tmp_path / "summary.json", {"best": selection, "training_seed": 101,
          "stop_reason": "wall_clock_budget", "episodes_completed": 22})
    return tmp_path


def test_budget_stop_with_incomplete_unselected_candidate_is_valid(run):
    write(run / "validation_50.json", {"complete": False, "score": None, "rows": []})
    report = audit_run(run)
    assert report["integrity_checks_passed"]
    assert report["incomplete_validation"] == ["50"]
    assert report["delay_saved_from_warmup"] == 0
    assert not report["publication_ready"]


@pytest.mark.parametrize("defect", ["duplicate", "missing", "nan", "hash", "score", "arrivals"])
def test_corrupted_validation_fails_closed(run, defect):
    path = run / "validation_warmup.json"
    data = json.loads(path.read_text())
    if defect == "duplicate":
        data["rows"] *= 2
    elif defect == "missing":
        data["rows"] = []
    elif defect == "nan":
        data["rows"][0]["delay"] = float("nan")
    elif defect == "hash":
        data["rows"][0]["checkpoint_hash"] = "wrong"
    elif defect == "score":
        data["score"] = 1.
    else:
        data["rows"].append({**data["rows"][0], "controller": "max_pressure", "arrivals_hash": "different"})
    write(path, data)
    with pytest.raises(ValueError):
        audit_run(run)


def test_selected_checkpoint_not_minimum_fails(run):
    original = json.loads((run / "validation_warmup.json").read_text())
    (run / "checkpoint_50.pt").write_bytes((run / "checkpoint_warmup.pt").read_bytes())
    original["score"] = original["rows"][0]["delay"] = 10.
    write(run / "validation_50.json", original)
    with pytest.raises(ValueError, match="first validation minimum"):
        audit_run(run)


def test_changed_checkpoint_bytes_fail(run):
    (run / "checkpoint_warmup.pt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        audit_run(run)


def test_completed_run_cannot_omit_scheduled_candidates(run):
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["arguments"].update(episodes=100, validate_every=50)
    write(run / "manifest.json", manifest)
    summary = json.loads((run / "summary.json").read_text())
    summary.update(stop_reason="completed", episodes_completed=100)
    write(run / "summary.json", summary)
    with pytest.raises(ValueError, match="missing scheduled validations"):
        audit_run(run)
