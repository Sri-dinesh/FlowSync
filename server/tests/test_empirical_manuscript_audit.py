import hashlib
import json
import zipfile

import pytest

from research.evidence.audit_empirical_manuscript import same_fields, verified_bundle


def bundle(tmp_path):
    (tmp_path/"rows.jsonl").write_text('{"value": 1}\n')
    source = b"archived original implementation\n"
    with zipfile.ZipFile(tmp_path/"source_snapshot.zip", "w") as archive:
        archive.writestr("old/location.py", source)
    manifest = dict(input_hashes={}, source_hashes={"old/location.py": hashlib.sha256(source).hexdigest()})
    report = dict(complete=True, smoke=False, output_hashes={
        "rows.jsonl": hashlib.sha256((tmp_path/"rows.jsonl").read_bytes()).hexdigest()})
    (tmp_path/"manifest.json").write_text(json.dumps(manifest))
    (tmp_path/"report.json").write_text(json.dumps(report))
    return manifest, report


def test_archived_source_is_verified_without_requiring_its_old_live_path(tmp_path):
    expected = bundle(tmp_path)
    assert verified_bundle(tmp_path) == expected


@pytest.mark.parametrize("mutation", ["output", "source", "incomplete", "smoke", "upstream", "traversal"])
def test_changed_or_incomplete_evidence_is_rejected(tmp_path, mutation):
    manifest, report = bundle(tmp_path)
    if mutation == "output":
        (tmp_path/"rows.jsonl").write_text('{"value": 999}\n')
    elif mutation == "source":
        manifest["source_hashes"]["old/location.py"] = "0"*64
    elif mutation == "incomplete":
        report["complete"] = False
    elif mutation == "smoke":
        report["smoke"] = True
    elif mutation == "upstream":
        manifest["input_hashes"][str(tmp_path/"rows.jsonl")] = "0"*64
    else:
        report["output_hashes"] = {"../outside": "0"*64}
    (tmp_path/"manifest.json").write_text(json.dumps(manifest))
    (tmp_path/"report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError):
        verified_bundle(tmp_path)


def test_recomputed_results_cannot_be_replaced_by_a_changed_summary():
    same_fields({"count": 5, "elapsed": 12}, {"count": 5})
    with pytest.raises(ValueError, match="count"):
        same_fields({"count": 6}, {"count": 5})
