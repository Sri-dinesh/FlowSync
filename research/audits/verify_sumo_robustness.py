"""Reconstruct the complete phase/horizon robustness evidence without SUMO."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_robustness_metrics import check_mechanics, measurements, summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.audits.verify_sumo_future_panel import read_trace, same_numbers
from research.experiments.sumo_robustness import PINNED_SOURCES, SOURCE_FILES, configuration, jobs, plans, trace_name, trim_plan


def verify(directory):
    report = json.loads((directory/"report.json").read_text())
    if report.get("complete") is not True:
        raise ValueError("Incomplete robustness collection")
    cfg = configuration(report["smoke"])
    smoke, frozen, tasks = cfg["smoke"], plans(cfg["smoke"]), jobs(cfg["smoke"])
    manifest = json.loads((directory/"manifest.json").read_text())
    if (manifest["configuration"] != cfg or manifest["planned_jobs"] != tasks
            or manifest["versions"] != dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0")
            or manifest["learned_policy_evaluated"] is not False or manifest["known_demand_families"] is not True):
        raise ValueError("Changed frozen design or collection scope")
    expected_files = {"manifest.json", "frozen_plans.json", "source_snapshot.zip", "runs.jsonl", "sumo_command.json",
        "nodes.nod.xml", "edges.edg.xml", "connections.con.xml", "network.net.xml", "routes.rou.xml"} | {trace_name(t) for t in tasks}
    if set(report["output_hashes"]) != expected_files or set(manifest["source_hashes"]) != set(SOURCE_FILES):
        raise ValueError("Missing source/output hash coverage")
    for name, expected in report["output_hashes"].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or file_hash(path) != expected:
            raise ValueError(f"Changed recorded output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if len(archive.namelist()) != len(SOURCE_FILES) or set(archive.namelist()) != set(SOURCE_FILES):
            raise ValueError("Incomplete/duplicate source archive")
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Archived source/protocol mismatch")
        if any(manifest["source_hashes"].get(name) != sha for name, sha in PINNED_SOURCES.items()):
            raise ValueError("Frozen controller/physical source changed")
    if json.loads((directory/"frozen_plans.json").read_text()) != frozen:
        raise ValueError("Changed frozen seeds/rates/schedules")
    command = json.loads((directory/"sumo_command.json").read_text())
    expected_command = [command[0], "-n", str((directory/"network.net.xml").resolve()), "-r", str((directory/"routes.rou.xml").resolve()),
        "--step-length", ".1", "--seed", "110000", "--time-to-teleport", "-1", "--no-step-log", "true",
        "--duration-log.disable", "true", "--xml-validation", "never"]
    normalized = command.copy()
    normalized[2], normalized[4] = str(Path(command[2]).resolve()), str(Path(command[4]).resolve())
    if normalized != expected_command:
        raise ValueError("Changed execution command")
    net = ET.parse(directory/"network.net.xml").getroot()
    links = [n for n in net.findall("connection") if n.get("tl") == "c"]
    axes = [int(n.get("from").split("_")[0] in "ew") for n in sorted(links, key=lambda n: int(n.get("linkIndex")))]
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected protected movement mapping")
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    identity = lambda r: tuple(r[k] for k in ("seed", "initial_phase", "controller", "repeat", "kind", "steps"))
    if [identity(r) for r in rows] != [identity(t) for t in tasks]:
        raise ValueError("Incomplete/duplicate or substituted jobs")
    lookup = {p["seed"]: p for p in frozen}
    for row in rows:
        plan = trim_plan(lookup[row["seed"]], row["steps"])
        if row["trace"] != trace_name(row) or row["family"] != plan["family"] or row["requested_arrival_sha256"] != digest(plan["schedule"]):
            raise ValueError("Unpaired arrivals or changed run identity")
        trace = read_trace(directory/row["trace"])
        if digest(trace) != row["semantic_trace_sha256"] or digest(trace[:cfg["endpoint_ticks"][0]]) != row["prefix_semantic_trace_sha256"]:
            raise ValueError("Changed raw trajectory/prefix")
        rebuilt = measurements(trace, plan, row, axes, cfg)
        if not same_numbers(rebuilt, row["measurements"]):
            raise ValueError("Canonical phase/packet/endpoint/axis metrics do not reconstruct")
    if not same_numbers(check_mechanics(rows, smoke), report["mechanics"]):
        raise ValueError("Mechanics repeats/prefixes do not reconstruct")
    summary = summarize(rows, frozen, cfg)
    if any(not same_numbers(value, report[key]) for key, value in summary.items()):
        raise ValueError("Hierarchical comparisons do not reconstruct")
    if (report["robustness_complete"] != (not smoke) or report["traffic_seeds"] != len(frozen)
            or report["paired_start_contexts"] != len(frozen)*2 or report["runs"] != len(tasks)
            or report["executed_signal_samples"] != sum(t["steps"] for t in tasks)
            or report["executed_signal_samples"] != cfg["planned_signal_samples"]
            or report["measurement_endpoints_seconds"] != [t//10 for t in cfg["endpoint_ticks"]]
            or report["primary_endpoint_seconds"] != cfg["steps"]//10 or report["prefix_measurements_overlap"] is not True
            or report["models_trained"] != 0 or report["policy_promoted"] is not False or report["publication_ready"] is not False
            or report["component_series_closed_on_completion"] != (not smoke)):
        raise ValueError("Relabelled smoke, endpoint coverage, replication count or completion scope")
    return dict(verified=True, smoke=smoke, robustness_complete=not smoke, traffic_seeds=len(frozen),
        paired_start_contexts=len(frozen)*2, runs=len(tasks), executed_signal_samples=report["executed_signal_samples"],
        primary_endpoint_seconds=cfg["steps"]//10, prefix_measurements_overlap=True,
        independently_rerun_trajectories=0, policy_promoted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))


if __name__ == "__main__":
    main()
