#!/usr/bin/env python3
"""Audit the predeclared low-update pilot; never select on final-test results."""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_training_results import audit_run, read_json, require
from research.compare_temporal_pilot import EXPECTED as TEMPORAL_EXPECTED, SEEDS, compare_paired_pilot

ARMS = dict(control="v7_36dim_observed", low_updates="v7_36dim_observed")
EXPECTED = {**TEMPORAL_EXPECTED, "expand_v7_parent": False}
OVERRIDES = dict(control=dict(updates_per_episode=32, target_update=200),
                 low_updates=dict(updates_per_episode=4, target_update=25))


def screen_against(pairs, baseline):
    base = statistics.mean(p[baseline]["delay"] for p in pairs)
    low = statistics.mean(p["low_updates"]["delay"] for p in pairs)
    return {
        f"mean_delay_improves_two_percent_vs_{baseline}": base > 0 and low <= base*.98,
        f"no_seed_regresses_over_one_percent_vs_{baseline}": all(
            p["low_updates"]["delay"] <= p[baseline]["delay"]*1.01 for p in pairs),
        f"no_mean_p95_regression_vs_{baseline}": statistics.mean(p["low_updates"]["p95"] for p in pairs)
            <= statistics.mean(p[baseline]["p95"] for p in pairs),
        f"no_mean_throughput_regression_vs_{baseline}": statistics.mean(p["low_updates"]["throughput"] for p in pairs)
            >= statistics.mean(p[baseline]["throughput"] for p in pairs),
    }


def screen(pairs):
    checks = screen_against(pairs, "control")
    checks["no_signal_violations"] = all(p[a]["signal_violations"] == 0 for p in pairs for a in ARMS)
    means = {a: statistics.mean(p[a]["delay"] for p in pairs) for a in ARMS}
    return dict(checks=checks, continue_to_expanded_validation=all(checks.values()),
                mean_delay_control=means["control"], mean_delay_low_updates=means["low_updates"],
                mean_delay_saved_s=means["control"]-means["low_updates"])


def check_training_pair(control, low):
    """Match exogenous inputs, not policy-dependent replay or trajectories."""
    keys = ("scenario", "seed", "fault", "executed_scenario", "epsilon", "demonstration_loss_weight")
    for left, right in zip(control, low):
        require(all(left[k] == right[k] for k in keys), "Unpaired training inputs")
        require(left["executed_scenario"]["split"] == "train", "Non-training replay input")
    for rows in (control, low):
        for row in rows:
            for key in ("unweighted_td_loss", "pre_clip_gradient_norm", "importance_weight_min",
                        "importance_weight_max", "td_error_mean"):
                value = row["q_stats"][key]
                require(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0,
                        "Invalid learning diagnostic")


def compare(directory):
    report = compare_paired_pilot(directory, arms=ARMS, expected=EXPECTED,
        arm_overrides=OVERRIDES, screen=screen,
        scope="Development update-pressure screen, not an independent test or proof of superiority")
    parents = {}
    for seed in SEEDS:
        logs, demonstrations = {}, {}
        for arm in ARMS:
            path = directory/f"{arm}_seed_{seed}"
            logs[arm] = [json.loads(line) for line in (path/"training.jsonl").read_text().splitlines()]
            demonstrations[arm] = [json.loads(line) for line in (path/"demonstrations.jsonl").read_text().splitlines()]
            require(len(demonstrations[arm]) == EXPECTED["demo_episodes"], "Incomplete demonstrations")
            require(all(r["executed_scenario"]["split"] == "train" for r in demonstrations[arm]),
                    "Non-training demonstration input")
        require(demonstrations["control"] == demonstrations["low_updates"], "Unpaired demonstrations")
        check_training_pair(logs["control"], logs["low_updates"])
        parents[seed] = next(r for r in audit_run(directory/f"control_seed_{seed}")["validation_curve"]
                             if r["checkpoint"] == "checkpoint_initial.pt")
    for point in report["common_checkpoint_curve"]:
        for pair in point["pairs"]:
            pair["parent"] = parents[pair["training_seed"]]
        point["checks"].update(screen_against(point["pairs"], "parent"))
        point["checks"]["all_runs_reached_primary_episode_90"] = (
            point["checkpoint"] == "checkpoint_90.pt" and
            all(r["episodes_completed"] == 90 and r["stop_reason"] == "completed" for r in report["completed_runs"]))
        point["continue_to_expanded_validation"] = all(point["checks"].values())
        point["mean_delay_parent"] = statistics.mean(p["parent"]["delay"] for p in point["pairs"])
    report["primary_endpoint_complete"] = report["primary"]["checks"]["all_runs_reached_primary_episode_90"]
    report["target_refresh_episode_ratio"] = 6.25
    return report


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
