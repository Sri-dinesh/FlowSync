#!/usr/bin/env python3
"""Select a completed bare-training control with shield-only VALIDATION.

Never overwrites the original selection or loads test scenarios. All scheduled
candidate checkpoints are evaluated, including initialization and warmup.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import torch
from research.training.train_policy import file_hash, load_split, preserve_rng, validation, VALIDATION_FAULTS


def candidate_labels(episodes, interval):
    if episodes < 1 or interval < 1:
        raise ValueError("Episode count and validation interval must be positive")
    checkpoints = sorted(set(range(interval, episodes + 1, interval)) | {episodes})
    return ["initial", "warmup", *map(str, checkpoints)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads((args.training_run / "manifest.json").read_text())
    summary = json.loads((args.training_run / "summary.json").read_text())
    recipe = original["arguments"]
    if summary.get("stop_reason") != "completed" or summary["episodes_completed"] != recipe["episodes"]:
        raise ValueError("Matched control requires a completed training schedule")
    if recipe.get("train_with_shield", False) or original.get("parent_sha256"):
        raise ValueError("Control must be independent, fresh, bare-policy training")
    labels = candidate_labels(recipe["episodes"], recipe["validate_every"])
    paths = {label: args.training_run / f"checkpoint_{label}.pt" for label in labels}
    hashes = {label: file_hash(path) for label, path in paths.items()}
    scenarios = {s.scenario_id: s.compute_hash() for s in load_split("validation")}
    if scenarios != original["validation_scenarios"]:
        raise ValueError("Validation scenarios changed since control training")
    faults = [asdict(f) for f in VALIDATION_FAULTS]
    if faults != original["validation_faults"]:
        raise ValueError("Validation fault profiles changed since control training")
    seeds = original["validation_seeds"]
    torch.set_num_threads(1)
    for path in paths.values():
        metadata = torch.load(path, map_location="cpu", weights_only=True)
        if metadata["training_seed"] != recipe["seed"] or metadata.get("parent_checkpoint_sha256"):
            raise ValueError("Candidate does not belong to the independent control training run")
    args.output.mkdir(parents=True, exist_ok=False)
    config = {"training_run": str(args.training_run.resolve()), "training_seed": recipe["seed"],
              "original_manifest_sha256": file_hash(args.training_run / "manifest.json"),
              "candidate_hashes": hashes, "candidate_order": labels, "validation_seeds": seeds,
              "validation_scenarios": scenarios, "validation_faults": original["validation_faults"],
              "planned_runs": len(labels)*len(scenarios)*len(seeds)*len(faults),
              "selection_controller": "d3qn_shield", "fallback_enabled": False,
              "selection_rule": "minimum mean validation delay; retain incumbent on ties",
              "test_access": False,
              "source_hashes": {str(p.relative_to(ROOT)): file_hash(p)
                                for base in (ROOT/"research", ROOT/"server/app") for p in base.rglob("*.py")}}
    (args.output / "configuration.json").write_text(json.dumps(config, indent=2))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in config["source_hashes"]:
            archive.write(ROOT/path, path)
        for path in (ROOT/"research/scenarios/validation").glob("*.yaml"):
            archive.write(path, str(path.relative_to(ROOT)))
    best, scores = None, {}
    for label, path in paths.items():
        if file_hash(path) != hashes[label]:
            raise ValueError("Candidate changed during frozen selection")
        score = preserve_rng(lambda: validation(path, args.output, label, seeds=seeds,
                                               train_with_shield=True))
        scores[label] = score
        if best is None or score < best["score"]:
            best = {"path": str(path.resolve()), "sha256": hashes[label], "score": score,
                    "episode": int(label) if label.isdigit() else 0,
                    "evaluation_controller": "d3qn_shield"}
        print(f"seed={recipe['seed']} {label}: shielded validation={score:.4f}s", flush=True)
    (args.output / "selection.json").write_text(json.dumps(best, indent=2))
    (args.output / "summary.json").write_text(json.dumps({"complete": True, "best": best,
        "scores": scores, "training_seed": recipe["seed"], "publication_ready": False}, indent=2))
    print(json.dumps(best), flush=True)


if __name__ == "__main__":
    main()
