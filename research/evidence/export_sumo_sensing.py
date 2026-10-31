"""Export verified sensing evidence and independent decimal arithmetic; no new traffic."""
import argparse
import csv
from decimal import Decimal, localcontext
from itertools import product
import json
import math
from pathlib import Path
import shutil
import sys

from research.analysis.sumo_sensing_metrics import MEASURES, SUMMARY_MEASURES
from research.pilots.recover_sumo_sensing import inventory, verify as verify_recovery
from research.pilots.run_sumo_sensing_panel import case_table, file_hash, read_trace, write

CONTROLLERS = ("max_pressure", "halted", "fixed")
FAULTS = ("clean", "delay2s", "miss30", "delay2s_miss30")
LABELS = dict(max_pressure="Max-Pressure", halted="Halted-count", fixed="Fixed",
              clean="Clean", delay2s="Delay 2 s", miss30="Miss 30%", delay2s_miss30="Delay + misses")


def number(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Nonfinite evidence value")
    return result


def interval(values, frozen):
    """Independent binomial-weight enumeration, rather than ordered seed tuples."""
    groups = [[p["seed"] for p in frozen if p["family"] == family]
              for family in sorted({p["family"] for p in frozen})]
    if len(groups) != 3 or any(len(group) != 2 for group in groups):
        raise ValueError("This frozen analysis requires two seeds in each of three families")
    draws = []
    for counts in product(range(3), repeat=3):
        mean = sum(k * values[a] + (2-k) * values[b] for k, (a, b) in zip(counts, groups)) / 6
        draws.extend([mean] * math.prod((1, 2, 1)[k] for k in counts))
    draws.sort()
    def quantile(probability):
        position = probability * (len(draws)-1)
        low = int(position)
        return draws[low] + (draws[min(low+1, len(draws)-1)]-draws[low]) * (position-low)
    return quantile(Decimal(".025")), quantile(Decimal(".975"))


def numeric_tables(rows, frozen, summary):
    lookup = {(r["seed"], r["controller"], r["fault"]): r["metrics"] for r in rows}
    expected = {(p["seed"], c, f) for p in frozen for c in CONTROLLERS for f in FAULTS}
    if len(rows) != 72 or set(lookup) != expected or any(r["repeat"] != 0 for r in rows):
        raise ValueError("Numeric export requires all 72 unique frozen cells")
    audit, contrasts, exact_sign_differences = [], [], []
    def check(label, saved, computed):
        error = abs(number(saved)-computed)
        if error > Decimal("1e-10"):
            raise ValueError(f"Independent arithmetic differs: {label}")
        audit.append(dict(quantity=label, saved=str(saved), decimal=str(computed), absolute_error=str(error)))
    with localcontext() as context:
        context.prec = 50
        for row in summary["aggregate"]:
            for metric in SUMMARY_MEASURES:
                computed = sum(number(lookup[p["seed"], row["controller"], row["fault"]][metric]) for p in frozen) / 6
                check(f"aggregate/{row['controller']}/{row['fault']}/{metric}", row[metric], computed)
        paired = {(r["kind"], r["controller"], r["fault"], r["seed"]): r for r in summary["paired_contrasts"]}
        if len(summary["contrasts"]) != 20 or len(paired) != 120:
            raise ValueError("Expected all 20 contrasts and 120 paired-seed rows")
        for row in summary["contrasts"]:
            kind, controller, fault = row["kind"], row["controller"], row["fault"]
            for metric in MEASURES:
                values = {}
                for plan in frozen:
                    seed = plan["seed"]
                    def value(c, f):
                        return number(lookup[seed, c, f][metric])
                    if kind == "fault_minus_clean":
                        amount = value(controller, fault)-value(controller, "clean")
                    elif kind == "pressure_saving":
                        amount = value(controller, fault)-value("max_pressure", fault)
                        if metric == "completed_trips": amount = -amount
                    elif kind == "factorial_interaction":
                        amount = value(controller, "delay2s_miss30")-value(controller, "delay2s")-value(controller, "miss30")+value(controller, "clean")
                    else:
                        raise ValueError("Unknown frozen contrast")
                    values[seed] = amount
                    check(f"paired/{kind}/{controller}/{fault}/{seed}/{metric}",
                          paired[kind, controller, fault, seed][metric], amount)
                saved = row["metrics"][metric]
                low, high = interval(values, frozen)
                check(f"contrast/{kind}/{controller}/{fault}/{metric}/mean", saved["mean"], sum(values.values()) / 6)
                check(f"contrast/{kind}/{controller}/{fault}/{metric}/lower", saved["interval"]["lower"], low)
                check(f"contrast/{kind}/{controller}/{fault}/{metric}/upper", saved["interval"]["upper"], high)
                if saved["interval"]["ordered_draws"] != 64:
                    raise ValueError("Changed frozen resampling coverage")
                exact = dict(positive=sum(v > 0 for v in values.values()), zero=sum(v == 0 for v in values.values()),
                             negative=sum(v < 0 for v in values.values()))
                recorded = {key: saved[key] for key in exact}
                if exact != recorded:
                    exact_sign_differences.append(dict(kind=kind, controller=controller, fault=fault, metric=metric,
                                                      frozen_float_signs=recorded, exact_decimal_signs=exact))
                contrasts.append(dict(kind=kind, controller=controller, fault=fault, metric=metric,
                    mean=saved["mean"], lower=saved["interval"]["lower"], upper=saved["interval"]["upper"],
                    ordered_draws=64, **recorded))
    return dict(contrasts=contrasts, arithmetic_audit=audit, decimal_sign_differences=exact_sign_differences)


def diagnostics(directory, rows):
    """Exploratory executed-service and first-action differences, separate from frozen contrasts."""
    lookup = {(r["seed"], r["controller"], r["fault"]): r for r in rows}
    service, splits = [], []
    for seed in sorted({r["seed"] for r in rows}):
        for controller in CONTROLLERS:
            clean = read_trace(directory / lookup[seed, controller, "clean"]["trace"])
            for fault in FAULTS:
                run = lookup[seed, controller, fault]
                trace = clean if fault == "clean" else read_trace(directory / run["trace"])
                green = [sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == p for r in trace) for p in (0, 1)]
                yellow = sum(r["fsm"]["stage"] == "yellow" for r in trace)
                red = sum(r["fsm"]["stage"] == "red" for r in trace)
                onsets = sum(r["fsm"]["stage"] == "yellow" and (i == 0 or trace[i-1]["fsm"]["stage"] != "yellow")
                             for i, r in enumerate(trace))
                if sum(green)+yellow+red != 1800 or onsets != run["metrics"]["switch_onsets"]:
                    raise ValueError("Exploratory signal accounting does not match verified metrics")
                service.append(dict(seed=seed, family=run["family"], controller=controller, fault=fault,
                    green_ns_s=green[0]/10, green_ew_s=green[1]/10, yellow_s=yellow/10,
                    all_red_s=red/10, clearance_s=(yellow+red)/10, switch_onsets=onsets))
                if fault == "clean": continue
                gates = [i for i, r in enumerate(trace) if "decision" in r]
                differing = [i for i in gates if trace[i]["decision"]["proposal"] != clean[i]["decision"]["proposal"]]
                first = differing[0] if differing else None
                stop = first if first is not None else len(trace)
                equal = all({k: v for k, v in a.items() if k not in ("decision", "sensing")} ==
                            {k: v for k, v in b.items() if k not in ("decision", "sensing")}
                            for a, b in zip(clean[:stop], trace[:stop]))
                if first is not None:
                    equal = equal and clean[first]["decision"]["before_fsm"] == trace[first]["decision"]["before_fsm"]
                splits.append(dict(seed=seed, family=run["family"], controller=controller, fault=fault,
                    decision_gates=len(gates), differing_proposals=len(differing), first_split_tick=first,
                    first_split_s=None if first is None else first/10, same_physical_prefix=equal,
                    clean_first_proposal=None if first is None else clean[first]["decision"]["proposal"],
                    fault_first_proposal=None if first is None else trace[first]["decision"]["proposal"],
                    lamps_differ_ticks=sum(a["lamps"] != b["lamps"] for a, b in zip(clean, trace))))
    return service, splits


