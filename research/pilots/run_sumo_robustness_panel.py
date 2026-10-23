"""Bounded initial-phase/horizon study with unchanged pressure/count policies."""
import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from research.analysis.sumo_robustness_metrics import check_mechanics, measurements, summarize
from research.audits.sumo_branch_feasibility import digest, file_hash, network
from research.experiments.sumo_robustness import ROOT, SOURCE_FILES, check_pins, configuration, episode, jobs, plans, trace_name, trim_plan
from research.policies.sumo_total_count import policy_for


def run(output, smoke=False):
    if output.exists():
        raise FileExistsError("Choose a new output directory; preserve old/partial evidence")
    if any((p/"report.json").exists() or (p/"manifest.json").exists() for p in output.resolve().parents):
        raise ValueError("Output must be outside recorded artifact directories")
    started = time.monotonic()
    import traci
    versions = {n: importlib.metadata.version(n) for n in ("eclipse-sumo", "traci", "sumolib")}
    binaries = {n: shutil.which(n, path=str(Path(sys.executable).parent)) for n in ("sumo", "netconvert")}
    if set(versions.values()) != {"1.24.0"} or not all(binaries.values()):
        raise ValueError("Requires the isolated SUMO/traci/sumolib 1.24.0 environment")
    check_pins()
    cfg, frozen, tasks = configuration(smoke), plans(smoke), jobs(smoke)
    lookup = {p["seed"]: p for p in frozen}
    output.mkdir(parents=True)
    manifest = dict(configuration=cfg, planned_jobs=tasks, versions=versions,
        source_hashes={name: file_hash(ROOT/name) for name in SOURCE_FILES},
        known_demand_families=True, learned_policy_evaluated=False,
        inference_boundary="canonical previous-step count packet and physical clock only")
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (output/"frozen_plans.json").write_text(json.dumps(frozen, indent=2)+"\n")
    schedule_hash = file_hash(output/"frozen_plans.json")
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in SOURCE_FILES:
            archive.write(ROOT/name, name)
    rows, conn, active = [], None, None
    report = dict(complete=False, robustness_complete=False, smoke=smoke, policy_promoted=False)
    def budget():
        if time.monotonic()-started > cfg["cap_seconds"]:
            raise TimeoutError("Frozen robustness collection cap exceeded")
    try:
        budget()
        network(output, binaries["netconvert"])
        command = [binaries["sumo"], "-n", str(output/"network.net.xml"), "-r", str(output/"routes.rou.xml"),
            "--step-length", ".1", "--seed", "110000", "--time-to-teleport", "-1", "--no-step-log", "true",
            "--duration-log.disable", "true", "--xml-validation", "never"]
        (output/"sumo_command.json").write_text(json.dumps(command, indent=2)+"\n")
        traci.start(command, label="robustness", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("robustness")
        axes = [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0, 0, 1, 1]:
            raise ValueError("Unexpected protected straight-movement mapping")
        for index, task in enumerate(tasks, start=1):
            budget()
            active = task
            plan = trim_plan(lookup[task["seed"]], task["steps"])
            conn.load(command[1:])
            trace, name = [], trace_name(task)
            with gzip.open(output/name, "xt") as stream:
                for frame in episode(conn, axes, plan, policy_for(task["controller"]), task["initial_phase"], budget):
                    stream.write(json.dumps(frame, sort_keys=True, allow_nan=False)+"\n")
                    trace.append(frame)
            measured = measurements(trace, plan, task, axes, cfg)
            row = dict(**task, family=plan["family"], trace=name, measurements=measured,
                requested_arrival_sha256=digest(plan["schedule"]), semantic_trace_sha256=digest(trace),
                prefix_semantic_trace_sha256=digest(trace[:cfg["endpoint_ticks"][0]]))
            rows.append(row)
            with (output/"runs.jsonl").open("a") as stream:
                stream.write(json.dumps(row, allow_nan=False)+"\n")
            print(f"Completed run {index}/{len(tasks)} (seed {task['seed']}, start {'EW' if task['initial_phase'] else 'NS'}, "
                  f"{task['controller']}, {task['kind']}, repeat {task['repeat']})", file=sys.stderr, flush=True)
        if len(rows) != cfg["planned_runs"] or file_hash(output/"frozen_plans.json") != schedule_hash:
            raise ValueError("Incomplete collection or changed schedules")
        mechanics = check_mechanics(rows, smoke)
        summary = summarize(rows, frozen, cfg)
        budget()
        report = dict(complete=True, robustness_complete=not smoke, smoke=smoke,
            traffic_seeds=len(frozen), paired_start_contexts=len(frozen)*2, runs=len(rows),
            executed_signal_samples=sum(r["steps"] for r in rows),
            measurement_endpoints_seconds=[n//10 for n in cfg["endpoint_ticks"]],
            primary_endpoint_seconds=cfg["steps"]//10, prefix_measurements_overlap=True,
            mechanics=mechanics, models_trained=0, policy_promoted=False, publication_ready=False,
            component_series_closed_on_completion=not smoke, **summary)
    except (Exception, KeyboardInterrupt) as exc:
        report = dict(complete=False, robustness_complete=False, smoke=smoke, completed_runs=len(rows),
            active_job=active, error=f"{type(exc).__name__}: {exc}", policy_promoted=False)
        raise
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception as exc:
            report.update(complete=False, robustness_complete=False, error=f"Connection close failed: {exc}")
            raise
        finally:
            report["elapsed_seconds"] = time.monotonic()-started
            report["output_hashes"] = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    report = run(args.output, args.smoke)
    selected = {k: report[k] for k in ("complete", "robustness_complete", "smoke", "traffic_seeds", "runs",
        "executed_signal_samples", "measurement_endpoints_seconds", "mechanics", "elapsed_seconds")}
    selected["endpoint_aggregate_comparisons"] = {key: value["aggregate"]["mean"] for key, value in report["endpoint_comparisons"].items()}
    print(json.dumps(selected, indent=2))


if __name__ == "__main__":
    main()
