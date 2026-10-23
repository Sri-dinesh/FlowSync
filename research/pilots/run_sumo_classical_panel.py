"""Execute matched whole-episode Fixed/halted/Max-Pressure SUMO baselines."""
from __future__ import annotations

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

from research.analysis.sumo_classical_metrics import summarize, validate_trace
from research.audits.sumo_branch_feasibility import digest, file_hash, network
from research.experiments.sumo_classical_runtime import SOURCE_FILES, configuration, episode, plans
from research.policies.sumo_classical import CONTROLLERS

ROOT = Path(__file__).resolve().parents[2]


def run(output, smoke=False):
    if output.exists():
        raise FileExistsError("Use a new output directory; preserve completed/partial evidence")
    import traci
    versions = {n: importlib.metadata.version(n) for n in ("eclipse-sumo", "traci", "sumolib")}
    if set(versions.values()) != {"1.24.0"}:
        raise ValueError("Install the pinned optional SUMO requirements in an isolated environment")
    binaries = {n: shutil.which(n, path=str(Path(sys.executable).parent)) for n in ("sumo", "netconvert")}
    if not all(binaries.values()):
        raise ValueError("SUMO binaries not found in this Python environment")
    cfg, frozen = configuration(smoke), plans(smoke)
    if any(not p["schedule"] for p in frozen):
        raise ValueError("Every declared case must have requested arrivals")
    output.mkdir(parents=True)
    start, conn, rows, active_job = time.monotonic(), None, [], None
    def budget():
        if time.monotonic()-start > cfg["cap_seconds"]:
            raise TimeoutError("Frozen baseline collection cap exceeded")
    manifest = dict(configuration=cfg, versions=versions, controllers=list(CONTROLLERS),
                    planned_cases=len(frozen), planned_runs=len(frozen)*len(CONTROLLERS)*cfg["repeats"],
                    source_hashes={name: file_hash(ROOT/name) for name in SOURCE_FILES},
                    demand_families_previously_inspected=True, learned_policy_evaluated=False,
                    controller_observation="previous completed-step clean count packet; no backlog/future metadata")
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (output/"frozen_plans.json").write_text(json.dumps(frozen, indent=2)+"\n")
    frozen_hash = file_hash(output/"frozen_plans.json")
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in SOURCE_FILES:
            archive.write(ROOT/name, name)
    try:
        budget()
        network(output, binaries["netconvert"])
        command = [binaries["sumo"], "-n", str(output/"network.net.xml"), "-r", str(output/"routes.rou.xml"),
                   "--step-length", ".1", "--seed", "110000", "--time-to-teleport", "-1",
                   "--no-step-log", "true", "--duration-log.disable", "true", "--xml-validation", "never"]
        (output/"sumo_command.json").write_text(json.dumps(command, indent=2)+"\n")
        traci.start(command, label="classical_panel", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("classical_panel")
        axes = [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0, 0, 1, 1]:
            raise ValueError("Unexpected protected straight-movement mapping")
        for case_index, plan in enumerate(frozen, start=1):
            for controller in CONTROLLERS:
                hashes = []
                for repeat in range(cfg["repeats"]):
                    budget()
                    active_job = dict(seed=plan["seed"], controller=controller, repeat=repeat)
                    conn.load(command[1:])
                    name = f"trace_{plan['seed']}_{controller}_r{repeat}.jsonl.gz"
                    trace = []
                    with gzip.open(output/name, "xt") as stream:
                        for row in episode(conn, axes, plan, controller, budget):
                            stream.write(json.dumps(row, sort_keys=True, allow_nan=False)+"\n")
                            trace.append(row)
                    metrics = validate_trace(trace, plan["schedule"], controller, axes, plan["steps"])
                    hashes.append(digest(trace))
                    row = dict(**active_job, family=plan["family"], metrics=metrics, trace=name,
                               semantic_trace_sha256=hashes[-1], requested_arrival_sha256=digest(plan["schedule"]))
                    rows.append(row)
                    with (output/"runs.jsonl").open("a") as stream:
                        stream.write(json.dumps(row, allow_nan=False)+"\n")
                if len(set(hashes)) != 1:
                    raise ValueError("Repeated same-policy/source mechanics trace differs")
            print(f"Completed case {case_index}/{len(frozen)} ({plan['family']}, seed {plan['seed']})",
                  file=sys.stderr, flush=True)
        keys = [(r["seed"], r["controller"], r["repeat"]) for r in rows]
        expected = {(p["seed"], c, repeat) for p in frozen for c in CONTROLLERS for repeat in range(cfg["repeats"])}
        if len(keys) != len(set(keys)) or set(keys) != expected or file_hash(output/"frozen_plans.json") != frozen_hash:
            raise ValueError("Incomplete/duplicate cells or changed frozen schedules")
        report = dict(complete=True, comparison_complete=not smoke, smoke=smoke, cases=len(frozen), runs=len(rows),
                      signal_samples=sum(r["metrics"]["signal_samples"] for r in rows),
                      repeat_mechanics_verified=smoke, models_trained=0, policy_promoted=False,
                      **summarize(rows, frozen))
    except (Exception, KeyboardInterrupt) as exc:
        report = dict(complete=False, comparison_complete=False, smoke=smoke, completed_runs=len(rows),
                      active_job=active_job, error=f"{type(exc).__name__}: {exc}", policy_promoted=False)
        raise
    finally:
        try:
            if conn is not None:
                conn.close()
        finally:
            report["elapsed_seconds"] = time.monotonic()-start
            report["output_hashes"] = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    report = run(args.output, args.smoke)
    print(json.dumps({k: report[k] for k in ("complete", "comparison_complete", "smoke", "cases", "runs",
                                           "signal_samples", "elapsed_seconds", "controllers")}, indent=2))


if __name__ == "__main__":
    main()
