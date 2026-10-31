"""Preserve a timed-out sensing prefix and collect only its missing whole episodes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

from research.experiments.sumo_sensing import PLAN, configuration, episode, plans, validate_trace
from research.observation.sumo_sensing import PRESETS
from research.pilots.run_sumo_sensing_panel import (
    ROOT, SOURCES, SUMO_OPTIONS, case_table, digest, file_hash, physical_view,
    read_trace, runtime, save_trace, summarize, trace_name, verify as verify_collection,
    write, write_csv,
)
from research.policies.sumo_classical import CONTROLLERS

SOURCE = "research/pilots/recover_sumo_sensing.py"
RECOVERY_CAP_SECONDS = 600
BASE_FILES = {"manifest.json", "frozen_plans.json", "source_snapshot.zip", "sumo_command.json",
              "nodes.nod.xml", "edges.edg.xml", "connections.con.xml", "network.net.xml", "routes.rou.xml"}


def jobs():
    return [dict(seed=p["seed"], controller=c, fault=f.name, repeat=0)
            for p in plans() for c in CONTROLLERS for f in PRESETS]


def axes_for(directory):
    links = [link for link in ET.parse(directory / "network.net.xml").getroot().findall("connection")
             if link.get("tl") == "c"]
    axes = [int(link.get("from").split("_")[0] in "ew")
            for link in sorted(links, key=lambda link: int(link.get("linkIndex")))]
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected protected-movement mapping")
    return axes


def inventory(directory, report_name="report.json"):
    return {p.relative_to(directory).as_posix(): file_hash(p)
            for p in sorted(directory.rglob("*")) if p.is_file() and p != directory / report_name}


def audit_prefix(directory):
    """Validate a closed timeout prefix without treating it as a complete panel."""
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    if (report.get("complete") is not False or report.get("scientific_panel_complete") is not False
            or report.get("smoke") is not False or report.get("policy_promoted") is not False
            or report.get("publication_ready") is not False
            or report.get("error") != "TimeoutError: Frozen sensing collection cap exceeded"
            or type(report.get("elapsed_seconds")) not in (int, float)
            or not math.isfinite(report["elapsed_seconds"]) or report["elapsed_seconds"] < 900):
        raise ValueError("Recovery requires the preserved closed timeout, not a completed/relabelled panel")
    if inventory(directory) != report["output_hashes"]:
        raise ValueError("Interrupted evidence inventory/hash mismatch")
    if (manifest["plan"] != PLAN or manifest["configuration"] != json.loads(json.dumps(configuration()))
            or set(manifest["source_hashes"]) != set(SOURCES)
            or any(file_hash(ROOT / n) != h for n, h in manifest["source_hashes"].items())):
        raise ValueError("Interrupted study source/configuration changed")
    with zipfile.ZipFile(directory / "source_snapshot.zip") as archive:
        if (len(archive.namelist()) != len(SOURCES) or set(archive.namelist()) != set(SOURCES)
                or any(hashlib.sha256(archive.read(n)).hexdigest() != h
                       for n, h in manifest["source_hashes"].items())):
            raise ValueError("Interrupted source archive mismatch")
    proof = manifest["mechanics"]
    mechanics = Path(proof["directory"])
    if file_hash(mechanics / "report.json") != proof["report_sha256"]:
        raise ValueError("Changed original mechanics basis")
    checked = verify_collection(mechanics)
    old = json.loads((mechanics / "manifest.json").read_text())
    if not checked["smoke"] or old["source_hashes"] != manifest["source_hashes"] or old["runtime"] != manifest["runtime"]:
        raise ValueError("Interrupted study differs from verified mechanics")
    frozen = plans()
    if json.loads((directory / "frozen_plans.json").read_text()) != frozen:
        raise ValueError("Changed interrupted schedules")
    command = json.loads((directory / "sumo_command.json").read_text())
    if (len(command) != 5 + len(SUMO_OPTIONS) or command[1] != "-n" or command[3] != "-r"
            or Path(command[2]).name != "network.net.xml" or Path(command[4]).name != "routes.rou.xml"
            or command[5:] != list(SUMO_OPTIONS)):
        raise ValueError("Changed interrupted SUMO command")
    rows = [json.loads(line) for line in (directory / "runs.jsonl").read_text().splitlines()]
    planned = jobs()
    if not 0 < len(rows) < len(planned) or report["completed_runs"] != len(rows):
        raise ValueError("Expected a nonempty proper prefix of complete episodes")
    if [{k: r[k] for k in planned[0]} for r in rows] != planned[:len(rows)]:
        raise ValueError("Interrupted rows are not the exact frozen prefix")
    if report["active_job"] != planned[len(rows)]:
        raise ValueError("Interrupted active job does not follow the completed prefix")
    names = {trace_name(**job) for job in planned[:len(rows)]}
    partial = trace_name(**planned[len(rows)])
    expected = BASE_FILES | {"runs.jsonl"} | names
    if set(report["output_hashes"]) not in (expected, expected | {partial}):
        raise ValueError("Unexpected interrupted output coverage")
    lookup = {p["seed"]: p for p in frozen}
    axes = axes_for(directory)
    fixed = {}
    for row in rows:
        name = trace_name(row["seed"], row["controller"], row["fault"], row["repeat"])
        plan = lookup[row["seed"]]
        trace = read_trace(directory / name)
        fault = next(f for f in PRESETS if f.name == row["fault"])
        if (row["family"] != plan["family"] or row["trace"] != name
                or row["requested_arrival_sha256"] != digest(plan["schedule"])
                or row["semantic_trace_sha256"] != digest(trace)
                or row["metrics"] != validate_trace(trace, plan, row["controller"], fault, axes)):
            raise ValueError("Completed prefix trajectory/metrics do not reconstruct")
        if row["controller"] == "fixed":
            physical = digest(physical_view(trace))
            if fixed.setdefault(row["seed"], physical) != physical:
                raise ValueError("Interrupted Fixed invariance failed")
    return dict(verified=True, complete=False, scientific_panel_complete=False,
                completed_runs=len(rows), remaining_runs=len(planned) - len(rows),
                partial_trace_excluded=partial if partial in report["output_hashes"] else None,
                independently_rerun_trajectories=0)


def recover(prefix, output):
    prefix, output = Path(prefix), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Choose a new recovery directory; preserve all previous attempts")
    if output.resolve().is_relative_to(prefix.resolve()):
        raise ValueError("Recovery output must be outside the preserved prefix")
    if subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCES, SOURCE], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the recovery adapter before collection")
    checked = audit_prefix(prefix)
    binaries, environment = runtime()
    original = json.loads((prefix / "manifest.json").read_text())
    if environment != original["runtime"]:
        raise ValueError("Recovery runtime must exactly match the interrupted study")
    parent_report = json.loads((prefix / "report.json").read_text())
    initial_rows = [json.loads(line) for line in (prefix / "runs.jsonl").read_text().splitlines()]
    output.mkdir(parents=True)
    collection = output / "collection"
    collection.mkdir()
    for name in BASE_FILES | {"runs.jsonl"} | {r["trace"] for r in initial_rows}:
        shutil.copyfile(prefix / name, collection / name)
    # The original executable archive/configuration stays intact. This adapter has its own provenance.
    manifest = dict(version="sumo_sensing_recovery_v1", prefix_directory=str(prefix.resolve()),
                    prefix_sha256={"report.json": file_hash(prefix / "report.json"), **parent_report["output_hashes"]},
                    prefix_verification=checked, original_cap_seconds=configuration()["cap_seconds"],
                    original_cap_met=False, recovery_cap_seconds=RECOVERY_CAP_SECONDS,
                    source_sha256={SOURCE: file_hash(ROOT / SOURCE)}, runtime=environment,
                    git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    planned_reused_runs=len(initial_rows), planned_new_runs=checked["remaining_runs"],
                    planned_parity_anchor_runs=1, traffic_and_analysis_changed=False,
                    execution_budget_amended=True, model_selection=False)
    write(output / "manifest.json", manifest)
    with zipfile.ZipFile(output / "recovery_source_snapshot.zip", "x") as archive:
        archive.write(ROOT / SOURCE, SOURCE)
    start, conn, active_job = time.monotonic(), None, None
    rows = initial_rows.copy()
    fixed = {}
    for row in initial_rows:
        if row["controller"] == "fixed":
            fixed[row["seed"]] = digest(physical_view(read_trace(prefix / row["trace"])))
    outcome = dict(complete=False, scientific_panel_complete=False, policy_promoted=False,
                   publication_ready=False, new_runs=0, parity_anchor_verified=False,
                   original_attempt_budget_met=False, execution_budget_amended=True,
                   partial_prefix_verified=None, episode_timings=[])
    canonical = dict(complete=False, scientific_panel_complete=False, smoke=False,
                     policy_promoted=False, publication_ready=False, recovered=True)
    def budget():
        if time.monotonic() - start > manifest["recovery_cap_seconds"]:
            raise TimeoutError("Recovery collection cap exceeded")
    try:
        import traci
        command = [binaries["sumo"], "-n", str((collection / "network.net.xml").resolve()),
                   "-r", str((collection / "routes.rou.xml").resolve()), *SUMO_OPTIONS]
        write(collection / "sumo_command.json", command)
        traci.start(command, label="sensing_recovery", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("sensing_recovery")
        axes = axes_for(collection)
        live_axes = [int(link[0][0].split("_")[0] in "ew")
                     for link in conn.trafficlight.getControlledLinks("c")]
        if axes != live_axes:
            raise ValueError("Recovery live signal mapping differs")
        lookup = {p["seed"]: p for p in plans()}
        first = initial_rows[0]
        conn.load(command[1:])
        anchor = save_trace(output / "parity_anchor.jsonl.gz", episode(conn, axes, lookup[first["seed"]],
                            first["controller"], next(f for f in PRESETS if f.name == first["fault"]), budget))
        if digest(anchor) != first["semantic_trace_sha256"]:
            raise ValueError("Recovery whole-episode parity anchor differs")
        outcome["parity_anchor_verified"] = True
        for job in jobs()[len(initial_rows):]:
            budget()
            active_job = job
            conn.load(command[1:])
            plan = lookup[job["seed"]]
            fault = next(f for f in PRESETS if f.name == job["fault"])
            name = trace_name(**job)
            episode_start = time.monotonic()
            trace = save_trace(collection / name, episode(conn, axes, plan, job["controller"], fault, budget))
            collected_at = time.monotonic()
            if job == jobs()[len(initial_rows)] and checked["partial_trace_excluded"] is not None:
                partial = read_trace(prefix / checked["partial_trace_excluded"])
                if trace[:len(partial)] != partial:
                    raise ValueError("Previously interrupted trajectory prefix differs")
                outcome["partial_prefix_verified"] = True
            metrics = validate_trace(trace, plan, job["controller"], fault, axes)
            if job["controller"] == "fixed":
                physical = digest(physical_view(trace))
                if fixed.setdefault(job["seed"], physical) != physical:
                    raise ValueError("Recovered Fixed traffic depends on sensing faults")
            row = dict(**job, family=plan["family"], metrics=metrics, trace=name,
                       semantic_trace_sha256=digest(trace), requested_arrival_sha256=digest(plan["schedule"]))
            rows.append(row)
            with (collection / "runs.jsonl").open("a") as stream:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
            outcome["new_runs"] += 1
            outcome["episode_timings"].append(dict(**job, collection_seconds=collected_at - episode_start,
                                                   validation_seconds=time.monotonic() - collected_at))
            print(f"Recovered episode {len(rows)}/{len(jobs())} ({job['seed']}, {job['controller']}, {job['fault']})", flush=True)
        summary = summarize(rows, plans(), 1)
        write_csv(collection / "cases.csv", case_table(rows))
        write_csv(collection / "aggregate.csv", summary["aggregate"])
        write_csv(collection / "paired_contrasts.csv", summary["paired_contrasts"])
        budget()
        canonical.update(complete=True, scientific_panel_complete=True, cases=len(plans()), runs=len(rows),
                         signal_samples=sum(r["metrics"]["signal_samples"] for r in rows),
                         mechanics_anchor_runs=0, mechanics_anchor_signal_samples=0,
                         fixed_invariance_verified=True, repeat_mechanics_verified=False,
                         clean_anchor_verified=False, summary=summary)
        outcome.update(complete=True, scientific_panel_complete=True, reused_runs=len(initial_rows),
                       panel_runs=len(rows), signal_samples=canonical["signal_samples"])
    except (Exception, KeyboardInterrupt) as exc:
        outcome.update(error=f"{type(exc).__name__}: {exc}", active_job=active_job)
        canonical.update(error=outcome["error"], completed_runs=len(rows), active_job=active_job)
        raise
    finally:
        try:
            if conn is not None:
                conn.close()
        finally:
            outcome["recovery_elapsed_seconds"] = time.monotonic() - start
            canonical["elapsed_seconds"] = parent_report["elapsed_seconds"] + outcome["recovery_elapsed_seconds"]
            canonical["execution_scope"] = "Recovered panel; original 900-second attempt timed out. See parent recovery manifest."
            canonical["output_hashes"] = inventory(collection)
            write(collection / "report.json", canonical)
            outcome["output_hashes"] = inventory(output)
            write(output / "report.json", outcome)
    return {k: v for k, v in outcome.items() if k != "output_hashes"}


def verify(directory):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest["version"] != "sumo_sensing_recovery_v1" or manifest["traffic_and_analysis_changed"] is not False
            or manifest["execution_budget_amended"] is not True or manifest["original_cap_met"] is not False
            or manifest["recovery_cap_seconds"] != RECOVERY_CAP_SECONDS or manifest["original_cap_seconds"] != 900
            or manifest["model_selection"] is not False or manifest["planned_parity_anchor_runs"] != 1):
        raise ValueError("Changed recovery protocol or budget disclosure")
    if (report.get("complete") is not True or report.get("scientific_panel_complete") is not True
            or report.get("publication_ready") is not False or report.get("policy_promoted") is not False
            or report.get("parity_anchor_verified") is not True or report.get("original_attempt_budget_met") is not False
            or report.get("execution_budget_amended") is not True):
        raise ValueError("Recovery is incomplete or relabelled")
    if inventory(directory) != report["output_hashes"]:
        raise ValueError("Recovery output/hash coverage mismatch")
    if {p.name for p in directory.iterdir()} != {"manifest.json", "report.json", "collection",
            "parity_anchor.jsonl.gz", "recovery_source_snapshot.zip"}:
        raise ValueError("Unexpected recovery output coverage")
    if (set(manifest["source_sha256"]) != {SOURCE}
            or manifest["source_sha256"][SOURCE] != file_hash(ROOT / SOURCE)):
        raise ValueError("Recovery replay requires its archived adapter source")
    with zipfile.ZipFile(directory / "recovery_source_snapshot.zip") as archive:
        if archive.namelist() != [SOURCE] or hashlib.sha256(archive.read(SOURCE)).hexdigest() != manifest["source_sha256"][SOURCE]:
            raise ValueError("Recovery source archive mismatch")
    prefix = Path(manifest["prefix_directory"])
    checked = audit_prefix(prefix)
    parent = json.loads((prefix / "report.json").read_text())
    if (manifest["prefix_verification"] != checked
            or manifest["prefix_sha256"] != {"report.json": file_hash(prefix / "report.json"), **parent["output_hashes"]}):
        raise ValueError("Recovery input coverage mismatch")
    if any(file_hash(prefix / n) != h for n, h in manifest["prefix_sha256"].items()):
        raise ValueError("Preserved timeout prefix changed")
    initial = [json.loads(line) for line in (prefix / "runs.jsonl").read_text().splitlines()]
    collection = directory / "collection"
    current = [json.loads(line) for line in (collection / "runs.jsonl").read_text().splitlines()]
    canonical = json.loads((collection / "report.json").read_text())
    original_manifest = json.loads((prefix / "manifest.json").read_text())
    if (json.loads((collection / "manifest.json").read_text()) != original_manifest
            or manifest["runtime"] != original_manifest["runtime"] or current[:len(initial)] != initial
            or report["reused_runs"] != len(initial) or report["new_runs"] != len(jobs()) - len(initial)
            or manifest["planned_reused_runs"] != len(initial) or manifest["planned_new_runs"] != report["new_runs"]
            or report["panel_runs"] != len(jobs()) or report["signal_samples"] != len(jobs()) * configuration()["steps"]
            or not 0 <= report["recovery_elapsed_seconds"] <= RECOVERY_CAP_SECONDS
            or canonical["elapsed_seconds"] != parent["elapsed_seconds"] + report["recovery_elapsed_seconds"]
            or canonical.get("recovered") is not True):
        raise ValueError("Recovery counts, runtime or elapsed accounting mismatch")
    for row in initial:
        if file_hash(prefix / row["trace"]) != file_hash(collection / row["trace"]):
            raise ValueError("Reused prefix trace bytes changed")
    anchor = read_trace(directory / "parity_anchor.jsonl.gz")
    if digest(anchor) != initial[0]["semantic_trace_sha256"]:
        raise ValueError("Recovery parity anchor mismatch")
    if checked["partial_trace_excluded"] is not None:
        partial = read_trace(prefix / checked["partial_trace_excluded"])
        continued = read_trace(collection / current[len(initial)]["trace"])
        if report.get("partial_prefix_verified") is not True or continued[:len(partial)] != partial:
            raise ValueError("Interrupted trajectory prefix does not reproduce")
    elif report.get("partial_prefix_verified") is not None:
        raise ValueError("Missing partial prefix cannot establish a parity claim")
    checked_collection = verify_collection(collection)
    return dict(verified=True, scientific_panel_complete=True, reused_runs=len(initial),
                newly_collected_runs=report["new_runs"], parity_anchor_runs=1,
                panel_runs=checked_collection["runs"], signal_samples=checked_collection["signal_samples"],
                original_attempt_budget_met=False, execution_budget_amended=True,
                independently_rerun_trajectories=0, publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prefix", type=Path)
    mode.add_argument("--audit-prefix", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.prefix and args.output is None:
        parser.error("--prefix requires --output")
    if not args.prefix and args.output is not None:
        parser.error("--output is only valid with --prefix")
    result = recover(args.prefix, args.output) if args.prefix else (
        audit_prefix(args.audit_prefix) if args.audit_prefix else verify(args.verify))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
