"""Export closed robustness evidence as CSV; no simulation or manuscript writing."""
import argparse
import csv
import json
from pathlib import Path

from research.analysis.analyze_sumo_count_ablation import demand_role
from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_robustness import verify


def run(directory, output):
    if output.exists():
        raise FileExistsError("Choose a new export directory")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Export must be outside the frozen collection")
    verification = verify(directory)
    if verification["smoke"]:
        raise ValueError("Performance tables require the completed full study")
    saved = json.loads((directory/"report.json").read_text())
    if saved["component_series_closed_on_completion"] is not True:
        raise ValueError("The component study must be closed")
    inputs = {name: file_hash(directory/name) for name in ("report.json", *saved["output_hashes"])}
    plans = {p["seed"]: p for p in json.loads((directory/"frozen_plans.json").read_text())}
    runs = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    tables = {name: [] for name in ("controller_summary", "comparison_summary", "phase_summary", "family_summary",
                                  "seed_summary", "paired_contexts", "axis_profiles", "signal_exposure")}
    for endpoint, comparison in saved["endpoint_comparisons"].items():
        common = dict(endpoint_seconds=int(endpoint), primary=comparison["primary"])
        aggregate = comparison["aggregate"]
        tables["comparison_summary"].append(dict(**common, first="total_incoming", reference="max_pressure",
            traffic_seeds=aggregate["traffic_seeds"], paired_start_contexts=aggregate["paired_start_contexts"], **aggregate["mean"]))
        for controller, values in comparison["controller_means"].items():
            tables["controller_summary"].append(dict(**common, controller=controller, **values["overall"]))
        for phase, values in comparison["by_initial_phase"].items():
            tables["phase_summary"].append(dict(**common, initial_phase=int(phase), initial_green="EW" if int(phase) else "NS",
                traffic_seeds=values["traffic_seeds"], paired_start_contexts=values["paired_start_contexts"], **values["mean"]))
        for family, values in comparison["by_family"].items():
            tables["family_summary"].append(dict(**common, family=family, traffic_seeds=values["traffic_seeds"],
                paired_start_contexts=values["paired_start_contexts"], **values["mean"]))
        for values in aggregate["seed_results"]:
            tables["seed_summary"].append(dict(**common, seed=values["seed"], initial_phase_contexts=values["initial_phase_contexts"], **values["mean"]))
        for values in comparison["case_results"]:
            tables["paired_contexts"].append(dict(**common, **{key: value for key, value in values.items() if key != "axis_results"}))
    for row in runs:
        for endpoint, values in row["measurements"].items():
            common = dict(endpoint_seconds=int(endpoint), seed=row["seed"], family=row["family"],
                          initial_phase=row["initial_phase"], controller=row["controller"])
            for axis, profile in values["axes"].items():
                tables["axis_profiles"].append(dict(**common, axis=axis, role=demand_role(plans[row["seed"]], axis), **profile))
            tables["signal_exposure"].append(dict(**common, **{key+"_s": value for key, value in values["signal"]["seconds"].items()},
                                                  switch_onsets=values["signal"]["switch_onsets"]))
    if any(file_hash(directory/name) != sha for name, sha in inputs.items()):
        raise ValueError("Input evidence changed during export")
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in tables.items():
        with (output/(name+".csv")).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output/"collection_report.json").write_bytes((directory/"report.json").read_bytes())
    (output/"collection_manifest.json").write_bytes((directory/"manifest.json").read_bytes())
    (output/"exporter_source.py").write_bytes(Path(__file__).read_bytes())
    manifest = dict(complete=True, component_series_closed=True, traffic_rollouts=0, models_trained=0,
        policy_promoted=False, verification=verification, input_sha256=inputs,
        csv_rows={name: len(rows) for name, rows in tables.items()},
        output_sha256={p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()},
        scope="CSV copies of verified measurements, not new experiments or fitted estimates. Positive saved waiting "
              "favours total counts over pressure. Blank lower/higher-demand fields in balanced families mean not applicable. "
              "The hierarchy is six traffic seeds, twelve paired starts and two overlapping endpoints; axis p95/max are "
              "within-axis values and aggregates average within-run values. No population significance, independent final "
              "test, new controller contribution, RL advantage or publication readiness is established.")
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.directory, args.output)
    print(json.dumps({key: result[key] for key in ("complete", "component_series_closed", "traffic_rollouts", "csv_rows")}, indent=2))


if __name__ == "__main__":
    main()
