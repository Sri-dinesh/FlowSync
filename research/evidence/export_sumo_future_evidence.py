"""Verify/export the completed SUMO future panel; never rerun or select traffic."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path

from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_future_panel import same_numbers, verify


def paired_gain(row, baseline):
    """Independent decimal aggregation of the recorded six-decimal outcomes."""
    base, alternative = row[str(baseline)], row[str(1-baseline)]
    number = lambda value: Decimal(str(value))
    return (number(base["delay"])-number(alternative["delay"]),
            number(alternative["throughput"])-number(base["throughput"]),
            number(base["endpoint_wait"])-number(alternative["endpoint_wait"]))


def mean(values):
    return sum(values, Decimal(0))/len(values)


def qualified(gain):
    return gain[0] > 1 and gain[1] >= 0 and gain[2] >= -1


def harmful(gain):
    return gain[0] < -1 or gain[1] < 0 or gain[2] < -1


def tables(cases, rows, choices):
    if len({c["source"] for c in cases}) != len(cases) or not cases:
        raise ValueError("Duplicate/empty sources")
    expected = {(c["source"], role, index) for c in cases
                for role, indices in (("single", (-1,)), ("fit", range(8)), ("check", range(8, 16))) for index in indices}
    keys = [(r["source"], r["role"], r["index"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate/changed future partition")
    per_future, per_source, arm_cases, source_means = [], [], {}, {}
    for case in cases:
        source, baseline = case["source"], case["baseline"]
        gains = {role: [paired_gain(r, baseline) for r in rows if r["source"] == source and r["role"] == role]
                 for role in ("single", "fit", "check")}
        frozen = dict(baseline=baseline)
        for arm, role in (("single", "single"), ("mean8", "fit")):
            average = tuple(mean([g[i] for g in gains[role]]) for i in range(3))
            frozen[arm] = 1-baseline if qualified(average) else baseline
        if choices[str(source)] != frozen:
            raise ValueError("Choice changed or uses the wrong selection partition")
        for row in (r for r in rows if r["source"] == source):
            values = paired_gain(row, baseline)
            per_future.append(dict(source=source, family=case["family"], role=row["role"], index=row["index"],
                baseline_phase=baseline, alternative_phase=1-baseline,
                delay_saved_vehicle_seconds=float(values[0]), completed_trips_gained=float(values[1]),
                endpoint_wait_saved_s=float(values[2]), joint_qualified=qualified(values), joint_harmful=harmful(values)))
        positive, negative = sum(g[0] > 1 for g in gains["check"]), sum(g[0] < -1 for g in gains["check"])
        item = dict(source=source, family=case["family"], gate_seconds=case["gate"]/10,
                    check_futures=8, positive=positive, negative=negative, deadband=8-positive-negative,
                    mixed=positive > 0 and negative > 0,
                    alternative_mean_delay_saved=float(mean([g[0] for g in gains["check"]])))
        for arm, action in frozen.items():
            values = gains["check"] if action != baseline else [(Decimal(0),)*3]*8
            source_means[source, arm] = tuple(mean([g[i] for g in values]) for i in range(3))
            arm_cases[source, arm] = values
            item[f"{arm}_choice"] = action
            item[f"{arm}_changed"] = action != baseline
            item[f"{arm}_delay_saved"] = float(source_means[source, arm][0])
        per_source.append(item)
    arms = []
    for arm in ("baseline", "single", "mean8"):
        values = [v for case in cases for v in arm_cases[case["source"], arm]]
        averages = [mean([source_means[c["source"], arm][i] for c in cases]) for i in range(3)]
        arms.append(dict(arm=arm, mean_delay_saved_vehicle_seconds=float(averages[0]),
            mean_completed_trips_gained=float(averages[1]), mean_endpoint_wait_saved_s=float(averages[2]),
            changed_gates=sum(r[f"{arm}_changed"] for r in per_source), check_cases=len(values),
            changed_cases=8*sum(r[f"{arm}_changed"] for r in per_source),
            qualified_cases=sum(qualified(v) for v in values), harmful_cases=sum(harmful(v) for v in values)))
    return per_future, per_source, arms


def plot(output, futures, sources):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.3), layout="constrained")
    for i, source in enumerate(sources):
        values = [r["delay_saved_vehicle_seconds"] for r in futures if r["source"] == source["source"] and r["role"] == "check"]
        offsets = [(-.21+.06*j) for j in range(8)]
        axes[0].scatter([i+x for x in offsets], values, s=20, color="#355f80", alpha=.85)
    for y in (-1, 1):
        axes[0].axhline(y, color="#999999", linestyle=":", linewidth=.8)
    axes[0].axhline(0, color="#555555", linewidth=.8)
    labels = [str(r["source"]) for r in sources]
    axes[0].set(xticks=range(len(labels)), xticklabels=labels, xlabel="Source seed (one fixed gate each)",
                ylabel="Alternative delay saved (vehicle-seconds)", title="Eight check futures per gate")
    axes[0].tick_params(axis="x", rotation=40)
    for offset, arm, color in ((-.18, "single", "#355f80"), (.18, "mean8", "#ba6b35")):
        axes[1].bar([i+offset for i in range(len(sources))], [r[f"{arm}_delay_saved"] for r in sources],
                    width=.36, color=color, label=arm.capitalize())
    coincide = all(r["single_choice"] == r["mean8_choice"] for r in sources)
    axes[1].set(xticks=range(len(labels)), xticklabels=labels, xlabel="Source seed (equal source weighting)",
                ylabel="Selected delay saved (vehicle-seconds)",
                title="Single and Mean8 choices coincide" if coincide else "Frozen selector outcomes")
    axes[1].tick_params(axis="x", rotation=40)
    axes[1].axhline(0, color="#555555", linewidth=.8)
    active = [str(r["source"]) for r in sources if r["single_delay_saved"] != 0 or r["mean8_delay_saved"] != 0]
    if len(active) == 1:
        axes[1].text(.04, .95, f"All aggregate savings come\nfrom source {active[0]}", transform=axes[1].transAxes,
                     ha="left", va="top", fontsize=9)
    axes[1].legend(frameon=False, loc="upper right", fontsize=8)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
    total = sum(s["check_futures"] for s in sources)
    fig.supxlabel(f"SUMO: {len(sources)} gates, {total} correlated check cases. Simulator-hindsight choices; no learned policy.", fontsize=8)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(output/f"sumo_future_stability.{ext}", dpi=220)
    plt.close(fig)


def export(directory, output):
    if output.exists():
        raise FileExistsError("Choose a new output directory")
    verification = verify(directory)
    if verification["smoke"] or not verification["scientific_panel_complete"]:
        raise ValueError("A complete non-smoke scientific panel is required")
    cases = json.loads((directory/"frozen_cases.json").read_text())
    choices = json.loads((directory/"frozen_choices.json").read_text())
    rows = [json.loads(line) for line in (directory/"outcomes.jsonl").read_text().splitlines()]
    report = json.loads((directory/"report.json").read_text())
    futures, sources, arms = tables(cases, rows, choices)
    signs = dict(positive=sum(r["positive"] for r in sources), negative=sum(r["negative"] for r in sources),
                 mixed_gates=sum(r["mixed"] for r in sources))
    if signs != report["sign_counts"]:
        raise ValueError("Independent sign aggregation mismatch")
    for arm in arms:
        original = report["arms"][arm["arm"]]
        values = [arm["mean_delay_saved_vehicle_seconds"], arm["mean_completed_trips_gained"], arm["mean_endpoint_wait_saved_s"]]
        if not same_numbers(values, [float(v) for v in original["mean_gain"]]):
            raise ValueError("Independent selector means mismatch")
        for key, old_key in (("changed_gates", "changed_gates"), ("harmful_cases", "harmful"), ("qualified_cases", "qualified")):
            if arm[key] != original[old_key]:
                raise ValueError("Independent selector counts mismatch")
    output.mkdir(parents=True, exist_ok=False)
    for name, table in (("futures.csv", futures), ("sources.csv", sources), ("selectors.csv", arms)):
        with (output/name).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    plot(output, futures, sources)
    same_choices = all(r["single_choice"] == r["mean8_choice"] for r in sources)
    active = [r["source"] for r in sources if r["single_changed"]]
    lookup = {r["arm"]: r for r in arms}
    single = lookup["single"]
    total = sum(r["check_futures"] for r in sources)
    concentration = "; ".join(f"{r['source']}: single {r['single_delay_saved']:.6f}, mean8 {r['mean8_delay_saved']:.6f}"
                               for r in sources if r["single_changed"] or r["mean8_changed"])
    note = ("# Independent SUMO action/future evidence\n\n"
        f"Verified {verification['branches']} branches at {len(sources)} fixed gates. "
        f"Across {total} check futures: {signs['positive']} positive, {signs['negative']} negative, "
        f"{total-signs['positive']-signs['negative']} within the ±1 vehicle-second deadband; "
        f"{signs['mixed_gates']} gates contain both signs.\n\n"
        f"Single/Mean8 choices coincide at every gate: {same_choices}. Changed source(s): {active}. "
        f"Single saves {single['mean_delay_saved_vehicle_seconds']:.6f} vehicle-seconds "
        f"averaged equally across {len(sources)} sources, with {single['mean_completed_trips_gained']:.6f} "
        f"completed-trip gain and {single['mean_endpoint_wait_saved_s']:.6f} s endpoint-wait saving. "
        f"Mean8 saves {lookup['mean8']['mean_delay_saved_vehicle_seconds']:.6f} vehicle-seconds. "
        f"Per-active-source savings (vehicle-seconds): {concentration or 'none'}. "
        f"Single has {single['qualified_cases']} qualified and {single['harmful_cases']} harmful check cases.\n\n"
        "This replicates future sensitivity in the declared SUMO setup and a local hindsight benefit. "
        "It establishes no added averaging benefit, learned-controller win, population prevalence or "
        "full-run superiority. Gates/futures are correlated, and completed trips differ from the custom "
        "simulator's passed-vehicle metric. No intervals, significance or safety guarantee.\n\n"
        "Verification recomputes saved traces and independent decimal outcome aggregation; "
        "no traffic trajectories were independently rerun during export. Old artifacts remain untouched.\n")
    (output/"README.md").write_text(note)
    manifest = dict(verified=True, publication_ready=False, traffic_rollouts=0, verification=verification,
        source_directory=str(directory.resolve()), exporter_sha256=file_hash(__file__),
        inputs={name: file_hash(directory/name) for name in ("manifest.json", "report.json", "frozen_cases.json",
                 "frozen_choices.json", "outcomes.jsonl", "source_snapshot.zip")},
        outputs={p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return dict(verified=True, branches=verification["branches"], mixed_gates=signs["mixed_gates"],
                choices_coincide=same_choices, active_sources=active, publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.directory, args.output), indent=2))


if __name__ == "__main__":
    main()
