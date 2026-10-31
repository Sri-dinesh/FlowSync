"""Arithmetic and export guards use synthetic metrics, not extra traffic samples."""
from copy import deepcopy
from decimal import Decimal, localcontext
from itertools import product
import json

import pytest

from research.analysis.sumo_sensing_metrics import MEASURES, summarize
from research.evidence import export_sumo_sensing as tool
from research.experiments.sumo_sensing import plans


def numeric_fixture():
    frozen, rows = plans(), []
    for index, plan in enumerate(frozen):
        for controller in tool.CONTROLLERS:
            for fault in tool.FAULTS:
                shift = 0 if controller == "fixed" else dict(clean=0, delay2s=1, miss30=2, delay2s_miss30=5)[fault]
                value = 10 + index + dict(max_pressure=0, halted=2, fixed=5)[controller] + shift
                metrics = dict(zip(MEASURES, (float(value), float(value+10), 150-value)))
                metrics.update(max_accumulated_wait_s=value+20, final_entry_backlog=2, switch_onsets=10)
                rows.append(dict(seed=plan["seed"], family=plan["family"], controller=controller,
                                 fault=fault, repeat=0, metrics=metrics))
    return rows, frozen, summarize(rows, frozen, 1)


def test_decimal_enumeration_matches_all_64_ordered_seed_draws():
    frozen = plans()
    values = {p["seed"]: Decimal(i*i) for i, p in enumerate(frozen)}
    groups = [[p["seed"] for p in frozen if p["family"] == family] for family in sorted({p["family"] for p in frozen})]
    with localcontext() as context:
        context.prec = 50
        draws = sorted(sum(values[s] for pair in draw for s in pair)/6
                       for draw in product(*(list(product(group, repeat=2)) for group in groups)))
        expected = []
        for probability in (Decimal(".025"), Decimal(".975")):
            position = probability*63
            index = int(position)
            expected.append(draws[index]+(draws[index+1]-draws[index])*(position-index))
        assert tool.interval(values, frozen) == tuple(expected)


def test_all_frozen_numbers_reconstruct_with_units_and_negative_controls():
    rows, frozen, summary = numeric_fixture()
    result = tool.numeric_tables(rows, frozen, summary)
    assert len(result["arithmetic_audit"]) == 612 and len(result["contrasts"]) == 60
    assert not result["decimal_sign_differences"]
    penalty = next(r for r in result["contrasts"] if r["kind"] == "fault_minus_clean"
                   and r["controller"] == "max_pressure" and r["fault"] == "delay2s" and r["metric"] == MEASURES[0])
    assert penalty["mean"] == penalty["lower"] == penalty["upper"] == 1
    assert all(r["mean"] == 0 for r in result["contrasts"] if r["controller"] == "fixed" and r["kind"] != "pressure_saving")


@pytest.mark.parametrize("change", ["aggregate", "paired", "mean", "interval", "draws", "missing", "nonfinite"])
def test_changed_evidence_cannot_pass_independent_arithmetic(change):
    rows, frozen, summary = numeric_fixture()
    if change == "aggregate": summary["aggregate"][0][MEASURES[0]] += .01
    elif change == "paired": summary["paired_contrasts"][0][MEASURES[0]] += .01
    elif change == "mean": summary["contrasts"][0]["metrics"][MEASURES[0]]["mean"] += .01
    elif change == "interval": summary["contrasts"][0]["metrics"][MEASURES[0]]["interval"]["lower"] += .01
    elif change == "draws": summary["contrasts"][0]["metrics"][MEASURES[0]]["interval"]["ordered_draws"] = 63
    elif change == "missing": rows.pop()
    else: rows[0]["metrics"][MEASURES[0]] = float("nan")
    with pytest.raises(ValueError):
        tool.numeric_tables(rows, frozen, summary)