def csv_write(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_tables(source):
    collection = source / "collection"
    report = json.loads((collection / "report.json").read_text())
    recovery = json.loads((source / "report.json").read_text())
    rows = [json.loads(line) for line in (collection / "runs.jsonl").read_text().splitlines()]
    frozen = json.loads((collection / "frozen_plans.json").read_text())
    numeric = numeric_tables(rows, frozen, report["summary"])
    service, splits = diagnostics(collection, rows)
    cases = [dict(**r, record_origin="reused" if i < recovery["reused_runs"] else "new",
                  source_trace_file=rows[i]["trace"], source_trace_sha256=report["output_hashes"][rows[i]["trace"]])
             for i, r in enumerate(case_table(rows))]
    tables = dict(cases=cases, aggregate=report["summary"]["aggregate"], contrasts=numeric["contrasts"],
                  paired_contrasts=report["summary"]["paired_contrasts"], arithmetic_audit=numeric["arithmetic_audit"],
                  exploratory_service=service, exploratory_first_splits=splits)
    return rows, report["summary"], tables, numeric


def figures(output, rows, summary, contrasts):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    colors = dict(max_pressure="#1768ac", halted="#b65c18", fixed="#59636d")
    labels = ("Stopped wait / requested vehicle (s)", "Within-run p95 stopped wait (s)", "Completed trips")
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), layout="constrained")
    aggregate = {(r["controller"], r["fault"]): r for r in summary["aggregate"]}
    for axis, metric, label in zip(axes, MEASURES, labels):
        for c in CONTROLLERS:
            axis.plot(range(4), [aggregate[c, f][metric] for f in FAULTS], marker="o", color=colors[c], label=LABELS[c])
            for x, fault in enumerate(FAULTS):
                axis.scatter([x]*6, [r["metrics"][metric] for r in rows if r["controller"] == c and r["fault"] == fault],
                             color=colors[c], alpha=.25, s=18)
        axis.set_xticks(range(4), [LABELS[f] for f in FAULTS], rotation=25, ha="right")
        axis.set_ylabel(label)
        axis.set_ylim(bottom=0)
        axis.grid(axis="y", alpha=.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("SUMO sensing panel: six paired traffic seeds; dots are runs, lines are means", fontsize=11)
    for extension in ("png", "pdf", "svg"): fig.savefig(output / f"sensing_outcomes.{extension}", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 10), sharey=True, layout="constrained")
    definitions = [(r["kind"], r["controller"], r["fault"]) for r in summary["contrasts"]]
    lookup = {(r["kind"], r["controller"], r["fault"], r["metric"]): r for r in contrasts}
    kind_label = dict(fault_minus_clean="Fault − clean", pressure_saving="Pressure saving", factorial_interaction="Interaction")
    for axis, metric, label in zip(axes, MEASURES, labels):
        for y, (kind, c, fault) in enumerate(definitions):
            row = lookup[kind, c, fault, metric]
            axis.hlines(y, row["lower"], row["upper"], color=colors[c], linewidth=2)
            axis.plot(row["mean"], y, "o", color=colors[c], markersize=4)
        axis.axvline(0, color="black", linewidth=.7)
        axis.set_xlabel(label)
        axis.grid(axis="x", alpha=.2)
    axes[0].set_yticks(range(len(definitions)), [f"{kind_label[k]} | {LABELS[c]} | {LABELS[f]}" for k, c, f in definitions], fontsize=7)
    axes[0].invert_yaxis()
    fig.suptitle("All 20 frozen contrasts: means and descriptive 95% seed-bootstrap intervals", fontsize=11)
    fig.supxlabel("Fault − clean: positive wait is a cost; pressure saving: positive favours pressure; interaction: both − delay − misses + clean", fontsize=8)
    for extension in ("png", "pdf", "svg"): fig.savefig(output / f"sensing_contrasts.{extension}", dpi=180)
    plt.close(fig)
    return matplotlib.__version__


