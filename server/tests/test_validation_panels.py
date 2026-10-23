import pytest
import copy

from research.evaluation.evaluate_validation import baseline_variants, policy_pair_variants
from research.analysis.report_expanded_validation import validate_panel


def test_policy_pair_has_identical_protections_and_explicit_parent():
    variants = policy_pair_variants("parent.pt")
    assert set(variants) == {"candidate", "parent"}
    for name, options in variants.values():
        assert name == "flowsync_uq"
        assert options["enable_shield"] and not options["enable_fallback"]
    assert variants["parent"][1]["checkpoint_path"] == "parent.pt"
    assert "checkpoint_path" not in variants["candidate"][1]
    with pytest.raises(ValueError):
        policy_pair_variants(None)


def test_baselines_include_raw_and_matched_shield_max_pressure():
    variants = baseline_variants()
    assert set(variants) == {"fixed", "actuated", "greedy", "max_pressure", "max_pressure_shield"}
    assert variants["max_pressure"] == ("max_pressure", {})
    assert variants["max_pressure_shield"] == ("max_pressure", {"apply_shield": True})


@pytest.mark.parametrize("mutation", ["none", "duplicate", "missing", "checkpoint", "scenario", "nan", "coverage", "test"])
def test_report_panel_rejects_invalid_evidence(mutation):
    config = dict(split="validation", scenario_hashes={"val_fixture": "scenario"}, seeds=[24001],
                  faults=[dict(name="clean")], variants={"candidate": None}, planned_runs=1,
                  variant_checkpoint_hashes={"candidate": "checkpoint"})
    rows = [dict(scenario="val_fixture", scenario_hash="scenario", seed=24001, fault="clean",
                 controller="candidate", checkpoint_hash="checkpoint", safety_samples=1200,
                 expected_safety_samples=1200, delay=10., p95=30., throughput=80, signal_violations=0)]
    if mutation == "none":
        validate_panel(config, rows)
        return
    if mutation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "missing":
        rows.clear()
    elif mutation == "checkpoint":
        rows[0]["checkpoint_hash"] = "wrong"
    elif mutation == "scenario":
        rows[0]["scenario_hash"] = "wrong"
    elif mutation == "nan":
        rows[0]["delay"] = float("nan")
    elif mutation == "coverage":
        rows[0]["safety_samples"] = 1199
    else:
        config["split"] = "test"
    with pytest.raises(ValueError):
        validate_panel(config, rows)
