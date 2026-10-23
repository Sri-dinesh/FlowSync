"""Frozen jobs and anchored inputs for the executed total-count component test."""
import json
from pathlib import Path

from research.audits.sumo_branch_feasibility import file_hash
from research.audits.verify_sumo_classical_panel import verify as verify_classical
from research.experiments.sumo_classical_runtime import SOURCE_FILES as CLASSICAL_SOURCES

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_REPORT_HASHES = {
    True: "38e2e3e1dbe4d6dc4a741239c6801c05198af11ba03690bc761a3722ed2e9fc6",
    False: "7cd78ca440dd49157d5046aebc9256b4e5f35fc20b07a713064f9d61410fd1bc",
}
SOURCE_FILES = (*CLASSICAL_SOURCES,
    "research/policies/sumo_total_count.py", "research/experiments/sumo_observed_episode.py",
    "research/experiments/sumo_count_ablation.py", "research/analysis/sumo_count_metrics.py",
    "research/analysis/analyze_sumo_classical_panel.py", "research/analysis/sumo_trace_metrics.py",
    "research/pilots/run_sumo_count_ablation.py", "research/audits/verify_sumo_count_ablation.py",
    "research/docs/protocols/SUMO_COUNT_ABLATION_20261023.md")


def configuration(smoke=False):
    if type(smoke) is not bool:
        raise ValueError("Smoke mode must be boolean")
    return dict(smoke=smoke, cap_seconds=120 if smoke else 360, steps=800 if smoke else 1800,
                new_runs=3 if smoke else 15, paired_cases=1 if smoke else 15,
                reference_report_sha256=REFERENCE_REPORT_HASHES[smoke], reused_development_cases=True)


def jobs(plans, smoke):
    if smoke:
        if len(plans) != 1:
            raise ValueError("Smoke requires exactly one mechanics case")
        return [dict(seed=plans[0]["seed"], controller=c, repeat=r)
                for c, r in (("max_pressure", 0), ("total_incoming", 0), ("total_incoming", 1))]
    return [dict(seed=p["seed"], controller="total_incoming", repeat=0) for p in plans]


def trace_name(job):
    return f"trace_{job['seed']}_{job['controller']}_r{job['repeat']}.jsonl.gz"


def load_reference(directory, smoke):
    if file_hash(directory/"report.json") != REFERENCE_REPORT_HASHES[smoke]:
        raise ValueError("Reference report is not the precommitted classical artifact")
    verified = verify_classical(directory)
    if verified["smoke"] is not smoke:
        raise ValueError("Reference smoke/full role mismatch")
    manifest = json.loads((directory/"manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError(f"Frozen classical dependency changed: {name}")
    report = json.loads((directory/"report.json").read_text())
    plans = json.loads((directory/"frozen_plans.json").read_text())
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    return dict(verification=verified, manifest=manifest, report=report, plans=plans, rows=rows,
                hashes={name: file_hash(directory/name) for name in ("report.json", *report["output_hashes"])},
                command=json.loads((directory/"sumo_command.json").read_text()))


def ensure_reference_unchanged(directory, reference):
    if any(file_hash(directory/name) != sha for name, sha in reference["hashes"].items()):
        raise ValueError("Reference evidence changed during the ablation")


def command_for(reference, directory, binary):
    command = list(reference["command"])
    if command[1:2] != ["-n"] or command[3:4] != ["-r"]:
        raise ValueError("Unexpected reference command layout")
    command[0], command[2], command[4] = str(binary), str(directory/"network.net.xml"), str(directory/"routes.rou.xml")
    return command