def export(source, output):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Choose a new evidence directory")
    recovery_manifest = json.loads((source / "manifest.json").read_text())
    prefix = Path(recovery_manifest["prefix_directory"])
    mechanics = Path(json.loads((prefix / "manifest.json").read_text())["mechanics"]["directory"])
    inputs = dict(recovery=source, original_attempt=prefix, mechanics=mechanics)
    if any(output.resolve().is_relative_to(path.resolve()) for path in inputs.values()):
        raise ValueError("Evidence output must be outside all frozen input directories")
    verification = verify_recovery(source)
    input_hashes = {name: inventory(path, report_name="__include_every_file__") for name, path in inputs.items()}
    collection = source / "collection"
    rows, summary, csvs, tables = build_tables(source)
    output.mkdir(parents=True)
    recovery_report = json.loads((source / "report.json").read_text())
    for name, values in csvs.items(): csv_write(output / f"{name}.csv", values)
    version = figures(output, rows, summary, tables["contrasts"])
    shutil.copyfile(source / "manifest.json", output / "recovery_manifest.json")
    shutil.copyfile(source / "report.json", output / "recovery_report.json")
    for name in ("manifest.json", "report.json", "frozen_plans.json", "source_snapshot.zip"):
        shutil.copyfile(collection / name, output / ("collection_"+name))
    shutil.copyfile(source / "recovery_source_snapshot.zip", output / "recovery_source_snapshot.zip")
    shutil.copyfile(Path(__file__), output / "exporter_source.py")
    write(output / "scope.json", dict(complete=True, source_verification=verification, traffic_rollouts=0,
        publication_ready=False, policy_promoted=False, independent_arithmetic_quantities=len(tables["arithmetic_audit"]),
        arithmetic_absolute_tolerance="1e-10", decimal_sign_differences=tables["decimal_sign_differences"],
        frozen_contrasts=20, traffic_seeds=6, bootstrap_ordered_draws=64, scientific_panel_signal_samples=129600,
        original_attempt_budget_met=False, execution_budget_amended=True,
        original_elapsed_seconds=json.loads((prefix / "report.json").read_text())["elapsed_seconds"],
        recovery_elapsed_seconds=recovery_report["recovery_elapsed_seconds"],
        uncertainty=summary["uncertainty"], contrast_signs=summary["contrast_signs"],
        exploratory_scope="Service exposure and first-proposal splits are post-hoc diagnostics, not new frozen contrasts or causal full-run benefits. Later proposal differences compare diverged traffic states.",
        availability="Tables, figures and source/provenance copies only. Raw traces remain in the listed local inputs; this is not a standalone public raw-data release.",
        software=dict(python=sys.version, matplotlib=version)))
    if any(inventory(path, report_name="__include_every_file__") != input_hashes[name] for name, path in inputs.items()):
        raise ValueError("Input evidence changed during export; output is unsealed")
    manifest = dict(complete=True, input_directories={k: str(p.resolve()) for k, p in inputs.items()},
                    input_sha256=input_hashes, csv_rows={k: len(v) for k, v in csvs.items()},
                    output_sha256=inventory(output, report_name="manifest.json"))
    write(output / "manifest.json", manifest)
    return dict(complete=True, csv_rows=manifest["csv_rows"], independent_arithmetic_quantities=len(tables["arithmetic_audit"]),
                traffic_rollouts=0, publication_ready=False)


