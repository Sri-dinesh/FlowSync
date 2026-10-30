"""Hash-checked panel export and post-hoc same-state proposal comparisons.

Full packet/shield/signal replay is the panel runner's separate --verify mode.
This exporter checks the sealed files and summaries without repeating that work.
"""
import argparse
from collections import Counter
import csv
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research.observation.arrival_tracks import Packet, TrackHistory
from research.pilots.run_arrival_window_panel import (
    CALIBRATION, METHODS, PRIMARY, PLAN, build_context, collect_rows, compare, means, sha, shield, write,
)
from research.policies.arrival_extension import choose_extension, pressure_phase, Timing


def csv_file(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def same_state_diagnosis(source, row):
    with gzip.open(source/row["raw_file"], "rt") as stream:
        raw = json.load(stream)
    timing = Timing(all_red=raw["case"]["scenario"]["red_duration"])
    history = TrackHistory(CALIBRATION)
    waits, counts, reasons = dict.fromkeys(range(4), 0.), Counter(), Counter()
    for frame in raw["frames"]:
        state = history.observe(Packet.parse(frame["packet"]))
        context, waits = build_context(state, frame["before"], frame["step"], waits, timing)
        if not frame["policy"]["gate"]:
            continue
        counts["gates"] += 1
        reasons[frame["policy"]["reason"]] += 1
        primary, _ = choose_extension(state, context, timing, PRIMARY)
        if primary != frame["proposed"]:
            raise ValueError("Primary proposal replay differs")
        for name in ("point_extension", "no_age_extension"):
            alternative, _ = choose_extension(state, context, timing, name)
            counts[f"different_from_{name}"] += int(alternative != primary)
        if frame["policy"]["reason"] == "supported_extension":
            counts["extensions"] += 1
            counts["extension_shield_overrides"] += int(frame["executed"] != primary)
            for subset in ("all", "upstream"):
                reference = pressure_phase(state, context.current_phase, subset=subset)
                executed = shield(timing).filter_context(reference, context).executed_action
                counts[f"extension_matches_{subset}_mp_executed"] += int(executed == frame["executed"])
    keys = ("gates", "extensions", "extension_shield_overrides", "different_from_point_extension",
            "different_from_no_age_extension", "extension_matches_all_mp_executed", "extension_matches_upstream_mp_executed")
    return dict(case_id=row["case_id"], **{key: counts[key] for key in keys}), dict(reasons)


def export(source, output):
    report = json.loads((source/"report.json").read_text())
    manifest = json.loads((source/"manifest.json").read_text())
    if report["smoke"] or not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)):
        raise ValueError("Export requires a completed non-smoke frozen panel")
    files = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file() and p != source/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(source/name) != h for name, h in report["output_sha256"].items()):
        raise ValueError("Frozen output hash/coverage mismatch")
    rows = collect_rows(source, manifest["cases"], manifest["methods"])
    if rows != report["rows"] or compare(rows, manifest["cases"], manifest["methods"]) != report["comparison"]:
        raise ValueError("Raw summary/screen reconstruction mismatch")
    output.mkdir(parents=True, exist_ok=False)
    case_lookup = {case["case_id"]: case for case in manifest["cases"]}
    exported = []
    for row in rows:
        case = case_lookup[row["case_id"]]
        exported.append(dict(case_id=row["case_id"], method=row["method"], traffic_seed=case["seed"], fault=case["fault"]["name"],
            **{key: row[key] for key in ("delay", "p95", "passed", "arrivals", "samples", "violations", "policy_gates", "extension_proposals")},
            shield_override_ticks=row["shield"]["total_overrides"], raw_file=row["raw_file"], raw_sha256=row["raw_sha256"]))
    csv_file(output/"all_cases.csv", exported)
    summary = [dict(method=method, **report["comparison"]["means"][method]) for method in METHODS]
    csv_file(output/"summary.csv", summary)
    conditions = [dict(method=method, fault=fault, **means([row for row in exported if row["method"] == method and row["fault"] == fault]))
                  for method in METHODS for fault in sorted({row["fault"] for row in exported})]
    csv_file(output/"condition_summary.csv", conditions)
    diagnosis, reasons = [], []
    for row in rows:
        if row["method"] != PRIMARY:
            continue
        values, reason_counts = same_state_diagnosis(source, row)
        diagnosis.append(values)
        reasons.extend(dict(case_id=row["case_id"], reason=reason, gates=n) for reason, n in sorted(reason_counts.items()))
    csv_file(output/"same_state_diagnosis.csv", diagnosis)
    csv_file(output/"primary_reasons.csv", reasons)
    totals = {key: sum(row[key] for row in diagnosis) for key in diagnosis[0] if key != "case_id"}
    write(output/"diagnosis.json", dict(totals=totals,
        scope="Post-hoc proposals on the primary's recorded delivered states, including separately shielded pressure proposals. No counterfactual traffic, independent replicates, causal benefit attribution or new selection rule."))
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout="constrained")
    labels = [method.replace("advanced_mp", "Advanced-MP").replace("mp_", "MP_").replace("_", " ") for method in METHODS]
    colors = ["#1768ac" if method == PRIMARY else "#bd8320" if method.endswith("extension") else "#8492a6" for method in METHODS]
    for axis, key, label in ((axes[0], "delay", "Mean stopped wait per arrived vehicle (s)"),
                             (axes[1], "p95", "Average within-run p95 stopped wait (s)")):
        values = [row[key] for row in summary]
        axis.barh(labels, values, color=colors)
        axis.invert_yaxis()
        axis.set(xlabel=label, xlim=(0, max(values)*1.16))
        axis.grid(axis="x", alpha=.2)
        axis.set_axisbelow(True)
        for i, value in enumerate(values):
            axis.text(value+max(values)*.015, i, f"{value:.3f}", va="center", fontsize=8)
    status = "passes" if report["continue_to_fresh_development"] else "fails"
    fig.suptitle(f"Arrival-window development: frozen screen {status}")
    fig.supxlabel("18 cases: 6 traffic/template realizations × 3 sensing conditions; descriptive equal means, no confidence intervals.\n"
                  "All methods and unfavorable cases retained; existing-family headroom test, not final confirmation or CCTV validation.", fontsize=9)
    fig.savefig(output/"arrival_window_comparison.png", dpi=200)
    fig.savefig(output/"arrival_window_comparison.svg")
    plt.close(fig)
    (output/"exporter_source.py").write_bytes(Path(__file__).read_bytes())
    write(output/"manifest.json", dict(input_directory=str(source.resolve()),
        input_sha256={name: sha(source/name) for name in ("manifest.json", "report.json")},
        output_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()}, publication_ready=False,
        scope="Sealed output hashes, raw result summary/screen reconstruction and same-state primary proposal diagnosis. Full packet/corruption/shield/signal replay uses the panel runner's separate --verify mode. No new traffic simulation."))
    return dict(complete=True, cases=len(rows), diagnosis=totals, screen_passed=report["continue_to_fresh_development"], publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
