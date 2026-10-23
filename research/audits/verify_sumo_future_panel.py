"""Verify saved independent-SUMO traces and summaries without running SUMO."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

from research.audits.sumo_branch_feasibility import audit_signals, digest, file_hash
from research.pilots.run_sumo_future_panel import FAMILIES, arrivals, choose, future_seed, outcome, summarize


def read_trace(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def same_numbers(left, right):
    """Strict structure/counts; tolerate only floating accumulation roundoff."""
    if isinstance(left, float) and type(right) in (float, int):
        return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=0, abs_tol=1e-9)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same_numbers(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_numbers(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def verify(directory):
    report = json.loads((directory/"report.json").read_text())
    manifest = json.loads((directory/"manifest.json").read_text())
    if report.get("complete") is not True:
        raise ValueError("Incomplete SUMO panel")
    if report["smoke"] != manifest["smoke"] or report["scientific_panel_complete"] != (not manifest["smoke"]):
        raise ValueError("Smoke cannot be relabelled scientific completion")
    if manifest["horizon_ticks"] != (200 if manifest["smoke"] else 400):
        raise ValueError("Changed frozen branch horizon")
    for name, expected in report["output_hashes"].items():
        target = (directory/name).resolve()
        if not target.is_relative_to(directory.resolve()) or file_hash(target) != expected:
            raise ValueError(f"Changed SUMO output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Changed archived SUMO source")
    cases = json.loads((directory/"frozen_cases.json").read_text())
    choices = json.loads((directory/"frozen_choices.json").read_text())
    rows = [json.loads(line) for line in (directory/"outcomes.jsonl").read_text().splitlines()]
    families = (("balanced", .2, .2, (109901,)),) if manifest["smoke"] else FAMILIES
    configurations = {seed: (family, ns, ew) for family, ns, ew, seeds in families for seed in seeds}
    if {c["source"] for c in cases} != set(configurations) or len(cases) != len(configurations):
        raise ValueError("Wrong frozen source configurations")
    keys = [(r["source"], r["role"], r["index"]) for r in rows]
    expected_keys = {(case["source"], f["role"], f["index"]) for case in cases for f in case["futures"]}
    if len(cases) != manifest["planned_sources"] or len(keys) != len(set(keys)) or set(keys) != expected_keys:
        raise ValueError("Incomplete/duplicate planned SUMO cells")
    lookup = dict(zip(keys, rows))
    branch_samples, prefix_samples = 0, 0
    axes = _axes(directory)
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected protected-movement mapping")
    for case in cases:
        family, ns, ew = configurations[case["source"]]
        if case["family"] != family or case["source_arrivals"] != arrivals(case["source"], 0, 1200, ns, ew):
            raise ValueError("Changed source demand")
        roles = {("single", -1)} | {("fit", i) for i in range(2 if manifest["smoke"] else 8)}
        roles |= {("check", i) for i in range(8, 10 if manifest["smoke"] else 16)}
        if {(f["role"], f["index"]) for f in case["futures"]} != roles or len(case["futures"]) != len(roles):
            raise ValueError("Changed frozen future partition")
        prefix = read_trace(directory/f"source_{case['source']}.jsonl.gz")
        if digest(prefix) != case["source_trace_sha256"] or [r["tick"] for r in prefix] != list(range(case["gate"])):
            raise ValueError("Changed source history")
        prefix_samples += len(prefix)
        for future in case["futures"]:
            seed = future_seed(case["source"], future["role"], future["index"], manifest["smoke"])
            if future["seed"] != seed or future["arrivals"] != arrivals(seed, case["gate"], case["gate"]+manifest["horizon_ticks"], ns, ew):
                raise ValueError("Changed future RNG keys or schedules")
            row = lookup[case["source"], future["role"], future["index"]]
            if row["requested_arrivals_sha256"] != digest(future["arrivals"]):
                raise ValueError("Changed frozen arrivals")
            for action in (0, 1):
                name = f"branch_{case['source']}_{future['role']}_{future['index']}_{action}.jsonl.gz"
                trace = read_trace(directory/name)
                if [r["tick"] for r in trace] != list(range(case["gate"], case["gate"]+manifest["horizon_ticks"])):
                    raise ValueError("Incomplete branch trace")
                if [a for r in trace for a in r["requested"]] != future["arrivals"]:
                    raise ValueError("Action branches do not receive paired requested arrivals")
                audit_signals(prefix+trace, axes)
                for sample in trace:
                    waited = round(.1*(sum(v[3] < .1 for v in sample["vehicles"])+len(sample["pending"])), 6)
                    if sample["wait_vehicle_seconds"] != waited:
                        raise ValueError("Stopped-wait integral does not match raw vehicles/backlog")
                current = outcome(prefix, trace)
                if any(not same_numbers(value, row[str(action)][k]) for k, value in current.items()):
                    raise ValueError("SUMO outcome does not recompute from raw trace")
                if row[str(action)]["first_execution"] != action:
                    raise ValueError("Requested initial action was not executed")
                permissions = {axes[i] for i, lamp in enumerate(trace[0]["lamps"]) if lamp in "GgyY"}
                if len(permissions) != 1:
                    raise ValueError("Invalid first signal execution")
                actual = next(iter(permissions)) ^ int("y" in trace[0]["lamps"])
                if actual != action:
                    raise ValueError("Raw lamps do not execute the frozen first action")
                branch_samples += len(trace)
        selection = [r for r in rows if r["source"] == case["source"]]
        fixed = dict(baseline=case["baseline"],
                     single=choose([r for r in selection if r["role"] == "single"], case["baseline"]),
                     mean8=choose([r for r in selection if r["role"] == "fit"], case["baseline"]))
        if choices[str(case["source"])] != fixed:
            raise ValueError("Frozen choices do not reconstruct from selection futures")
    expected = summarize(cases, rows, choices, manifest["smoke"])
    if any(not same_numbers(value, report[k]) for k, value in expected.items()):
        raise ValueError("SUMO report does not recompute")
    return dict(verified=True, smoke=manifest["smoke"], scientific_panel_complete=not manifest["smoke"],
                branches=2*len(rows), unique_source_ticks=prefix_samples, branch_ticks=branch_samples,
                independently_rerun_trajectories=0, publication_ready=False,
                scope="Hashes, raw signal/arrival coverage, outcomes and frozen-choice/summary reconstruction")


def _axes(directory):
    import xml.etree.ElementTree as ET
    links = [node for node in ET.parse(directory/"network.net.xml").getroot().findall("connection") if node.get("tl") == "c"]
    return [int(link.get("from").split("_")[0] in "ew") for link in sorted(links, key=lambda link: int(link.get("linkIndex")))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))


if __name__ == "__main__":
    main()
