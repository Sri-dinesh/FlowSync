"""Attribute the completed count ablation's waiting/trip trade-off; no rollouts."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
import zipfile

from research.analysis.sumo_classical_metrics import percentile95
from research.analysis.sumo_trace_metrics import signal_partition
from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_count_ablation import verify
from research.audits.verify_sumo_future_panel import read_trace
from research.experiments.sumo_count_ablation import ROOT, SOURCE_FILES

AXES = ("ns", "ew")


def profile(trace, schedule):
    """Accumulated stopped wait and green absence, including unfinished requests.

    Called after full raw verification. Green absence is a phase measurement,
    not a vehicle's waiting time or a claim that no vehicle crossed on yellow.
    """
    if not trace or [r["tick"] for r in trace] != list(range(len(trace))):
        raise ValueError("Requires a complete ordered episode starting at zero")
    origins = {a[2]: ("ns" if a[1] in "ns" else "ew") for a in schedule}
    if not schedule or len(origins) != len(schedule) or any(a[1] not in ("n", "s", "e", "w") for a in schedule):
        raise ValueError("Invalid/duplicate requested origins")
    expected = {}
    for request in schedule:
        expected.setdefault(request[0], []).append(request)
    waits, completed, requested = Counter(), set(), set()
    absence, demanded, longest, longest_demanded = ([0, 0] for _ in range(4))
    for row in trace:
        if row["requested"] != expected.get(row["tick"], []):
            raise ValueError("Changed requested schedule")
        new_ids = {a[2] for a in row["requested"]}
        if new_ids & requested:
            raise ValueError("Repeated requested vehicle")
        requested |= new_ids
        active = [v[0] for v in row["vehicles"]]
        queued = [a[2] for a in row["pending"]]
        arrived = set(row["arrived"])
        if (len(set(active+queued)) != len(active+queued) or len(arrived) != len(row["arrived"])
                or arrived & completed or not arrived <= requested):
            raise ValueError("Duplicate or unknown inventory/completion")
        completed |= arrived
        if set(active+queued) & completed or requested != set(active+queued) | completed:
            raise ValueError("Requested/active/pending/completed inventory mismatch")
        stopped, waiting_axis = [], Counter()
        for vid, edge, _position, speed in row["vehicles"]:
            if not math.isfinite(speed) or speed < 0 or vid not in origins:
                raise ValueError("Invalid vehicle speed or missing origin")
            if speed < .1:
                stopped.append(vid)
                if edge.endswith("_in"):
                    waiting_axis[origins[vid]] += 1
        for vid in queued:
            if vid not in origins:
                raise ValueError("Missing queued origin")
            waiting_axis[origins[vid]] += 1
            stopped.append(vid)
        if round(len(stopped)/10, 6) != row["wait_vehicle_seconds"]:
            raise ValueError("Stopped waiting does not reconstruct")
        waits.update(stopped)
        signal = row["fsm"]
        for i, axis in enumerate(AXES):
            green = signal["stage"] == "green" and signal["phase"] == i
            absence[i] = 0 if green else absence[i]+1
            demanded[i] = 0 if green or not waiting_axis[axis] else demanded[i]+1
            longest[i] = max(longest[i], absence[i])
            longest_demanded[i] = max(longest_demanded[i], demanded[i])
    if requested != set(origins):
        raise ValueError("Requested schedule extends beyond observed horizon")
    vehicles = {vid: dict(axis=axis, wait_s=waits[vid]/10, completed=vid in completed) for vid, axis in origins.items()}
    groups = {}
    for i, axis in enumerate(AXES):
        members = [v for v in vehicles.values() if v["axis"] == axis]
        values = [v["wait_s"] for v in members]
        ticks = sum(waits[vid] for vid in origins if origins[vid] == axis)
        groups[axis] = dict(requested=len(members), completed_trips=sum(v["completed"] for v in members),
            wait_vehicle_seconds=ticks/10, mean_wait_s=ticks/10/len(members) if members else 0.,
            p95_wait_s=percentile95(values), max_wait_s=max(values, default=0.),
            longest_green_absence_s=longest[i]/10,
            longest_green_absence_with_stopped_demand_s=longest_demanded[i]/10)
    return dict(axes=groups, vehicles=vehicles, wait_vehicle_seconds=sum(waits.values())/10,
                signal=signal_partition(trace))


def demand_role(plan, axis):
    if plan["ns_rate"] == plan["ew_rate"]:
        return "balanced"
    lower = "ns" if plan["ns_rate"] < plan["ew_rate"] else "ew"
    return "lower_demand" if axis == lower else "higher_demand"


def paired_vehicles(total, pressure, plan):
    if total.keys() != pressure.keys():
        raise ValueError("Policies do not have paired requested vehicles")
    rows = []
    for vid in sorted(total):
        a, b = total[vid], pressure[vid]
        if a["axis"] != b["axis"]:
            raise ValueError("Requested route origin changed")
        rows.append(dict(seed=plan["seed"], family=plan["family"], vehicle=vid, axis=a["axis"],
            role=demand_role(plan, a["axis"]), total_wait_s=a["wait_s"], pressure_wait_s=b["wait_s"],
            wait_saved_s=round(b["wait_s"]-a["wait_s"], 6),
            total_completed=a["completed"], pressure_completed=b["completed"]))
    return rows


def run(directory, reference, output):
    if output.exists():
        raise FileExistsError("Choose a new analysis output directory")
    if any(output.resolve().is_relative_to(p.resolve()) for p in (directory, reference)):
        raise ValueError("Output must be outside both frozen input directories")
    verification = verify(directory, reference)
    if verification["smoke"]:
        raise ValueError("Requires the completed full component experiment")
    input_hashes = {}
    for label, path in (("count", directory), ("classical", reference)):
        saved = json.loads((path/"report.json").read_text())
        input_hashes[label] = {name: file_hash(path/name) for name in ("report.json", *saved["output_hashes"])}
    frozen = json.loads((directory/"frozen_plans.json").read_text())
    count_report = json.loads((directory/"report.json").read_text())
    new = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    old = [json.loads(line) for line in (reference/"runs.jsonl").read_text().splitlines()]
    lookup = {(r["seed"], r["controller"]): (path, r)
              for path, rows in ((directory, new), (reference, old)) for r in rows if r["repeat"] == 0}
    axes, pairs, signals = [], [], []
    for plan in frozen:
        measured = {}
        for controller in ("total_incoming", "max_pressure"):
            path, row = lookup[plan["seed"], controller]
            values = profile(read_trace(path/row["trace"]), plan["schedule"])
            if abs(values["wait_vehicle_seconds"]-row["metrics"]["total_stopped_wait_vehicle_seconds"]) > 1e-6:
                raise ValueError("Wait attribution differs from verified metrics")
            measured[controller] = values
            for axis, metrics in values["axes"].items():
                axes.append(dict(seed=plan["seed"], family=plan["family"], controller=controller,
                                 axis=axis, role=demand_role(plan, axis), **metrics))
            signals.append(dict(seed=plan["seed"], family=plan["family"], controller=controller,
                                seconds=values["signal"]["seconds"], switch_onsets=values["signal"]["switch_onsets"]))
        paired = paired_vehicles(measured["total_incoming"]["vehicles"], measured["max_pressure"]["vehicles"], plan)
        expected_saved = measured["max_pressure"]["wait_vehicle_seconds"]-measured["total_incoming"]["wait_vehicle_seconds"]
        if abs(sum(r["wait_saved_s"] for r in paired)-expected_saved) > 1e-6:
            raise ValueError("Paired vehicle waiting does not conserve the saved integral")
        pairs.extend(paired)
    summaries = {}
    for controller in ("total_incoming", "max_pressure"):
        summaries[controller] = {}
        for role in ("balanced", "lower_demand", "higher_demand"):
            selected = [r for r in axes if r["controller"] == controller and r["role"] == role]
            summaries[controller][role] = dict(case_axes=len(selected), **{key: statistics.mean(r[key] for r in selected)
                for key in ("mean_wait_s", "p95_wait_s", "max_wait_s", "completed_trips", "longest_green_absence_s",
                            "longest_green_absence_with_stopped_demand_s")})
    for label, path in (("count", directory), ("classical", reference)):
        if any(file_hash(path/name) != sha for name, sha in input_hashes[label].items()):
            raise ValueError("Input evidence changed during analysis")
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in (("case_axes.csv", axes), ("paired_vehicles.csv", pairs)):
        with (output/name).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (output/"signals.json").write_text(json.dumps(signals, indent=2)+"\n")
    sources = (*SOURCE_FILES, "research/analysis/analyze_sumo_count_ablation.py")
    with zipfile.ZipFile(output/"analysis_source.zip", "w") as archive:
        for name in sources:
            archive.write(ROOT/name, name)
    report = dict(complete=True, cases=len(frozen), analysed_policy_runs=len(frozen)*2,
        traffic_rollouts=0, policy_promoted=False, verification=verification,
        primary=count_report["comparisons"][0], by_controller_and_role=summaries,
        requested_vehicle_pairs=len(pairs),
        paired_vehicle_counts=dict(wait_improved=sum(r["wait_saved_s"] > 0 for r in pairs),
            wait_equal=sum(r["wait_saved_s"] == 0 for r in pairs), wait_worsened=sum(r["wait_saved_s"] < 0 for r in pairs),
            additional_completions=sum(r["total_completed"] and not r["pressure_completed"] for r in pairs),
            lost_completions=sum(r["pressure_completed"] and not r["total_completed"] for r in pairs)),
        input_sha256=input_hashes, analysis_source_sha256={name: file_hash(ROOT/name) for name in sources},
        output_sha256={p.name: file_hash(p) for p in output.iterdir() if p.is_file()},
        scope="Post-hoc attribution on consumed development cases; no new simulation or fitted policy. "
              "Demand role follows declared family rates and is evaluation-only. Axis/vehicle waits are accumulated "
              "stopped waiting, including external backlog and unfinished requests. Green absence is a phase exposure, "
              "not individual waiting or zero yellow discharge. Averages weight case-axis groups equally; no pooled p95, "
              "independent vehicle/frame samples, isolated timing cause or fresh final test is claimed.")
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.directory, args.reference, args.output)
    print(json.dumps({k: result[k] for k in ("complete", "cases", "analysed_policy_runs", "traffic_rollouts",
                                           "by_controller_and_role", "paired_vehicle_counts")}, indent=2))


if __name__ == "__main__":
    main()
