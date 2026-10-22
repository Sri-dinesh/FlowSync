#!/usr/bin/env python3
"""Export auditable simulation findings without converting them into readiness claims."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics


def controller_label(row):
    """Use intervention labels, not the shared FlowSync-UQ implementation name."""
    label = row.get("label", row["controller_name"])
    train = row.get("training_seed")
    suffix = f"_seed{train}"
    return label.removesuffix(suffix) if train is not None else label


def controller_summary(rows, clean_only=False):
    selected = [r for r in rows if not clean_only or r["condition"] == "clean"]
    summaries = []
    for controller in sorted({controller_label(r) for r in selected}):
        subset = [r for r in selected if controller_label(r) == controller]
        summaries.append({"controller": controller, "runs": len(subset),
                          "mean_delay_s": statistics.mean(r["avg_delay"] for r in subset),
                          "mean_within_run_p95_s": statistics.mean(r["p95_delay"] for r in subset),
                          "mean_vehicles_passed": statistics.mean(r["total_vehicles_passed"] for r in subset)})
    return summaries


def export(run_dir):
    report = json.loads((run_dir / "report.json").read_text())
    manifest = json.loads((run_dir / "manifest.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "runs.jsonl").read_text().splitlines()]
    if len(rows) != manifest["planned_runs"]:
        raise ValueError("Cannot export an incomplete evaluation as complete evidence")
    if len({(r["label"], r["scenario_id"], r["condition"], r["seed"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate evaluation cells")
    if any(r["safety_samples"] != r["num_steps"] for r in rows):
        raise ValueError("Incomplete executed-signal audit coverage")
    safety = sum(r["executed_conflict_violations"] + r["executed_clearance_violations"] for r in rows)
    summaries = controller_summary(rows, clean_only=True)
    all_summaries = controller_summary(rows)
    with (run_dir / "clean_controller_summary.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    with (run_dir / "all_condition_controller_summary.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(all_summaries[0]))
        writer.writeheader()
        writer.writerows(all_summaries)
    with (run_dir / "condition_means.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report["condition_means"][0]))
        writer.writeheader()
        writer.writerows(report["condition_means"])
    matched = manifest.get("matched_shield", False)
    primary_summaries = all_summaries if matched else summaries
    primary_scope = "all ten condition cells; matched shield comparison" if matched else "seven clean scenarios"
    lines = ["# Frozen simulation evaluation — evidence, not deployment certification", "",
             f"Completed {len(rows):,} planned runs; {len(manifest['choices'])} independent training seeds; "
             f"{len(manifest['traffic_seeds'])} paired traffic seeds.", "",
             f"## Primary: {primary_scope}", "",
             "| Controller | Mean delay (s) | Mean within-run p95 (s) | Runs |",
             "| --- | ---: | ---: | ---: |"]
    for item in primary_summaries:
        lines.append(f"| {item['controller']} | {item['mean_delay_s']:.3f} | {item['mean_within_run_p95_s']:.3f} | {item['runs']} |")
    lines += ["", "Learning methods aggregate ALL independent training runs, not the winning seed.",
              "Delay is accumulated vehicle waiting through the finite simulation horizon, including "
              "vehicles still present/backlogged. It is not completed-trip travel time.", "",
              "## Paired differences", "",
              "Positive saved seconds favors the proposed method; negative favors the baseline.", "",
              "| Comparison | Mean saved (s) | Crossed bootstrap 95% interval (s) |",
              "| --- | ---: | --- |"]
    for name, item in report["comparisons"].items():
        if name.startswith("clean_") or (matched and "metric" in item):
            lo, hi = item["bootstrap_ci95_s"]
            lines.append(f"| {name} | {item['mean_delay_saved_s']:.3f} | [{lo:.3f}, {hi:.3f}] |")
    lines += ["", "Intervals resample training runs and paired traffic seeds; scenarios remain fixed. "
              "These are descriptive intervals with few training replicates, not multiplicity-adjusted hypothesis tests.",
              "", "## Integrity and limits", "",
              f"- Matched traffic arrival traces: {report['arrival_traces_match']}.",
              f"- Measured simulated signal conflict/clearance violations: {safety}.",
              "- This does not measure collisions, pedestrian safety or real hardware behavior.",
              "- Sensor errors are synthetic count faults, not validated camera detections.",
              "- The test scenario templates were previously inspected; these traffic seeds were fresh.",
              "- Checkpoint selection used validation only. A shield removal intervention uses the same "
              "checkpoint, not a separately optimized unshielded policy. This is not a matched training-recipe ablation.",
              "- Shield-only D3QN and full UQ are separate intervention labels even though they share "
              "an internal implementation. Average within-run p95 is not a pooled vehicle percentile.",
              "- Inspect every condition in condition_means.csv, including losses and out-of-distribution cases.",
              "- Publication/deployment readiness is NOT established automatically by this report.", "",
              "## Frozen checkpoints", ""]
    for item in manifest["choices"]:
        lines += [f"- Training seed {item['training_seed']}: `{item['path']}`; SHA-256 `{item['sha256']}`."]
    lines += ["", f"Exporter SHA-256: `{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}`.", ""]
    with (run_dir / "EVIDENCE_SUMMARY.md").open("x") as stream:
        stream.write("\n".join(lines))
    # Preserve the actual postprocessor separately from the frozen simulation
    # archive: reporting fixes must not rewrite the simulation's source snapshot.
    exporter_bytes = Path(__file__).read_bytes()
    with (run_dir / "postprocessing_source.py").open("xb") as stream:
        stream.write(exporter_bytes)
    provenance = {"exporter_sha256": hashlib.sha256(exporter_bytes).hexdigest(),
                  "input_sha256": {name: hashlib.sha256((run_dir/name).read_bytes()).hexdigest()
                                   for name in ("manifest.json", "report.json", "runs.jsonl")},
                  "grouping": "intervention label with training-seed suffix removed; never implementation class",
                  "simulation_snapshot_modified": False}
    with (run_dir / "postprocessing_manifest.json").open("x") as stream:
        json.dump(provenance, stream, indent=2)
    print(run_dir / "EVIDENCE_SUMMARY.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    export(parser.parse_args().run_dir)
