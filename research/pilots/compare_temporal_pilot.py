#!/usr/bin/env python3
"""Compare fixed-budget temporal/control arms without choosing a winning seed."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import torch
from research.audits.audit_training_results import audit_run, read_json, require
from server.app.rl.observations import TEMPORAL_CONTROL_VERSION, TEMPORAL_VERSION, OBSERVATION_DIMS

ARMS = {"control": TEMPORAL_CONTROL_VERSION, "temporal": TEMPORAL_VERSION}
SEEDS = (101, 202, 303)
EXPECTED = dict(episodes=90, demo_episodes=24, imitation_updates=0, pretrain_updates=0,
    updates_per_episode=32, learning_rate=.0001, validate_every=30, target_update=200,
    domain_randomization=True, episode_steps=1200, validation_seeds=[21001, 21002],
    skip_initial_baselines=True, demo_loss_weight=.5, train_with_shield=True,
    expand_v7_parent=True, max_wall_seconds=360, clean_only=False,
    demo_loss_final_weight=None, demo_loss_decay_episodes=0)


def common_online_labels(curves):
    common = set.intersection(*({r["checkpoint"] for r in curve} for curve in curves))
    require({"checkpoint_initial.pt", "checkpoint_warmup.pt"} <= common, "Initial/warmup validation missing")
    online = sorted((name for name in common if name not in ("checkpoint_initial.pt", "checkpoint_warmup.pt")),
                    key=lambda name: int(name.removeprefix("checkpoint_").removesuffix(".pt")))
    require(bool(online), "No common completed online validation across all six runs")
    return online


def continuation_screen(pairs):
    """Engineering continuation criteria only; no significance or readiness claim."""
    control = statistics.mean(p["control"]["delay"] for p in pairs)
    temporal = statistics.mean(p["temporal"]["delay"] for p in pairs)
    checks = dict(mean_delay_improves_two_percent=control > 0 and temporal <= control * .98,
        no_seed_regresses_over_one_percent=all(p["temporal"]["delay"] <= p["control"]["delay"] * 1.01 for p in pairs),
        no_mean_p95_regression=statistics.mean(p["temporal"]["p95"] for p in pairs)
            <= statistics.mean(p["control"]["p95"] for p in pairs),
        no_mean_throughput_regression=statistics.mean(p["temporal"]["throughput"] for p in pairs)
            >= statistics.mean(p["control"]["throughput"] for p in pairs),
        no_signal_violations=all(p[a]["signal_violations"] == 0 for p in pairs for a in ARMS))
    return dict(checks=checks, continue_to_expanded_validation=all(checks.values()),
                mean_delay_control=control, mean_delay_temporal=temporal,
                mean_delay_saved_s=control-temporal)


def compare_paired_pilot(directory, *, arms, expected, arm_overrides, screen, scope):
    """Shared integrity checks for two-arm, fixed-episode-budget development pilots."""
    require(len(arms) == 2, "Expected exactly two pilot arms")
    varying_arguments = {k for overrides in arm_overrides.values() for k in overrides}
    batch = read_json(directory / "batch_manifest.json")
    with zipfile.ZipFile(directory / "source_snapshot.zip") as archive:
        require(all(hashlib.sha256(archive.read(k)).hexdigest() == v for k, v in batch["source_hashes"].items()),
                "Batch source archive mismatch")
    audits, inputs, initial_rows = {}, {}, {}
    shared = shared_design = None
    for seed in SEEDS:
        parent = batch["parents"][str(seed)]
        require(hashlib.sha256(Path(parent["path"]).read_bytes()).hexdigest() == parent["sha256"], "Parent changed")
        original = torch.load(parent["path"], map_location="cpu", weights_only=True)["online_net"]
        for arm, version in arms.items():
            path = directory / f"{arm}_seed_{seed}"
            audit = audit_run(path)
            manifest = read_json(path / "manifest.json")
            args = manifest["arguments"]
            arm_expected = {**expected, **arm_overrides.get(arm, {})}
            require(all(args.get(k) == v for k, v in arm_expected.items()), "Unexpected pilot configuration")
            updates = arm_expected["updates_per_episode"]
            require(args["seed"] == seed and args["observation_version"] == version, "Arm/seed mismatch")
            require(manifest["parent_sha256"] == parent["sha256"], "Parent provenance mismatch")
            require(all(batch["source_hashes"].get(k) == v for k, v in manifest["source_hashes"].items()),
                    "Training sources differ from frozen batch")
            common = {k: v for k, v in args.items() if k not in
                      {"output", "checkpoint", "seed", "observation_version", *varying_arguments}}
            if shared is None:
                shared = common
            require(shared == common, "Confounded paired arguments")
            design = {k: manifest[k] for k in ("training_scenarios", "validation_scenarios",
                "validation_seeds", "validation_faults", "reward_version", "shield_enabled",
                "fallback_enabled", "online_update_schedule", "parent_initialization", "observation_schema")}
            if shared_design is None:
                shared_design = design
            require(design == shared_design, "Confounded evaluation/training design")
            initial = torch.load(path / "checkpoint_initial.pt", map_location="cpu", weights_only=True)
            require(initial["obs_version"] == version, "Initial observation version mismatch")
            for key, value in original.items():
                child = initial["online_net"][key]
                if args["expand_v7_parent"] and key == "feature_layer.0.weight":
                    require(child.shape == (value.shape[0], OBSERVATION_DIMS[version]) and not child[:, 36:].any(), "Nonzero added columns")
                    child = child[:, :36]
                require(torch.equal(value, child), "Initial policy does not preserve parent weights")
            logs = [json.loads(line) for line in (path / "training.jsonl").read_text().splitlines()]
            require([r["episode"] for r in logs] == list(range(1, audit["episodes_completed"]+1)), "Incomplete episode log")
            require(all(r["online_updates"] == updates and r["total_updates"] == updates*r["episode"] for r in logs),
                    "Unequal optimizer budget")
            require(all(isinstance(r["loss"], (int, float)) and math.isfinite(r["loss"]) for r in logs),
                    "Non-finite training loss")
            for candidate in audit["validation_curve"]:
                label = candidate["checkpoint"].removeprefix("checkpoint_").removesuffix(".pt")
                data = read_json(path / f"validation_{label}.json")
                rows = data["rows"]
                require(all(r["safety_samples"] == r["expected_safety_samples"] > 0 for r in rows),
                        "Incomplete signal audit")
                for row in rows:
                    key = row["scenario"], row["seed"]
                    require(inputs.setdefault(key, row["arrivals_hash"]) == row["arrivals_hash"], "Unpaired arrivals")
                    if label == "initial":
                        key = seed, row["scenario"], row["seed"], row["fault"]
                        metrics = tuple(row[k] for k in ("delay", "p95", "throughput", "conflicts", "clearance_violations"))
                        require(initial_rows.setdefault(key, metrics) == metrics, "Initial trajectories disagree")
                state = torch.load(path / candidate["checkpoint"], map_location="cpu", weights_only=True)
                require(all(torch.isfinite(w).all() for w in state["online_net"].values()), "Non-finite checkpoint weights")
                expected_updates = int(label)*updates if label.isdigit() else 0
                require(state["total_train_steps"] == expected_updates and state["obs_version"] == version,
                        "Checkpoint update count/version mismatch")
            audits[(seed, arm)] = audit
    labels = common_online_labels([a["validation_curve"] for a in audits.values()])
    curve = []
    all_candidates_safe = all(r["signal_violations"] == 0 for a in audits.values() for r in a["validation_curve"])
    for checkpoint in labels:
        pairs = [{"training_seed": seed, **{arm: next(r for r in audits[(seed, arm)]["validation_curve"]
                   if r["checkpoint"] == checkpoint) for arm in arms}} for seed in SEEDS]
        curve.append(dict(checkpoint=checkpoint, pairs=pairs, **screen(pairs)))
        curve[-1]["checks"]["all_completed_candidates_have_no_signal_violations"] = all_candidates_safe
        curve[-1]["continue_to_expanded_validation"] &= all_candidates_safe
    return dict(comparison_available=True, primary=curve[-1], common_checkpoint_curve=curve,
        completed_runs=[dict(training_seed=s, arm=a, episodes_completed=v["episodes_completed"], stop_reason=v["stop_reason"])
                        for (s, a), v in audits.items()],
        publication_ready=False, automatic_promotion=False,
        scope=scope)


def compare(directory):
    return compare_paired_pilot(directory, arms=ARMS, expected=EXPECTED,
        arm_overrides={}, screen=continuation_screen,
        scope="Development screen at latest common fixed-update checkpoint; not proof of superiority")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.batch)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps(dict(comparison_available=False, error=str(exc), publication_ready=False)))
        raise SystemExit(1)
    print(json.dumps(result, indent=2, allow_nan=False))
