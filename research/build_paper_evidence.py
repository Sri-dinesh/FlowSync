#!/usr/bin/env python3
"""Generate traceable paper tables/plots from a frozen matched-shield evaluation.

Read-only with respect to inputs. Outputs must go to a NEW directory. This is
postprocessing, never training, candidate selection or publication certification.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.export_evidence import controller_summary
from research.evaluate_replicates import summarize

LABELS = {
    "fixed": "Fixed", "actuated": "Actuated", "greedy": "Greedy",
    "max_pressure": "Max-Pressure", "max_pressure_shield": "Max-Pressure + shield",
    "d3qn": "D3QN", "d3qn_shield": "D3QN + shield", "flowsync_uq": "Full FlowSync-UQ",
}
CONTRASTS = {
    "d3qn_shield_vs_max_pressure_shield_avg_delay": "D3QN + shield vs MP + shield",
    "d3qn_shield_vs_d3qn_avg_delay": "Adding shield to D3QN",
    "max_pressure_shield_vs_max_pressure_avg_delay": "Adding shield to Max-Pressure",
    "flowsync_uq_vs_d3qn_shield_avg_delay": "Adding UQ fallback to D3QN + shield",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_evidence(directory):
    """Reject stale/tampered exports, missing cells and mismatched provenance."""
    manifest = json.loads((directory / "manifest.json").read_text())
    report = json.loads((directory / "report.json").read_text())
    provenance = json.loads((directory / "postprocessing_manifest.json").read_text())
    if manifest.get("matched_shield") is not True:
        raise ValueError("Requires a frozen matched-shield evaluation")
    for name in ("manifest.json", "report.json", "runs.jsonl"):
        if sha(directory / name) != provenance["input_sha256"][name]:
            raise ValueError(f"Frozen postprocessing input changed: {name}")
    if sha(directory / "postprocessing_source.py") != provenance["exporter_sha256"]:
        raise ValueError("Archived exporter hash mismatch")
    if sha(directory / "protocol.md") != manifest["protocol_sha256"]:
        raise ValueError("Frozen protocol hash mismatch")
    with zipfile.ZipFile(directory / "source_snapshot.zip") as archive:
        for name, digest in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Frozen simulation source mismatch: {name}")
    rows = [json.loads(line) for line in (directory / "runs.jsonl").read_text().splitlines()]
    jobs = {(j["label"], Path(j["scenario_path"]).stem, j["condition"], j["seed"]): j
            for j in manifest["jobs"]}
    keys = [(r["label"], r["scenario_id"], r["condition"], r["seed"]) for r in rows]
    if (len(rows) != manifest["planned_runs"] or len(jobs) != len(manifest["jobs"])
            or len(keys) != len(set(keys)) or set(keys) != set(jobs)):
        raise ValueError("Incomplete, duplicate or unexpected planned cells")
    checkpoints = {c["training_seed"]: c for c in manifest["choices"]}
    if len(checkpoints) != len(manifest["choices"]):
        raise ValueError("Duplicate training replicate")
    arrivals = {}
    for row, key in zip(rows, keys):
        if row["training_seed"] != jobs[key]["training_seed"]:
            raise ValueError("Training replicate mismatch")
        train = row["training_seed"]
        if train is not None and row["checkpoint_hash"] != checkpoints[train]["sha256"]:
            raise ValueError("Checkpoint provenance mismatch")
        if row["scenario_hash"] != manifest["scenario_hashes"][row["scenario_id"]]:
            raise ValueError("Scenario provenance mismatch")
        if row["safety_samples"] != row["num_steps"] or row["safety_samples"] <= 0:
            raise ValueError("Incomplete executed-signal coverage")
        for field in ("avg_delay", "p95_delay", "total_vehicles_passed", "safety_samples",
                      "executed_conflict_violations", "executed_clearance_violations"):
            if not math.isfinite(row[field]) or row[field] < 0:
                raise ValueError(f"Invalid metric: {field}")
        arrival_key = (row["scenario_id"], row["seed"])
        arrival = row["arrival_trace_hash"]
        if not arrival or arrivals.setdefault(arrival_key, arrival) != arrival:
            raise ValueError("Unpaired arrival traces")
    # Recompute statistics from raw rows; do not trust a manually edited table.
    if summarize(rows, matched_shield=True) != report:
        raise ValueError("Stored statistical report does not reproduce from raw runs")
    return manifest, report, rows


def write_csv(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_tables(output, summary, report):
    write_csv(output / "controllers.csv", summary)
    contrasts = []
    for name, item in report["comparisons"].items():
        contrasts.append(dict(comparison=name,
            scope="clean only" if name.startswith("clean_") else "all condition cells",
            metric=item.get("metric", "avg_delay"), saved_s=item["mean_delay_saved_s"],
            ci95_low_s=item["bootstrap_ci95_s"][0], ci95_high_s=item["bootstrap_ci95_s"][1]))
    write_csv(output / "contrasts.csv", contrasts)
    lines = [r"\begin{table}[t]", r"\centering", r"\small",
             r"\caption{Frozen simulation results across all condition cells. Lower delay is better. "
             r"Tail values are means of within-run p95, not pooled percentiles.}",
             r"\label{tab:audited-results}", r"\begin{tabular}{lrrr}", r"\hline",
             r"Controller & Delay (s) & Tail (s) & Runs \\", r"\hline"]
    for row in summary:
        lines.append(f"{LABELS[row['controller']]} & {row['mean_delay_s']:.3f} & "
                     f"{row['mean_within_run_p95_s']:.3f} & {row['runs']} " + r"\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}", ""]
    (output / "controllers.tex").write_text("\n".join(lines))


def plot_results(output, summary, report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(7.2, 4.0), layout="constrained")
    # Fixed semantic order, not sorted to foreground a favorable method.
    lookup = {r["controller"]: r for r in summary}
    names = list(LABELS)
    values = [lookup[n]["mean_delay_s"] for n in names]
    bars = ax.barh([LABELS[n] for n in names], values, color="#476b8e")
    ax.invert_yaxis()
    ax.set_xlim(0, max(values) * 1.16)
    ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.set_xlabel("Mean accumulated waiting per arrived vehicle (s); lower is better")
    ax.set_title("Frozen evaluation: all conditions and all training replicates")
    ax.spines[["top", "right"]].set_visible(False)
    for ext in ("pdf", "png"):
        fig.savefig(output / f"mean_delay.{ext}", dpi=240)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 3.4), layout="constrained")
    for y, (name, label) in enumerate(CONTRASTS.items()):
        item = report["comparisons"][name]
        lo, hi = item["bootstrap_ci95_s"]
        ax.hlines(y, lo, hi, color="#476b8e", linewidth=2)
        ax.plot(item["mean_delay_saved_s"], y, "o", color="#172f46")
    ax.set_yticks(range(len(CONTRASTS)), CONTRASTS.values())
    ax.invert_yaxis()
    ax.axvline(0, linestyle="--", color="gray", linewidth=1)
    ax.set_xlabel("Mean delay saved (s); positive favors first/added method")
    ax.set_title("Paired effects: descriptive 95% crossed-bootstrap intervals")
    ax.spines[["top", "right"]].set_visible(False)
    for ext in ("pdf", "png"):
        fig.savefig(output / f"paired_effects.{ext}", dpi=240)
    plt.close(fig)


def build(directory, output):
    if output.exists():
        raise FileExistsError("Choose a new output directory; existing evidence is preserved")
    manifest, report, rows = load_evidence(directory)
    summary = controller_summary(rows)
    if {r["controller"] for r in summary} != set(LABELS):
        raise ValueError("Unexpected controller family")
    output.mkdir(parents=True, exist_ok=False)
    write_tables(output, summary, report)
    plot_results(output, summary, report)
    (output / "postprocessor.py").write_bytes(Path(__file__).read_bytes())
    note = ("# Generated paper evidence — not submission certification\n\n"
            f"Source: `{directory.resolve()}`\n\n"
            f"{len(rows):,} runs; {len(manifest['choices'])} training replicates; "
            f"{len(manifest['traffic_seeds'])} traffic seeds. All templates/conditions "
            "remain fixed in the bootstrap. Intervals are descriptive and unadjusted.\n\n"
            "`controllers.tex` is an IEEE-compatible table fragment; CSV files retain full precision. "
            "Figures show point means and paired differences separately, not independent-run error bars. "
            "No winner or significance stars are assigned.\n\n"
            "Finite-horizon waiting includes unfinished/backlogged vehicles; it is not completed-trip "
            "travel time. Bare D3QN retains the physical signal FSM. Synthetic count faults are not "
            "camera validation; measured signal violations are not collision or deployment evidence. "
            "This final-evaluation bundle must not be pooled with later development validation.\n\n"
            "Raw evidence is untouched. The provenance manifest binds inputs and generated outputs. "
            "It is an integrity record, not independent certification of the simulator.\n")
    (output / "README.md").write_text(note)
    provenance = {"publication_ready": False, "simulation_inputs_modified": False,
        "source_directory": str(directory.resolve()),
        "input_sha256": {name: sha(directory / name) for name in (
            "manifest.json", "report.json", "runs.jsonl", "protocol.md", "source_snapshot.zip",
            "postprocessing_manifest.json", "postprocessing_source.py")},
        "output_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, allow_nan=False))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.evaluation, args.output))