def test_binary_roundoff_signs_are_disclosed_without_changing_frozen_results():
    rows, frozen, _ = numeric_fixture()
    for row in rows:
        if row["controller"] == "max_pressure":
            row["metrics"][MEASURES[0]] = dict(clean=.1, delay2s=.2, miss30=.2, delay2s_miss30=.3)[row["fault"]]
    summary = summarize(rows, frozen, 1)
    result = tool.numeric_tables(rows, frozen, summary)
    mismatch = next(r for r in result["decimal_sign_differences"] if r["controller"] == "max_pressure" and r["metric"] == MEASURES[0])
    assert mismatch["exact_decimal_signs"]["zero"] == 6
    assert mismatch["frozen_float_signs"]["negative"] == 6
    original = next(r for r in result["contrasts"] if r["kind"] == "factorial_interaction"
                    and r["controller"] == "max_pressure" and r["metric"] == MEASURES[0])
    assert original["negative"] == 6 and original["mean"] < 0


@pytest.fixture
def source_paths(tmp_path):
    source, prefix, mechanics = (tmp_path/name for name in ("recovery", "prefix", "mechanics"))
    for path in (source, prefix, mechanics): path.mkdir()
    (source/"manifest.json").write_text(json.dumps(dict(prefix_directory=str(prefix))))
    (prefix/"manifest.json").write_text(json.dumps(dict(mechanics=dict(directory=str(mechanics)))))
    return source, prefix, mechanics


def test_existing_output_is_preserved_before_any_verification(tmp_path, monkeypatch):
    output = tmp_path/"existing"
    output.mkdir()
    sentinel = output/"keep"
    sentinel.write_text("preserve")
    monkeypatch.setattr(tool, "verify_recovery", lambda _: pytest.fail("must reject first"))
    with pytest.raises(FileExistsError): tool.export(tmp_path/"absent", output)
    assert sentinel.read_text() == "preserve"


@pytest.mark.parametrize("index", [0, 1, 2])
def test_export_cannot_be_nested_in_any_frozen_input(source_paths, monkeypatch, index):
    monkeypatch.setattr(tool, "verify_recovery", lambda _: pytest.fail("must reject before verifying"))
    with pytest.raises(ValueError, match="outside"):
        tool.export(source_paths[0], source_paths[index]/"new")
    assert not (source_paths[index]/"new").exists()


def test_failed_full_verification_does_not_create_export(source_paths, tmp_path, monkeypatch):
    def reject(_): raise ValueError("Recovery is incomplete")
    monkeypatch.setattr(tool, "verify_recovery", reject)
    output = tmp_path/"export"
    with pytest.raises(ValueError, match="incomplete"): tool.export(source_paths[0], output)
    assert not output.exists()


def test_export_verifier_reconstructs_every_csv_even_after_manifest_rehash(source_paths, tmp_path, monkeypatch):
    output = tmp_path/"export"
    output.mkdir()
    tables = {"cases": [dict(metric=1)], "contrasts": [dict(metric=2)], "exploratory_service": [dict(metric=3)]}
    numeric = dict(arithmetic_audit=[{}]*612)
    monkeypatch.setattr(tool, "build_tables", lambda _: (None, None, deepcopy(tables), numeric))
    for name, rows in tables.items(): tool.csv_write(output/(name+".csv"), rows)
    manifest = dict(complete=True, input_directories={"recovery":str(source_paths[0])},
                    input_sha256={"recovery":tool.inventory(source_paths[0], report_name="__include_every_file__")},
                    csv_rows={name:len(rows) for name, rows in tables.items()},
                    output_sha256=tool.inventory(output, report_name="manifest.json"))
    tool.write(output/"manifest.json", manifest)
    assert tool.verify(output)["verified"]
    (output/"cases.csv").write_text("metric\n9\n")
    manifest["output_sha256"] = tool.inventory(output, report_name="manifest.json")
    tool.write(output/"manifest.json", manifest)
    with pytest.raises(ValueError, match="CSV does not reconstruct"): tool.verify(output)
