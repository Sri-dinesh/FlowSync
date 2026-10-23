"""Verify the new total-count traces and their immutable reused references."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_count_metrics import summarize
from research.audits.sumo_branch_feasibility import digest, file_hash
from research.audits.verify_sumo_future_panel import read_trace, same_numbers
from research.experiments.sumo_count_ablation import SOURCE_FILES, command_for, configuration, jobs, load_reference, trace_name
from research.experiments.sumo_observed_episode import validate_trace
from research.policies.sumo_total_count import policy_for


def verify(directory, reference_directory):
    report = json.loads((directory/"report.json").read_text())
    if report.get("complete") is not True:
        raise ValueError("Incomplete total-count ablation")
    smoke = report["smoke"]
    cfg = configuration(smoke)
    reference = load_reference(reference_directory, smoke)
    frozen, tasks = reference["plans"], jobs(reference["plans"], smoke)
    manifest = json.loads((directory/"manifest.json").read_text())
    if (manifest["configuration"] != cfg or manifest["planned_jobs"] != tasks
            or manifest["versions"] != reference["manifest"]["versions"]
            or manifest["reference_input_sha256"] != reference["hashes"]
            or manifest["reference_manifest_sha256"] != reference["hashes"]["manifest.json"]
            or manifest["learned_policy_evaluated"] is not False or manifest["reused_development_cases"] is not True):
        raise ValueError("Changed declared configuration, references or scope")
    if (report["comparison_complete"] != (not smoke) or report["anchor_replay_verified"] != smoke
            or report["total_repeat_verified"] != smoke or report["models_trained"] != 0
            or report["policy_promoted"] is not False or report["reused_development_cases"] is not True):
        raise ValueError("Relabelled smoke or changed experiment scope")
    expected_files = {"manifest.json", "frozen_plans.json", "source_snapshot.zip", "network.net.xml", "routes.rou.xml",
                      "sumo_command.json", "runs.jsonl"} | {trace_name(t) for t in tasks}
    if set(report["output_hashes"]) != expected_files or set(manifest["source_hashes"]) != set(SOURCE_FILES):
        raise ValueError("Missing output/source hash coverage")
    for name, expected in report["output_hashes"].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or file_hash(path) != expected:
            raise ValueError(f"Changed output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if len(archive.namelist()) != len(SOURCE_FILES) or set(archive.namelist()) != set(SOURCE_FILES):
            raise ValueError("Incomplete/duplicate source archive")
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Archived source/protocol mismatch")
    for name in ("network.net.xml", "routes.rou.xml", "frozen_plans.json"):
        if file_hash(directory/name) != reference["hashes"][name]:
            raise ValueError("Changed matched network, routes or paired schedules")
    command = json.loads((directory/"sumo_command.json").read_text())
    normalized = command.copy()
    normalized[2], normalized[4] = str(Path(command[2]).resolve()), str(Path(command[4]).resolve())
    if normalized != command_for(reference, directory.resolve(), command[0]):
        raise ValueError("Changed SUMO command parameters or network selection")
    net = ET.parse(directory/"network.net.xml").getroot()
    links = [n for n in net.findall("connection") if n.get("tl") == "c"]
    axes = [int(n.get("from").split("_")[0] in "ew") for n in sorted(links, key=lambda n: int(n.get("linkIndex")))]
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected protected movement mapping")
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    if [(r["seed"], r["controller"], r["repeat"]) for r in rows] != [
            (t["seed"], t["controller"], t["repeat"]) for t in tasks]:
        raise ValueError("Incomplete/duplicate or substituted jobs")
    plans, repeats = {p["seed"]: p for p in frozen}, {}
    for row in rows:
        plan, name = plans[row["seed"]], trace_name(row)
        if row["trace"] != name or row["family"] != plan["family"] or row["requested_arrival_sha256"] != digest(plan["schedule"]):
            raise ValueError("Changed case identity or paired requested arrivals")
        trace = read_trace(directory/name)
        metrics = validate_trace(trace, plan["schedule"], policy_for(row["controller"]), axes, cfg["steps"])
        semantic = digest(trace)
        if row["semantic_trace_sha256"] != semantic or not same_numbers(metrics, row["metrics"]):
            raise ValueError("Raw packet/proposal/metric reconstruction failed")
        key = (row["seed"], row["controller"])
        if repeats.setdefault(key, semantic) != semantic:
            raise ValueError("Total-count repeats differ")
        if row["controller"] == "max_pressure":
            anchor = next(r for r in reference["rows"] if r["seed"] == row["seed"]
                          and r["controller"] == "max_pressure" and r["repeat"] == 0)
            if semantic != anchor["semantic_trace_sha256"]:
                raise ValueError("Max-Pressure anchor replay mismatch")
    summaries = summarize(rows, reference["rows"], frozen, smoke)
    if any(not same_numbers(value, report[key]) for key, value in summaries.items()):
        raise ValueError("All-case paired comparisons do not reconstruct")
    samples = sum(r["metrics"]["signal_samples"] for r in rows)
    if (report["cases"] != len(frozen) or report["new_runs"] != len(rows) or report["new_signal_samples"] != samples
            or report["reference_runs"] != reference["verification"]["runs"]
            or report["reference_signal_samples"] != reference["verification"]["signal_samples"]):
        raise ValueError("Changed new/reference sample coverage")
    return dict(verified=True, smoke=smoke, comparison_complete=not smoke, cases=len(frozen), new_runs=len(rows),
        new_signal_samples=samples, reference_runs=reference["verification"]["runs"],
        reference_signal_samples=reference["verification"]["signal_samples"],
        anchor_replay_verified=smoke, total_repeat_verified=smoke, independently_rerun_trajectories=0,
        reused_development_cases=True, policy_promoted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.reference), indent=2))


if __name__ == "__main__":
    main()
