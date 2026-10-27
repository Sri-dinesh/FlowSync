"""Retrospective waiting decomposition of the closed SUMO robustness panel."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import zipfile

from research.analysis.analyze_sumo_count_ablation import demand_role
from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_robustness import verify
from research.experiments.sumo_robustness import ROOT, SOURCE_FILES


SPECIFICATION = dict(
    retrospective=True, collection="sumo_robustness/full_20261023",
    primary_endpoint_seconds=360, cumulative_endpoints_seconds=[180, 360],
    disjoint_windows_seconds=[[0, 180], [180, 360]],
    contrast="total_incoming minus max_pressure; positive waiting differences are costs",
    weighting="Average starts within each traffic seed, then average seeds equally",
    questions=[
        "How do actual requested-vehicle shares combine axis waiting costs into overall mean cost?",
        "Does lower-rate-axis extra waiting also accumulate during seconds 180 to 360?",
    ],
    limits=[
        "Post hoc accounting of inspected data, not a new confirmatory experiment or causal intervention.",
        "Six traffic seeds; four asymmetric seeds. Starts and windows are dependent, not extra replicates.",
        "Equal-axis weighting changes the reporting objective, not the controller or measured traffic.",
        "Window wait includes carried vehicles and entry backlog; dividing by time gives average waiting inventory.",
        "No subtraction of percentiles or endpoint mean delays to infer window delay.",
        "No significance test, steady-state claim, policy promotion or established algorithmic novelty.",
    ],
)
AXES = ("ns", "ew")


def checked_profile(measurement):
    """Require an additive, nonempty axis partition with the recorded denominator."""
    axes, overall = measurement["axes"], measurement["overall"]
    for axis in AXES:
        group = axes[axis]
        count, wait = group["requested"], group["wait_vehicle_seconds"]
        if type(count) is not int or count <= 0 or not math.isfinite(wait) or wait < 0:
            raise ValueError("Invalid axis count/wait")
        if not math.isclose(wait/count, group["mean_wait_s"], rel_tol=0, abs_tol=1e-6):
            raise ValueError("Axis mean does not reconstruct")
    count = sum(axes[a]["requested"] for a in AXES)
    wait = sum(axes[a]["wait_vehicle_seconds"] for a in AXES)
    if count != overall["requested_vehicles"]:
        raise ValueError("Axis counts do not conserve requested vehicles")
    if not math.isclose(wait, overall["total_stopped_wait_vehicle_seconds"], rel_tol=0, abs_tol=1e-6):
        raise ValueError("Axis waiting does not conserve overall waiting")
    if not math.isclose(wait/count, overall["mean_stopped_wait_per_requested_vehicle_s"], rel_tol=0, abs_tol=1e-6):
        raise ValueError("Overall mean does not reconstruct")
    return count


def decompose(total, pressure, plan):
    count = checked_profile(total)
    if count != checked_profile(pressure):
        raise ValueError("Unpaired requested denominator")
    result = dict(requested=count)
    role_costs = {}
    for axis in AXES:
        a, b = total["axes"][axis], pressure["axes"][axis]
        if a["requested"] != b["requested"]:
            raise ValueError("Unpaired axis denominators")
        delta = a["wait_vehicle_seconds"]-b["wait_vehicle_seconds"]
        cost = delta/a["requested"]
        role = demand_role(plan, axis)
        result.update({f"{axis}_role": role, f"{axis}_requested_share": a["requested"]/count,
                       f"{axis}_mean_cost_s": cost, f"{axis}_contribution_s": delta/count})
        role_costs[role] = (cost, delta/count, a["requested"]/count)
    result["overall_mean_cost_s"] = sum(result[f"{a}_contribution_s"] for a in AXES)
    result["equal_axis_mean_cost_s"] = statistics.mean(result[f"{a}_mean_cost_s"] for a in AXES)
    direct = (total["overall"]["total_stopped_wait_vehicle_seconds"]
              - pressure["overall"]["total_stopped_wait_vehicle_seconds"])/count
    result["identity_residual_s"] = result["overall_mean_cost_s"]-direct
    if abs(result["identity_residual_s"]) > 1e-9:
        raise ValueError("Weighted waiting identity failed")
    for role in ("lower_demand", "higher_demand"):
        values = role_costs.get(role, (None, None, None))
        for name, value in zip(("mean_cost_s", "contribution_s", "requested_share"), values):
            result[f"{role}_{name}"] = value
    return result


def window_cost(total, pressure, start, end, plan):
    """Subtract integrals, not means; vehicles may wait in both disjoint windows."""
    result = {}
    for axis in AXES:
        waits = []
        for measurements in (total, pressure):
            later = measurements[str(end)]["axes"][axis]["wait_vehicle_seconds"]
            earlier = measurements[str(start)]["axes"][axis]["wait_vehicle_seconds"] if start else 0
            if later < earlier:
                raise ValueError("Cumulative waiting decreased")
            waits.append(later-earlier)
        cost = waits[0]-waits[1]
        result[f"{axis}_wait_cost_vehicle_seconds"] = cost
        result[f"{axis}_average_waiting_inventory_cost"] = cost/(end-start)
        role = demand_role(plan, axis)
        if role != "balanced":
            result[f"{role}_average_waiting_inventory_cost"] = cost/(end-start)
    result["overall_wait_cost_vehicle_seconds"] = sum(result[f"{a}_wait_cost_vehicle_seconds"] for a in AXES)
    result["overall_average_waiting_inventory_cost"] = result["overall_wait_cost_vehicle_seconds"]/(end-start)
    for role in ("lower_demand", "higher_demand"):
        result.setdefault(f"{role}_average_waiting_inventory_cost", None)
    return result


def aggregate(rows, fields):
    """Keep both starts in every seed; do not pool vehicles or contexts as seeds."""
    seeds = []
    for seed in sorted({r["seed"] for r in rows}):
        selected = [r for r in rows if r["seed"] == seed]
        if len(selected) != 2 or {r["initial_phase"] for r in selected} != {0, 1}:
            raise ValueError("Every seed must retain both initial phases exactly once")
        seeds.append(dict(seed=seed, family=selected[0]["family"], **{
            key: statistics.mean(r[key] for r in selected) for key in fields}))
    if not seeds:
        raise ValueError("Empty summary")
    return dict(traffic_seeds=len(seeds), paired_start_contexts=len(rows), seed_results=seeds,
                mean={k: statistics.mean(r[k] for r in seeds) for k in fields})


def analyse(runs, plans):
    lookup = {(r["seed"], r["initial_phase"], r["controller"]): r for r in runs}
    expected = {(p["seed"], phase, c) for p in plans for phase in (0, 1)
                for c in ("total_incoming", "max_pressure")}
    if len(lookup) != len(runs) or set(lookup) != expected:
        raise ValueError("Incomplete or duplicate paired runs")
    endpoints, windows = [], []
    for plan in plans:
        for phase in (0, 1):
            a, b = (lookup[plan["seed"], phase, c]["measurements"] for c in ("total_incoming", "max_pressure"))
            common = dict(seed=plan["seed"], family=plan["family"], initial_phase=phase)
            for end in SPECIFICATION["cumulative_endpoints_seconds"]:
                endpoints.append(dict(**common, endpoint_seconds=end, **decompose(a[str(end)], b[str(end)], plan)))
            for start, end in SPECIFICATION["disjoint_windows_seconds"]:
                windows.append(dict(**common, start_seconds=start, end_seconds=end, **window_cost(a, b, start, end, plan)))
    summaries = {}
    for endpoint in SPECIFICATION["cumulative_endpoints_seconds"]:
        selected = [r for r in endpoints if r["endpoint_seconds"] == endpoint]
        fields = ["overall_mean_cost_s", "equal_axis_mean_cost_s", "ns_contribution_s", "ew_contribution_s"]
        asymmetric = [r for r in selected if r["lower_demand_mean_cost_s"] is not None]
        roles = [f"{role}_{field}" for role in ("lower_demand", "higher_demand")
                 for field in ("mean_cost_s", "contribution_s", "requested_share")]
        summaries[str(endpoint)] = dict(all=aggregate(selected, fields), asymmetric=aggregate(asymmetric, fields+roles),
            balanced=aggregate([r for r in selected if r["lower_demand_mean_cost_s"] is None], fields))
    window_summaries = {}
    for start, end in SPECIFICATION["disjoint_windows_seconds"]:
        selected = [r for r in windows if r["start_seconds"] == start and r["end_seconds"] == end]
        asymmetric = [r for r in selected if r["lower_demand_average_waiting_inventory_cost"] is not None]
        field = "overall_average_waiting_inventory_cost"
        roles = [f"{role}_average_waiting_inventory_cost" for role in ("lower_demand", "higher_demand")]
        window_summaries[f"{start}-{end}"] = dict(all=aggregate(selected, [field]),
            asymmetric=aggregate(asymmetric, [field, *roles]),
            asymmetric_contexts_with_lower_demand_wait_increase=sum(r[roles[0]] > 1e-9 for r in asymmetric),
            asymmetric_contexts_with_higher_demand_wait_decrease=sum(r[roles[1]] < -1e-9 for r in asymmetric))
    return dict(endpoints=endpoints, windows=windows, endpoint_summary=summaries, window_summary=window_summaries)


def figure(analysis, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = analysis["endpoint_summary"]["360"]["all"]["seed_results"]
    x = list(range(len(rows)))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout="constrained")
    ax = axes[0]
    for offset, axis, color in ((-.18, "ns", "#0072B2"), (.18, "ew", "#D55E00")):
        ax.bar([i+offset for i in x], [r[f"{axis}_contribution_s"] for r in rows],
               width=.34, label=f"{axis.upper()} weighted contribution", color=color)
    ax.scatter(x, [r["overall_mean_cost_s"] for r in rows], marker="D", color="black", s=24, label="Overall cost", zorder=3)
    ax.set(title="360 s: axis costs combine into the overall mean", ylabel="Extra stopped wait per requested vehicle (s)")
    ax = axes[1]
    for offset, window, color in ((-.18, "0-180", "#0072B2"), (.18, "180-360", "#D55E00")):
        values = analysis["window_summary"][window]["all"]["seed_results"]
        ax.bar([i+offset for i in x], [r["overall_average_waiting_inventory_cost"] for r in values],
               width=.34, label=f"{window} s", color=color)
    ax.set(title="Waiting also changes after the initial 180 s", ylabel="Extra average waiting inventory (vehicles)")
    labels = [f"{r['seed']}\n{r['family'].replace('_dominant', ' heavy')}" for r in rows]
    for ax in axes:
        ax.axhline(0, color="#555555", linewidth=.7)
        ax.set_xticks(x, labels, fontsize=8)
        ax.legend(fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Total incoming counts minus Max-Pressure; two starts averaged within each seed", fontsize=11)
    for extension in ("png", "svg", "pdf"):
        fig.savefig(output/f"waiting_accounting.{extension}", dpi=180)
    plt.close(fig)


def run(directory, output):
    if output.exists():
        raise FileExistsError("Choose a new analysis directory")
    if output.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Analysis must remain outside the frozen collection")
    saved = json.loads((directory/"report.json").read_text())
    inputs = {name: file_hash(directory/name) for name in ("report.json", *saved["output_hashes"])}
    verification = verify(directory)
    if verification["smoke"] or not saved["component_series_closed_on_completion"]:
        raise ValueError("Requires the completed, closed full robustness study")
    plans = json.loads((directory/"frozen_plans.json").read_text())
    runs = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    result = analyse(runs, plans)
    if any(file_hash(directory/name) != sha for name, sha in inputs.items()):
        raise ValueError("Input evidence changed during analysis")
    output.mkdir(parents=True, exist_ok=False)
    for table in ("endpoints", "windows"):
        with (output/f"{table}.csv").open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(result[table][0]))
            writer.writeheader()
            writer.writerows(result[table])
    figure(result, output)
    source_names = sorted(set(SOURCE_FILES) | {Path(__file__).resolve().relative_to(ROOT).as_posix()})
    with zipfile.ZipFile(output/"analysis_source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in source_names:
            archive.write(ROOT/name, name)
    if any(file_hash(directory/name) != sha for name, sha in inputs.items()):
        raise ValueError("Input evidence changed during export")
    report = dict(complete=True, specification=SPECIFICATION, traffic_rollouts=0, models_trained=0,
        independently_rerun_trajectories=0, policy_promoted=False, publication_ready=False,
        verification=verification, input_sha256=inputs,
        analysis_source_sha256={name: file_hash(ROOT/name) for name in source_names},
        csv_rows={table: len(result[table]) for table in ("endpoints", "windows")},
        max_identity_residual_s=max(abs(r["identity_residual_s"]) for r in result["endpoints"]),
        endpoint_summary=result["endpoint_summary"], window_summary=result["window_summary"],
        output_sha256={p.name: file_hash(p) for p in sorted(output.iterdir())})
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.directory, args.output)
    print(json.dumps({k: result[k] for k in ("complete", "traffic_rollouts", "csv_rows", "max_identity_residual_s")}, indent=2))


if __name__ == "__main__":
    main()
