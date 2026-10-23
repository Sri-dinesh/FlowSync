"""Diagnose all saved SUMO action branches; no simulation, tuning or paper writing."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_trace_metrics import WINDOWS, gate_features, origin_map, signal_partition, wait_partition
from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_future_panel import read_trace, same_numbers, verify


def paired_metrics(base, alternative):
    values = dict(delay_saved=round(base["waiting"]["total"]-alternative["waiting"]["total"], 6))
    for group in ("by_origin", "by_location", "by_cohort"):
        for key in base["waiting"][group]:
            values[f"{group}.{key}"] = round(base["waiting"][group][key]-alternative["waiting"][group][key], 6)
        if abs(sum(v for k, v in values.items() if k.startswith(group+"."))-values["delay_saved"]) > 1e-6:
            raise ValueError("Paired decomposition does not conserve saved delay")
    for i, stop in enumerate(WINDOWS[1:]):
        values[f"saved_until_{stop/10:g}s"] = round(base["waiting"]["cumulative"][stop-1]-alternative["waiting"]["cumulative"][stop-1], 6)
        values[f"saved_window_{WINDOWS[i]/10:g}_{stop/10:g}s"] = round(base["waiting"]["by_window"][i]-alternative["waiting"]["by_window"][i], 6)
    for stage in ("green", "yellow", "red", "green_0", "green_1"):
        values[f"alternative_extra_{stage}_s"] = round(alternative["signal"]["seconds"][stage]-base["signal"]["seconds"][stage], 6)
    return values


def plot(output, curves, sources):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), layout="constrained")
    for ax, source in zip(axes.flat, sources):
        values = curves[source]
        for curve in values:
            ax.plot([(i+1)/10 for i in range(len(curve))], curve, color="#698aa5", alpha=.35, linewidth=.8)
        mean = [statistics.mean(x) for x in zip(*values)]
        ax.plot([(i+1)/10 for i in range(len(mean))], mean, color="#163e5d", linewidth=2)
        ax.axhline(0, color="gray", linewidth=.8)
        ax.set(title=f"Source {source}", xlabel="Elapsed branch time (s)", ylabel="Waiting saved (vehicle-seconds)")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Alternative hold versus recorded immediate-switch proposal")
    fig.supxlabel("Eight seen check futures per state; bold = descriptive mean. Prefixes are not new evaluation horizons.", fontsize=9)
    for ext in ("png", "svg"):
        fig.savefig(output/f"waiting_prefixes.{ext}", dpi=180)
    plt.close(fig)


def run(directory, output, plots=True):
    if output.exists():
        raise FileExistsError("Choose a new output directory; original evidence stays unchanged")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Output must be outside the frozen input directory")
    verification = verify(directory)
    if verification["smoke"]:
        raise ValueError("The completed full panel is required")
    cases = json.loads((directory/"frozen_cases.json").read_text())
    saved = [json.loads(line) for line in (directory/"outcomes.jsonl").read_text().splitlines()]
    lookup = {(r["source"], r["role"], r["index"]): r for r in saved}
    choices = json.loads((directory/"frozen_choices.json").read_text())
    net = ET.parse(directory/"network.net.xml").getroot()
    lengths = {e.get("id"): float(e.find("lane").get("length")) for e in net.findall("edge") if not e.get("id").startswith(":")}
    features, pairs, signal_runs, summaries, curves = [], [], [], [], {}
    for case in cases:
        source = case["source"]
        prefix = read_trace(directory/f"source_{source}.jsonl.gz")
        feature = gate_features(prefix, lengths)
        if feature["halted_proposal"] != case["baseline"] or feature["current_phase"] != case["current_phase"]:
            raise ValueError("Recorded proposal does not reconstruct from pre-action input")
        if case["baseline"] == case["current_phase"]:
            raise ValueError("This diagnosis requires the recorded switch-versus-hold cases")
        features.append(dict(source=source, pre_action_tick=prefix[-1]["tick"], gate_tick=case["gate"], **feature))
        present = {v[0] for v in prefix[-1]["vehicles"]} | {v[2] for v in prefix[-1]["pending"]}
        curves[source] = []
        outcomes = []
        for future in case["futures"]:
            origins = origin_map(prefix, future["arrivals"])
            analyses = {}
            for action in (0, 1):
                path = directory/f"branch_{source}_{future['role']}_{future['index']}_{action}.jsonl.gz"
                trace = read_trace(path)
                waiting, signal = wait_partition(trace, origins, present), signal_partition(trace)
                if not same_numbers(waiting["total"], lookup[source, future["role"], future["index"]][str(action)]["delay"]):
                    raise ValueError("Independent waiting attribution differs from recorded outcome")
                analyses[action] = dict(waiting=waiting, signal=signal)
                signal_runs.append(dict(source=source, role=future["role"], index=future["index"], action=action, **signal))
            base, alternative = analyses[case["baseline"]], analyses[1-case["baseline"]]
            pair = dict(source=source, role=future["role"], index=future["index"], **paired_metrics(base, alternative))
            measured = lookup[source, future["role"], future["index"]]
            original, changed = measured[str(case["baseline"])], measured[str(1-case["baseline"])]
            pair["completed_trips_gained"] = changed["throughput"]-original["throughput"]
            pair["endpoint_wait_saved_s"] = round(original["endpoint_wait"]-changed["endpoint_wait"], 6)
            pairs.append(pair)
            if future["role"] == "check":
                curves[source].append([round(a-b, 6) for a, b in zip(base["waiting"]["cumulative"], alternative["waiting"]["cumulative"])])
                outcomes.append(pair)
        columns = [k for k in outcomes[0] if k not in ("source", "role", "index")]
        summary = dict(source=source, current_phase=feature["current_phase"],
                       check_futures=len(outcomes), **{k: statistics.mean(r[k] for r in outcomes) for k in columns})
        summary["alternative_harmful_cases"] = sum(r["delay_saved"] < -1 or r["completed_trips_gained"] < 0
                                                   or r["endpoint_wait_saved_s"] < -1 for r in outcomes)
        summary["alternative_qualified_cases"] = sum(r["delay_saved"] > 1 and r["completed_trips_gained"] >= 0
                                                     and r["endpoint_wait_saved_s"] >= -1 for r in outcomes)
        for action in (0, 1):
            runs = [r for r in signal_runs if r["source"] == source and r["role"] == "check" and r["action"] == action]
            summary[f"action_{action}_distinct_signal_sequences"] = len({json.dumps(r["runs"], sort_keys=True) for r in runs})
        summaries.append(summary)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in (("paired_waiting.csv", pairs), ("source_check_summary.csv", summaries)):
        with (output/name).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    for name, rows in (("gate_features.json", features), ("signal_runs.json", signal_runs)):
        (output/name).write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")
    input_rows = []
    for feature in features:
        row = {k: feature[k] for k in ("source", "pre_action_tick", "gate_tick", "current_phase", "green_age_s",
                                      "halted_proposal", "total_count_shadow_proposal", "pressure_shadow_proposal",
                                      "evaluation_only_entry_backlog")}
        for field in ("halted", "incoming", "moving", "near_30m", "geometric_eta_le_4s", "raw_pressure"):
            for i, label in enumerate(("ns", "ew")):
                row[f"{field}_{label}"] = feature[field][i]
        input_rows.append(row)
    with (output/"source_inputs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(input_rows[0]))
        writer.writeheader()
        writer.writerows(input_rows)
    if plots:
        plot(output, curves, [c["source"] for c in cases])
    scope = ("Post-hoc diagnosis on six consumed states; no fitting or predictive validation. "
             "The acting controller uses halted counts and physical state. Incoming/moving/position "
             "features and pressure proposals are shadows on saved clean state, not executed policies. "
             "External backlog/cohort attribution is evaluation-only. Prefixes/partitions do not "
             "isolate causal contributions of clearance or certify a new horizon/control win.")
    report = dict(complete=True, source_states=len(cases), analysed_branches=len(signal_runs),
                  future_pairs=len(pairs), traffic_rollouts=0, models_fitted=0, policy_promoted=False,
                  all_recorded_switch_proposals_reconstructed=True,
                  pressure_shadow_differs_from_baseline=sum(f["pressure_shadow_proposal"] != f["halted_proposal"] for f in features),
                  pressure_shadow_matches_both_frozen_selectors=sum(
                      f["pressure_shadow_proposal"] == choices[str(f["source"])]["single"] == choices[str(f["source"])]["mean8"]
                      for f in features),
                  sources=summaries, scope=scope, verification=verification,
                  input_sha256={name: file_hash(directory/name) for name in ("manifest.json", "report.json", "frozen_cases.json",
                      "frozen_choices.json", "outcomes.jsonl", "source_snapshot.zip", "network.net.xml")},
                  output_sha256={p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
    source_files = [Path(__file__), Path(__file__).resolve().parents[1]/"analysis/sumo_trace_metrics.py"]
    with zipfile.ZipFile(output/"analysis_source.zip", "w") as archive:
        for path in source_files:
            archive.write(path, path.name)
    report["analysis_source_sha256"] = file_hash(output/"analysis_source.zip")
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    report = run(args.directory, args.output, not args.no_plots)
    print(json.dumps({k: report[k] for k in ("complete", "source_states", "analysed_branches", "future_pairs", "traffic_rollouts", "pressure_shadow_differs_from_baseline")}, indent=2))


if __name__ == "__main__":
    main()
