"""Read-only classical SUMO diagnosis on verified, already consumed trajectories."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics
import zipfile

from research.analysis.sumo_trace_metrics import signal_partition
from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_classical_panel import verify
from research.audits.verify_sumo_future_panel import read_trace
from research.experiments.sumo_classical_runtime import SOURCE_FILES
from research.policies.sumo_classical import Clock, Counts, choose_action

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = ("all_agree", "total_and_pressure_agree", "halted_and_total_agree", "halted_and_pressure_agree")


def decision_comparison(decision):
    """Same delivered packet/context, without executing a counterfactual action."""
    packet = Counts.from_dict(decision["packet"])
    fsm = decision["before_fsm"]
    clock = Clock(fsm["phase"], fsm["stage"], fsm["age"])
    eligible = clock.stage == "green" and clock.age >= 80
    totals = (sum(packet.incoming[:2]), sum(packet.incoming[2:]))
    total = clock.phase if not eligible or totals[clock.phase] == max(totals) else int(totals[1] > totals[0])
    halted, pressure = (choose_action(c, packet, clock) for c in ("halted", "max_pressure"))
    pattern = ("all_agree" if halted == total == pressure else "total_and_pressure_agree" if total == pressure
               else "halted_and_total_agree" if halted == total else "halted_and_pressure_agree")
    return dict(eligible=eligible, halted=halted, total_incoming=total, max_pressure=pressure, pattern=pattern,
                halted_differs_total=halted != total, total_differs_pressure=total != pressure,
                halted_differs_pressure=halted != pressure)


def trace_measurements(trace, schedule):
    """Disjoint wait partitions; origin/location partitions describe the same wait."""
    origins = {a[2]: a[1] for a in schedule}
    if len(origins) != len(schedule) or not trace:
        raise ValueError("Requires unique requested vehicles and a nonempty trace")
    origin_ticks, location_ticks, decisions = Counter(), Counter(), Counter()
    for row in trace:
        stopped = [(v[0], "incoming" if v[1].endswith("_in") else "outgoing" if v[1].endswith("_out") else "internal")
                   for v in row["vehicles"] if v[3] < .1]
        stopped += [(a[2], "entry_backlog") for a in row["pending"]]
        if len({v[0] for v in stopped}) != len(stopped) or round(len(stopped)/10, 6) != row["wait_vehicle_seconds"]:
            raise ValueError("Stopped-wait attribution does not reconstruct")
        for vid, location in stopped:
            if vid not in origins:
                raise ValueError("Missing requested origin")
            origin_ticks[origins[vid]] += 1
            location_ticks[location] += 1
        if "decision" in row:
            compared = decision_comparison(row["decision"])
            decisions["all_decisions"] += 1
            if compared["eligible"]:
                decisions["eligible_decisions"] += 1
                decisions[compared["pattern"]] += 1
                for field in ("halted_differs_total", "total_differs_pressure", "halted_differs_pressure"):
                    decisions[field] += compared[field]
    if sum(origin_ticks.values()) != sum(location_ticks.values()):
        raise ValueError("Origin/location waiting partitions disagree")
    signal = signal_partition(trace)
    return dict(wait_vehicle_seconds=sum(origin_ticks.values())/10,
                wait_by_origin={d: origin_ticks[d]/10 for d in "nsew"},
                wait_by_location={k: location_ticks[k]/10 for k in ("incoming", "outgoing", "internal", "entry_backlog")},
                signals=dict(seconds=signal["seconds"], switch_onsets=signal["switch_onsets"]),
                decisions={k: decisions[k] for k in ("all_decisions", "eligible_decisions", *PATTERNS,
                           "halted_differs_total", "total_differs_pressure", "halted_differs_pressure")})


def first_proposal_split(left, right):
    """Check identical histories until the first differing executed policy proposal."""
    if len(left) != len(right):
        raise ValueError("Unpaired whole-episode horizons")
    for a, b in zip(left, right):
        if a == b:
            continue
        x, y = a.get("decision"), b.get("decision")
        if (x is None or y is None or x["packet"] != y["packet"] or x["before_fsm"] != y["before_fsm"]
                or x["proposal"] == y["proposal"] or a["tick"] != b["tick"]):
            raise ValueError("Trajectories diverged before an observed proposal split")
        return dict(tick=a["tick"], packet=x["packet"], before_fsm=x["before_fsm"],
                    halted_proposal=x["proposal"], pressure_proposal=y["proposal"], **decision_comparison(x))
    return None


def contrast_summary(cases):
    if not cases:
        raise ValueError("No paired cases")
    fields = ("mean_wait_saved_s", "p95_wait_saved_s", "completed_trips_gained")
    return dict(cases=len(cases),
        mean={k: statistics.mean(row[k] for row in cases) for k in fields},
        direction_counts={k: dict(improved=sum(row[k] > 0 for row in cases),
                                 equal=sum(row[k] == 0 for row in cases),
                                 worsened=sum(row[k] < 0 for row in cases)) for k in fields},
        lower_mean_wait_without_p95_or_trip_loss=sum(row[fields[0]] > 0 and all(row[k] >= 0 for k in fields[1:])
                                                   for row in cases),
        regression_cases=[{k: row[k] for k in ("seed", "family", *fields)}
                          for row in cases if any(row[k] < 0 for k in fields)])


def run(directory, output):
    if output.exists():
        raise FileExistsError("Use a new analysis directory")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Analysis output must be outside the frozen input directory")
    verification = verify(directory)
    if verification["smoke"]:
        raise ValueError("Requires the completed full classical comparison")
    saved_report = json.loads((directory/"report.json").read_text())
    inputs = {name: file_hash(directory/name) for name in ("report.json", *saved_report["output_hashes"])}
    plans = json.loads((directory/"frozen_plans.json").read_text())
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    lookup = {(r["seed"], r["controller"]): r for r in rows}
    measurements, cases, splits = [], [], []
    for plan in plans:
        traces, measured = {}, {}
        for controller in ("halted", "fixed", "max_pressure"):
            row = lookup[plan["seed"], controller]
            trace = read_trace(directory/row["trace"])
            values = trace_measurements(trace, plan["schedule"])
            if abs(values["wait_vehicle_seconds"]-row["metrics"]["total_stopped_wait_vehicle_seconds"]) > 1e-6:
                raise ValueError("Waiting partitions differ from verified primary metrics")
            measurements.append(dict(seed=plan["seed"], family=plan["family"], controller=controller, **values))
            traces[controller], measured[controller] = trace, values
        split = first_proposal_split(traces["halted"], traces["max_pressure"])
        splits.append(dict(seed=plan["seed"], family=plan["family"], first_split=split))
        for reference in ("halted", "fixed"):
            old, pressure = (lookup[plan["seed"], c]["metrics"] for c in (reference, "max_pressure"))
            paired = dict(seed=plan["seed"], family=plan["family"], reference=reference,
                requested=old["requested_vehicles"],
                mean_wait_saved_s=round(old["mean_stopped_wait_per_requested_vehicle_s"]-pressure["mean_stopped_wait_per_requested_vehicle_s"], 6),
                p95_wait_saved_s=round(old["p95_accumulated_wait_s"]-pressure["p95_accumulated_wait_s"], 6),
                completed_trips_gained=pressure["completed_trips"]-old["completed_trips"],
                wait_vehicle_seconds_saved=round(measured[reference]["wait_vehicle_seconds"]-measured["max_pressure"]["wait_vehicle_seconds"], 6))
            for partition in ("origin", "location"):
                values = {key: round(value-measured["max_pressure"]["wait_by_"+partition][key], 6)
                          for key, value in measured[reference]["wait_by_"+partition].items()}
                if abs(sum(values.values())-paired["wait_vehicle_seconds_saved"]) > 1e-6:
                    raise ValueError("Paired waiting attribution does not conserve saved delay")
                paired.update({f"saved_{partition}_{key}_vehicle_seconds": value for key, value in values.items()})
            cases.append(paired)
    controllers = saved_report["controllers"]
    pressure_mean = controllers["max_pressure"]["mean_stopped_wait_per_requested_vehicle_s"]
    contrasts = {c: dict(**contrast_summary([r for r in cases if r["reference"] == c]),
        mean_wait_reduction_percent=100*(1-pressure_mean/controllers[c]["mean_stopped_wait_per_requested_vehicle_s"]))
        for c in ("halted", "fixed")}
    by_controller = {}
    for controller in controllers:
        values = [r for r in measurements if r["controller"] == controller]
        keys = values[0]["decisions"]
        by_controller[controller] = dict(decisions={k: sum(r["decisions"][k] for r in values) for k in keys},
            mean_wait_by_location_vehicle_seconds={k: statistics.mean(r["wait_by_location"][k] for r in values)
                                                   for k in values[0]["wait_by_location"]},
            mean_signal_seconds={k: statistics.mean(r["signals"]["seconds"][k] for r in values)
                                 for k in values[0]["signals"]["seconds"]})
    if any(file_hash(directory/name) != sha for name, sha in inputs.items()):
        raise ValueError("Input evidence changed during analysis")
    output.mkdir(parents=True, exist_ok=False)
    with (output/"paired_cases.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(cases)
    for name, values in (("trace_measurements.json", measurements), ("first_proposal_splits.json", splits)):
        (output/name).write_text(json.dumps(values, indent=2, allow_nan=False)+"\n")
    analysis_sources = (*SOURCE_FILES, "research/analysis/analyze_sumo_classical_panel.py", "research/analysis/sumo_trace_metrics.py")
    with zipfile.ZipFile(output/"analysis_source.zip", "w") as archive:
        for name in analysis_sources:
            archive.write(ROOT/name, name)
    report = dict(complete=True, cases=len(plans), analysed_runs=len(rows), traffic_rollouts=0, models_fitted=0,
        policy_promoted=False, verification=verification, comparisons=contrasts, by_controller=by_controller,
        input_sha256=inputs, analysis_source_sha256={name: file_hash(ROOT/name) for name in analysis_sources},
        scope="Descriptive analysis of consumed development cases. Same-state proposal differences do not "
              "measure counterfactual traffic benefit or isolate moving-count/outgoing-count causes. "
              "Decision frames are correlated; origin and location are separate partitions of the same waiting. "
              "No new traffic, hypothesis test, RL transfer or policy promotion.",
        output_sha256={p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.directory, args.output)
    print(json.dumps({key: report[key] for key in ("complete", "cases", "analysed_runs", "traffic_rollouts", "comparisons")}, indent=2))


if __name__ == "__main__":
    main()
