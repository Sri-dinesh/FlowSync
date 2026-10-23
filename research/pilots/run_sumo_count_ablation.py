"""Execute only the new total-count arm against anchored classical SUMO results."""
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

from research.analysis.sumo_count_metrics import summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.experiments.sumo_count_ablation import (
    ROOT, SOURCE_FILES, command_for, configuration, ensure_reference_unchanged, jobs, load_reference, trace_name,
)
from research.experiments.sumo_observed_episode import episode, validate_trace
from research.policies.sumo_total_count import policy_for


def run(reference_directory, output, smoke=False):
    if output.exists():
        raise FileExistsError("Use a new output directory; preserve completed/partial evidence")
    if output.resolve().is_relative_to(reference_directory.resolve()):
        raise ValueError("Output must be outside the frozen reference directory")
    started = time.monotonic()
    import traci
    versions = {name: importlib.metadata.version(name) for name in ("eclipse-sumo", "traci", "sumolib")}
    binary = shutil.which("sumo", path=str(Path(sys.executable).parent))
    if set(versions.values()) != {"1.24.0"} or not binary:
        raise ValueError("Requires the isolated pinned SUMO/traci/sumolib 1.24.0 environment")
    cfg = configuration(smoke)
    reference = load_reference(reference_directory, smoke)
    frozen, tasks = reference["plans"], jobs(reference["plans"], smoke)
    lookup = {p["seed"]: p for p in frozen}
    output.mkdir(parents=True)
    manifest = dict(configuration=cfg, versions=versions, planned_jobs=tasks,
        reference_directory=str(reference_directory), reference_input_sha256=reference["hashes"],
        reference_manifest_sha256=file_hash(reference_directory/"manifest.json"),
        source_hashes={name: file_hash(ROOT/name) for name in SOURCE_FILES},
        learned_policy_evaluated=False, reused_development_cases=True)
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (output/"frozen_plans.json").write_bytes((reference_directory/"frozen_plans.json").read_bytes())
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in SOURCE_FILES:
            archive.write(ROOT/name, name)
    rows, conn, active_job = [], None, None
    report = dict(complete=False, comparison_complete=False, smoke=smoke, policy_promoted=False)
    def budget():
        if time.monotonic()-started > cfg["cap_seconds"]:
            raise TimeoutError("Frozen total-count collection cap exceeded")
    try:
        budget()
        for name in ("network.net.xml", "routes.rou.xml"):
            (output/name).write_bytes((reference_directory/name).read_bytes())
        command = command_for(reference, output, binary)
        (output/"sumo_command.json").write_text(json.dumps(command, indent=2)+"\n")
        traci.start(command, label="count_ablation", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("count_ablation")
        axes = [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0, 0, 1, 1]:
            raise ValueError("Unexpected straight-movement mapping")
        repeats = {}
        for index, task in enumerate(tasks, start=1):
            budget()
            active_job = task
            plan, name = lookup[task["seed"]], trace_name(task)
            conn.load(command[1:])
            policy = policy_for(task["controller"])
            trace = []
            with gzip.open(output/name, "xt") as stream:
                for frame in episode(conn, axes, plan, policy, budget):
                    stream.write(json.dumps(frame, sort_keys=True, allow_nan=False)+"\n")
                    trace.append(frame)
            metrics = validate_trace(trace, plan["schedule"], policy, axes, cfg["steps"])
            semantic = digest(trace)
            if task["controller"] == "max_pressure":
                anchor = next(r for r in reference["rows"] if r["seed"] == task["seed"]
                              and r["controller"] == "max_pressure" and r["repeat"] == 0)
                if semantic != anchor["semantic_trace_sha256"]:
                    raise ValueError("New runtime does not reproduce the original Max-Pressure trace")
            key = (task["seed"], task["controller"])
            if repeats.setdefault(key, semantic) != semantic:
                raise ValueError("Repeated total-count trajectory mismatch")
            row = dict(**task, family=plan["family"], trace=name, metrics=metrics,
                       semantic_trace_sha256=semantic, requested_arrival_sha256=digest(plan["schedule"]))
            rows.append(row)
            with (output/"runs.jsonl").open("a") as stream:
                stream.write(json.dumps(row, allow_nan=False)+"\n")
            print(f"Completed run {index}/{len(tasks)} ({task['controller']}, seed {task['seed']}, repeat {task['repeat']})",
                  file=sys.stderr, flush=True)
        if [(r["seed"], r["controller"], r["repeat"]) for r in rows] != [
                (t["seed"], t["controller"], t["repeat"]) for t in tasks]:
            raise ValueError("Incomplete/duplicate planned jobs")
        if file_hash(output/"frozen_plans.json") != reference["hashes"]["frozen_plans.json"]:
            raise ValueError("Frozen schedules changed")
        ensure_reference_unchanged(reference_directory, reference)
        budget()
        report = dict(complete=True, comparison_complete=not smoke, smoke=smoke, cases=len(frozen),
            new_runs=len(rows), new_signal_samples=sum(r["metrics"]["signal_samples"] for r in rows),
            reference_runs=reference["verification"]["runs"], reference_signal_samples=reference["verification"]["signal_samples"],
            anchor_replay_verified=smoke, total_repeat_verified=smoke,
            models_trained=0, policy_promoted=False, reused_development_cases=True,
            **summarize(rows, reference["rows"], frozen, smoke))
    except (Exception, KeyboardInterrupt) as exc:
        report = dict(complete=False, comparison_complete=False, smoke=smoke, completed_runs=len(rows),
                      active_job=active_job, error=f"{type(exc).__name__}: {exc}", policy_promoted=False)
        raise
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception as exc:
            report.update(complete=False, comparison_complete=False, error=f"Connection close failed: {exc}")
            raise
        finally:
            report["elapsed_seconds"] = time.monotonic()-started
            report["output_hashes"] = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    report = run(args.reference, args.output, args.smoke)
    selected = {key: report[key] for key in ("complete", "comparison_complete", "smoke", "cases", "new_runs",
        "new_signal_samples", "reference_runs", "reference_signal_samples", "anchor_replay_verified",
        "total_repeat_verified", "elapsed_seconds", "controller_means")}
    selected["comparisons"] = [{key: row[key] for key in ("reference", "primary", "mean", "direction_counts")}
                               for row in report["comparisons"]]
    print(json.dumps(selected, indent=2))


if __name__ == "__main__":
    main()
