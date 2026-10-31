import ast
from copy import deepcopy
import hashlib
import json
import zipfile

import pytest

from research.evidence.export_methodology import ROOT,TABLE_START,TABLE_END,check_content,compare_sources,content_table,export,expression_fingerprint,inspect,select


def fixture_catalogue(tmp_path, *, unused=False):
    source = tmp_path/"source.py"
    source.write_text('raise RuntimeError("source must never be imported")\nclass Config:\n    RATE = .99\ndef consumer():\n    return 1\n')
    ref = dict(file="source.py",scope="Config",kind="assignment",target="RATE")
    tree = ast.parse(source.read_text())
    item = dict(id="rate",source=ref,unit="dimensionless",purpose="Test source default",profiles=["test"],origin="local_engineering",
        status="declared_unused" if unused else "active",justification="Fixture, no calibration claim",override_notes="Explicit override",references=[],
        reviewed_ast_sha256=expression_fingerprint(select(tree,ref)))
    if unused:
        consumer = dict(file="source.py",scope="consumer",kind="symbol")
        item["consumers"] = [dict(source=consumer,reviewed_ast_sha256=expression_fingerprint(select(tree,consumer)))]
    catalogue = dict(schema_version="methodology_v1",profiles={"test":"Fixture"},references={},parameters=[item],methods=[],
        open_evidence_requirements=["No external validation"])
    path = tmp_path/"catalogue.json"
    path.write_text(json.dumps(catalogue))
    return source,path,catalogue


def test_source_defaults_are_read_without_importing_and_numbers_require_review(tmp_path):
    source,path,_ = fixture_catalogue(tmp_path)
    first = inspect(tmp_path,path.name)
    assert first["structural_integrity_passed"] and first["parameters"][0]["value"] == .99
    source.write_text("# A comment changes line positions only\n"+source.read_text())
    assert inspect(tmp_path,path.name)["structural_integrity_passed"]
    source.write_text(source.read_text().replace(".99",".98"))
    changed = inspect(tmp_path,path.name)
    assert not changed["structural_integrity_passed"] and changed["parameters"][0]["value"] == .98
    assert any("Unreviewed source" in issue for issue in changed["issues"])


def test_unchanged_unused_declaration_cannot_hide_new_consumer_use(tmp_path):
    source,path,_ = fixture_catalogue(tmp_path,unused=True)
    assert inspect(tmp_path,path.name)["structural_integrity_passed"]
    source.write_text(source.read_text().replace("return 1","return Config.RATE"))
    report = inspect(tmp_path,path.name)
    assert not report["structural_integrity_passed"]
    assert report["parameters"][0]["value"] == .99
    assert any("consumer/activity" in issue for issue in report["issues"])


@pytest.mark.parametrize("mutation",["missing_unit","missing_basis","duplicate","unknown_profile","ambiguous","path_escape"])
def test_incomplete_or_ambiguous_review_metadata_fails(tmp_path,mutation):
    source,path,catalogue = fixture_catalogue(tmp_path)
    item = catalogue["parameters"][0]
    if mutation == "missing_unit": item.pop("unit")
    elif mutation == "missing_basis": item.pop("justification")
    elif mutation == "duplicate": catalogue["parameters"].append(deepcopy(item))
    elif mutation == "unknown_profile": item["profiles"] = ["not_a_runtime"]
    elif mutation == "ambiguous": source.write_text(source.read_text().replace("RATE = .99","RATE = .99\n    RATE = .99"))
    else: item["source"]["file"] = "../outside.py"
    path.write_text(json.dumps(catalogue))
    assert not inspect(tmp_path,path.name)["structural_integrity_passed"]


def test_dynamic_default_is_not_evaluated_and_none_is_distinct(tmp_path):
    source,path,catalogue = fixture_catalogue(tmp_path)
    source.write_text(source.read_text().replace("RATE = .99","RATE = read_secret_or_open_model()"))
    item = catalogue["parameters"][0]
    item["reviewed_ast_sha256"] = expression_fingerprint(select(ast.parse(source.read_text()),item["source"]))
    path.write_text(json.dumps(catalogue))
    row = inspect(tmp_path,path.name)["parameters"][0]
    assert row["resolution"] == "dynamic" and row["value"] is None
    assert "read_secret" in row["expression"]


def test_documented_parameter_table_cannot_silently_drift(tmp_path):
    _,path,_ = fixture_catalogue(tmp_path)
    report = inspect(tmp_path,path.name)
    document = tmp_path/"CONTENT.md"
    document.write_text(TABLE_START+"\n"+content_table(report)+"\n"+TABLE_END)
    assert not check_content(report,document)
    document.write_text(document.read_text().replace("0.99","0.98"))
    assert check_content(report,document)


def test_real_catalogue_exports_sources_not_measurement_or_production_certification(tmp_path):
    report = inspect()
    assert report["structural_integrity_passed"],report["issues"]
    assert not report["production_certified"] and not report["field_validation_established"] and not report["algorithmic_novelty_established"]
    assert next(p for p in report["parameters"] if p["id"] == "learning.gamma")["value"] == .99
    assert next(p for p in report["parameters"] if p["id"] == "network.feature_layer")["resolution"] == "architecture_spec"
    target = tmp_path/"export"
    export(report,target)
    assert (target/"parameters.csv").exists()
    with zipfile.ZipFile(target/"source_snapshot.zip") as archive:
        assert not any(name.endswith((".env",".pt",".pth")) for name in archive.namelist())
    with pytest.raises(FileExistsError):
        export(report,target)


def test_historical_hash_comparison_is_read_only_and_rejects_external_paths(tmp_path):
    source = tmp_path/"module.py"
    source.write_text("VALUE = 1\n")
    manifest = tmp_path/"manifest.json"
    manifest.write_text(json.dumps(dict(source_hashes={"module.py":hashlib.sha256(source.read_bytes()).hexdigest()})))
    assert compare_sources(tmp_path,manifest)["recorded_sources_match"]
    source.write_text("VALUE = 2\n")
    before = source.read_bytes(),manifest.read_bytes()
    assert not compare_sources(tmp_path,manifest)["recorded_sources_match"]
    assert (source.read_bytes(),manifest.read_bytes()) == before
    manifest.write_text(json.dumps(dict(source_hashes={"../outside.py":"0"*64})))
    with pytest.raises(ValueError,match="leaves"):
        compare_sources(tmp_path,manifest)
