"""Reconstruct matched SUMO baseline packets, proposals, physics and metrics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_classical_metrics import summarize, validate_trace
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.audits.verify_sumo_future_panel import read_trace, same_numbers
from research.experiments.sumo_classical_runtime import SOURCE_FILES, configuration, plans
from research.policies.sumo_classical import CONTROLLERS


def verify(directory):
    report = json.loads((directory/"report.json").read_text())
    manifest = json.loads((directory/"manifest.json").read_text())
    if report.get("complete") is not True:
        raise ValueError("Incomplete baseline collection")
    smoke = report["smoke"]
    if type(smoke) is not bool or report["models_trained"] != 0 or report["policy_promoted"] is not False:
        raise ValueError("Changed collection scope")
    cfg, frozen = configuration(smoke), plans(smoke)
    if (manifest["configuration"] != json.loads(json.dumps(cfg)) or manifest["controllers"] != list(CONTROLLERS)
            or manifest["versions"] != dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0")
            or report["comparison_complete"] != (not smoke) or report["repeat_mechanics_verified"] != smoke):
        raise ValueError("Changed declared configuration or relabelled smoke")
    expected_files = {"manifest.json", "frozen_plans.json", "source_snapshot.zip", "sumo_command.json", "runs.jsonl",
                      "nodes.nod.xml", "edges.edg.xml", "connections.con.xml", "network.net.xml", "routes.rou.xml"}
    expected_files |= {f"trace_{p['seed']}_{c}_r{repeat}.jsonl.gz"
                       for p in frozen for c in CONTROLLERS for repeat in range(cfg["repeats"])}
    if set(report["output_hashes"]) != expected_files or set(manifest["source_hashes"]) != set(SOURCE_FILES):
        raise ValueError("Incomplete output/source hash coverage")
    for name, expected in report["output_hashes"].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or file_hash(path) != expected:
            raise ValueError(f"Changed recorded output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if len(archive.namelist()) != len(SOURCE_FILES) or set(archive.namelist()) != set(SOURCE_FILES):
            raise ValueError("Incomplete/duplicate source archive")
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Archived source/protocol hash mismatch")
    if json.loads((directory/"frozen_plans.json").read_text()) != frozen:
        raise ValueError("Changed paired traffic seeds/rates/schedules")
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    expected = {(p["seed"], c, repeat) for p in frozen for c in CONTROLLERS for repeat in range(cfg["repeats"])}
    keys = [(r["seed"], r["controller"], r["repeat"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate controller/source/repeat cells")
    network = ET.parse(directory/"network.net.xml").getroot()
    links = [node for node in network.findall("connection") if node.get("tl") == "c"]
    axes = [int(link.get("from").split("_")[0] in "ew") for link in sorted(links, key=lambda n: int(n.get("linkIndex")))]
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected signal movement mapping")
    lookup, repetitions = {p["seed"]: p for p in frozen}, {}
    for row in rows:
        plan = lookup[row["seed"]]
        name = f"trace_{row['seed']}_{row['controller']}_r{row['repeat']}.jsonl.gz"
        if row["family"] != plan["family"] or row["trace"] != name or row["requested_arrival_sha256"] != digest(plan["schedule"]):
            raise ValueError("Unpaired demand or changed run identity")
        trace = read_trace(directory/name)
        semantic = digest(trace)
        metrics = validate_trace(trace, plan["schedule"], row["controller"], axes, cfg["steps"])
        if semantic != row["semantic_trace_sha256"] or not same_numbers(metrics, row["metrics"]):
            raise ValueError("Trace/controller/metrics do not reconstruct")
        key = (row["seed"], row["controller"])
        if repetitions.setdefault(key, semantic) != semantic:
            raise ValueError("Repeated mechanics trajectory mismatch")
    expected_summary = summarize(rows, frozen)
    if any(not same_numbers(value, report[key]) for key, value in expected_summary.items()):
        raise ValueError("Paired summaries do not reconstruct")
    samples = sum(r["metrics"]["signal_samples"] for r in rows)
    if (report["cases"] != len(frozen) or report["runs"] != len(rows) or report["signal_samples"] != samples
            or manifest["planned_cases"] != len(frozen) or manifest["planned_runs"] != len(rows)):
        raise ValueError("Reported run/signal coverage differs from raw cells")
    return dict(verified=True, smoke=smoke, comparison_complete=not smoke, cases=len(frozen), runs=len(rows),
                signal_samples=samples, requested_arrivals_paired=True, packets_and_proposals_reconstructed=True,
                independently_rerun_trajectories=0, policy_promoted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))


if __name__ == "__main__":
    main()