def verify(directory):
    """Check sealed export/input bytes and CSV arithmetic; raw replay occurred during export."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if not manifest["complete"] or inventory(directory, report_name="manifest.json") != manifest["output_sha256"]:
        raise ValueError("Export output coverage/hash mismatch")
    for name, path in manifest["input_directories"].items():
        if inventory(Path(path), report_name="__include_every_file__") != manifest["input_sha256"][name]:
            raise ValueError("Export input coverage/hash mismatch")
    source = Path(manifest["input_directories"]["recovery"])
    _, _, csvs, tables = build_tables(source)
    if manifest["csv_rows"] != {name: len(rows) for name, rows in csvs.items()}:
        raise ValueError("Changed export table coverage")
    for name, rows in csvs.items():
        with (directory / f"{name}.csv").open(newline="") as stream:
            actual = list(csv.DictReader(stream))
        if actual != [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows]:
            raise ValueError("Export CSV does not reconstruct")
    return dict(verified=True, independent_arithmetic_quantities=len(tables["arithmetic_audit"]),
                scope="Export and input hashes plus decimal numeric reconstruction. No new raw trajectory replay or traffic simulation.",
                independently_rerun_trajectories=0, publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.source and args.output is None: parser.error("--source requires --output")
    if args.verify and args.output is not None: parser.error("--output is only valid with --source")
    print(json.dumps(export(args.source, args.output) if args.source else verify(args.verify), indent=2))


if __name__ == "__main__":
    main()
