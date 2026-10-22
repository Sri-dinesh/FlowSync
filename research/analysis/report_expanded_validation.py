#!/usr/bin/env python3
"""Audit a frozen parent/candidate validation screen and report every replicate."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from research.evaluation.evaluate_replicates import crossed_bootstrap

BASELINES = ("fixed", "actuated", "greedy", "max_pressure", "max_pressure_shield")
TRAINING_SEEDS = (101, 202, 303)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_panel(config, rows):
    expected = set(itertools.product(config["scenario_hashes"], config["seeds"],
                                    [f["name"] for f in config["faults"]], config["variants"]))
    actual = [(r["scenario"], r["seed"], r["fault"], r["controller"]) for r in rows]
    if config["split"] != "validation" or len(rows) != config["planned_runs"] or len(rows) != len(expected) or set(actual) != expected:
        raise ValueError("Incomplete, duplicate or non-validation panel")
    for r in rows:
        if r["scenario_hash"] != config["scenario_hashes"][r["scenario"]]:
            raise ValueError("Scenario provenance mismatch")
        if r["controller"] in config["variant_checkpoint_hashes"] and r["checkpoint_hash"] != config["variant_checkpoint_hashes"][r["controller"]]:
            raise ValueError("Checkpoint provenance mismatch")
        if r["safety_samples"] != r["expected_safety_samples"] or r["safety_samples"] <= 0:
            raise ValueError("Missing signal-audit coverage")
        metrics = [r[k] for k in ("delay", "p95", "throughput", "signal_violations")]
        if not np.isfinite(metrics).all() or min(metrics) < 0:
            raise ValueError("Invalid performance measurements")


def metrics(rows):
    return dict(runs=len(rows), mean_delay=float(np.mean([r["delay"] for r in rows])),
                mean_within_run_p95=float(np.mean([r["p95"] for r in rows])),
                mean_throughput=float(np.mean([r["throughput"] for r in rows])),
                signal_violations=sum(r["signal_violations"] for r in rows),
                shield_interventions=sum(r["shield_interventions"] for r in rows))


def report(directory):
    panels, configuration, hashes, arrivals = {}, None, {}, {}
    for panel in ("baselines", *(f"seed_{s}" for s in TRAINING_SEEDS)):
        base = directory/panel
        config = json.loads((base/"configuration.json").read_text())
        rows = [json.loads(line) for line in (base/"runs.jsonl").read_text().splitlines()]
        validate_panel(config, rows)
        wanted = set(BASELINES) if panel == "baselines" else {"candidate", "parent"}
        if set(config["variants"]) != wanted:
            raise ValueError("Unexpected comparison panel")
        if configuration is None:
            configuration = config
        for key in ("seeds", "faults", "scenario_hashes", "source_hashes"):
            if config[key] != configuration[key]:
                raise ValueError(f"Panels disagree on {key}")
        with zipfile.ZipFile(base/"source_snapshot.zip") as archive:
            if any(hashlib.sha256(archive.read(k)).hexdigest() != v for k, v in config["source_hashes"].items()):
                raise ValueError("Frozen source archive mismatch")
        for r in rows:
            key = (r["scenario"], r["seed"])
            if not r["arrivals_hash"] or arrivals.setdefault(key, r["arrivals_hash"]) != r["arrivals_hash"]:
                raise ValueError("Unpaired arrivals across panels")
        panels[panel] = rows
        for name in ("configuration.json", "runs.jsonl", "source_snapshot.zip"):
            hashes[f"{panel}/{name}"] = digest(base/name)
    conditions = list(itertools.product(sorted(configuration["scenario_hashes"]), [f["name"] for f in configuration["faults"]]))
    lookup = {(panel, r["controller"], r["scenario"], r["fault"], r["seed"]): r
              for panel, rows in panels.items() for r in rows}
    comparisons = {}
    for reference in ("parent", *BASELINES):
        for metric in ("delay", "p95"):
            differences = [[[lookup[(f"seed_{train}" if reference == "parent" else "baselines", reference, sc, fault, seed)][metric]
                              - lookup[(f"seed_{train}", "candidate", sc, fault, seed)][metric]
                              for sc, fault in conditions] for seed in configuration["seeds"]] for train in TRAINING_SEEDS]
            comparisons[f"candidate_vs_{reference}_{metric}"] = crossed_bootstrap(differences)
    all_rows = [r for rows in panels.values() for r in rows]
    aggregate = {name: metrics([r for r in all_rows if r["controller"] == name])
                 for name in ("candidate", "parent", *BASELINES)}
    return dict(scope="Additional development validation; no independent final-test superiority claim",
        publication_ready=False, traffic_seeds=configuration["seeds"], training_seeds=TRAINING_SEEDS,
        runs=len(all_rows), safety_samples=sum(r["safety_samples"] for r in all_rows),
        signal_violations=sum(r["signal_violations"] for r in all_rows), integrity_checks_passed=True,
        aggregate=aggregate, comparisons=comparisons,
        by_training_seed={s: {label: metrics([r for r in panels[f"seed_{s}"] if r["controller"] == label])
                             for label in ("candidate", "parent")} for s in TRAINING_SEEDS},
        by_fault={f["name"]: {name: metrics([r for r in all_rows if r["controller"] == name and r["fault"] == f["name"]])
                              for name in aggregate} for f in configuration["faults"]},
        input_sha256=hashes, postprocessor_sha256=digest(Path(__file__)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--save", action="store_true", help="Exclusively create report and preserve its actual postprocessor")
    args = p.parse_args()
    data = report(args.directory)
    if args.save:
        if any((args.directory/name).exists() for name in ("report.json", "postprocessor.py")):
            raise FileExistsError("Report artifacts already exist; refusing overwrite")
        with (args.directory/"postprocessor.py").open("xb") as stream:
            stream.write(Path(__file__).read_bytes())
        with (args.directory/"report.json").open("x") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
    print(json.dumps(data, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
