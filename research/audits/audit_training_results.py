#!/usr/bin/env python3
"""Read-only validation-selection integrity audit. Never runs training or test scenarios."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics


def read_json(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_run(directory: Path) -> dict:
    manifest = read_json(directory / "manifest.json")
    summary = read_json(directory / "summary.json")
    require(manifest.get("test_access") is False, "Run does not declare validation-only selection")
    require(summary["training_seed"] == manifest["arguments"]["seed"], "Training seed mismatch")
    controller = manifest["selection_controller"]
    expected = set(itertools.product(manifest["validation_scenarios"],
                                    manifest["validation_seeds"],
                                    [f["name"] for f in manifest["validation_faults"]]))
    require(bool(expected), "Empty validation design")
    arrivals, curve, incomplete = {}, [], []
    files = sorted(directory.glob("validation_*.json"), key=lambda p:
                   -2 if p.stem == "validation_initial" else
                   -1 if p.stem == "validation_warmup" else int(p.stem.split("_")[-1]))
    if summary["stop_reason"] == "completed":
        arguments = manifest["arguments"]
        require(summary["episodes_completed"] == arguments["episodes"], "Completed run episode count mismatch")
        labels = {"initial", "warmup"}
        labels.update(str(n) for n in range(arguments["validate_every"], arguments["episodes"] + 1,
                                            arguments["validate_every"]))
        if arguments["episodes"]:
            labels.add(str(arguments["episodes"]))
        require({p.stem.removeprefix("validation_") for p in files} == labels,
                "Completed run is missing scheduled validations or contains unexpected candidates")
    for path in files:
        data = read_json(path)
        label = path.stem.removeprefix("validation_")
        if data.get("complete") is not True:
            incomplete.append(label)
            continue
        require(data.get("selection_controller") == controller, f"{label}: selection controller mismatch")
        rows = [r for r in data["rows"] if r["controller"] == controller]
        keys = [(r["scenario"], r["seed"], r["fault"]) for r in rows]
        require(len(keys) == len(expected) and set(keys) == expected,
                f"{label}: missing, duplicate or unexpected validation cells")
        checkpoint = directory / f"checkpoint_{label}.pt"
        digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        for row in rows:
            require(row["checkpoint_hash"] == digest, f"{label}: checkpoint hash mismatch")
            for metric in ("delay", "p95", "throughput", "conflicts", "clearance_violations", "starvations"):
                require(isinstance(row[metric], (int, float)) and math.isfinite(row[metric])
                        and row[metric] >= 0, f"{label}: invalid {metric}")
        # Baselines, faults and successive checkpoints must see the same arrivals.
        for row in data["rows"]:
            key = (row["scenario"], row["seed"])
            arrival = row["arrivals_hash"]
            require(bool(arrival) and arrivals.setdefault(key, arrival) == arrival,
                    f"{label}: paired arrival mismatch")
        score = statistics.mean(r["delay"] for r in rows)
        require(math.isclose(score, data["score"], rel_tol=1e-12, abs_tol=1e-12),
                f"{label}: reported score differs from rows")
        curve.append({"checkpoint": checkpoint.name, "sha256": digest, "delay": score,
                      "p95": statistics.mean(r["p95"] for r in rows),
                      "throughput": statistics.mean(r["throughput"] for r in rows),
                      "signal_violations": sum(r["conflicts"] + r["clearance_violations"] for r in rows)})
    require(bool(curve), "No completed validation available; no assessable selection")
    require(summary["stop_reason"] != "completed" or not incomplete,
            "Completed run contains incomplete validation")
    selection = read_json(directory / "selection.json")
    require(summary["best"] == selection, "Summary and selection disagree")
    selected = min(curve, key=lambda row: row["delay"])
    require(Path(selection["path"]).name == selected["checkpoint"]
            and selection["sha256"] == selected["sha256"], "Selection is not the first validation minimum")
    require(selection["evaluation_controller"] == controller, "Selected controller mismatch")
    require(math.isclose(selection["score"], selected["delay"], rel_tol=1e-12, abs_tol=1e-12),
            "Selected score mismatch")
    warmup = next((r for r in curve if r["checkpoint"] == "checkpoint_warmup.pt"), None)
    return {"directory": str(directory), "integrity_checks_passed": True,
            "training_seed": summary["training_seed"], "stop_reason": summary["stop_reason"],
            "episodes_completed": summary["episodes_completed"],
            "reward_version": manifest.get("reward_version", "not recorded in legacy manifest"),
            "selected": selected, "validation_curve": curve, "incomplete_validation": incomplete,
            "delay_saved_from_warmup": warmup["delay"] - selected["delay"] if warmup else None,
            "publication_ready": False,
            "scope": "Artifact consistency only; not execution attestation or independent performance evidence"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+", help="Individual seed/run directories")
    args = parser.parse_args()
    reports, failed = [], False
    for directory in args.runs:
        try:
            reports.append(audit_run(directory))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            reports.append({"directory": str(directory), "integrity_checks_passed": False, "error": str(exc)})
            failed = True
    print(json.dumps(reports, indent=2, allow_nan=False))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
