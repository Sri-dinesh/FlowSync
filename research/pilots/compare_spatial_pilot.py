#!/usr/bin/env python3
"""Audit fixed-budget spatial learning against the matched control and parents."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.audits.audit_training_results import audit_run, require
from research.pilots.compare_temporal_pilot import EXPECTED as BASE_EXPECTED, SEEDS, compare_paired_pilot
from research.pilots.compare_update_pressure_pilot import check_training_pair
from server.app.rl.observations import SPATIAL_CONTROL_VERSION, SPATIAL_VERSION

ARMS = {"control": SPATIAL_CONTROL_VERSION, "spatial": SPATIAL_VERSION}
EXPECTED = {**BASE_EXPECTED, "updates_per_episode": 4, "target_update": 25, "max_wall_seconds": 600}


def checks_against(pairs, reference):
    base = statistics.mean(p[reference]["delay"] for p in pairs)
    new = statistics.mean(p["spatial"]["delay"] for p in pairs)
    return {f"two_percent_delay_gain_vs_{reference}": base > 0 and new <= .98 * base,
        f"no_seed_over_one_percent_loss_vs_{reference}": all(p["spatial"]["delay"] <= 1.01*p[reference]["delay"] for p in pairs),
        f"no_p95_loss_vs_{reference}": statistics.mean(p["spatial"]["p95"] for p in pairs) <= statistics.mean(p[reference]["p95"] for p in pairs),
        f"no_throughput_loss_vs_{reference}": statistics.mean(p["spatial"]["throughput"] for p in pairs) >= statistics.mean(p[reference]["throughput"] for p in pairs)}


def screen(pairs):
    checks = checks_against(pairs, "control")
    checks["no_signal_violations"] = all(p[a]["signal_violations"] == 0 for p in pairs for a in ARMS)
    return dict(checks=checks, continue_to_expanded_validation=all(checks.values()),
        mean_delay_control=statistics.mean(p["control"]["delay"] for p in pairs),
        mean_delay_spatial=statistics.mean(p["spatial"]["delay"] for p in pairs))


def compare(directory):
    report = compare_paired_pilot(directory, arms=ARMS, expected=EXPECTED, arm_overrides={}, screen=screen,
        scope="Repeated development validation, not independent testing or superiority over strong baselines")
    parents = {}
    for seed in SEEDS:
        logs, demos = {}, {}
        for arm in ARMS:
            path = directory / f"{arm}_seed_{seed}"
            logs[arm] = [json.loads(l) for l in (path / "training.jsonl").read_text().splitlines()]
            demos[arm] = [json.loads(l) for l in (path / "demonstrations.jsonl").read_text().splitlines()]
            require(len(demos[arm]) == 24, "Incomplete demonstrations")
            require(all(r["executed_scenario"]["split"] == "train" for r in demos[arm]), "Non-training demonstrations")
        require(demos["control"] == demos["spatial"], "Unpaired demonstrations")
        check_training_pair(logs["control"], logs["spatial"])
        parents[seed] = next(r for r in audit_run(directory / f"control_seed_{seed}")["validation_curve"]
                             if r["checkpoint"] == "checkpoint_initial.pt")
    for point in report["common_checkpoint_curve"]:
        for pair in point["pairs"]:
            pair["parent"] = parents[pair["training_seed"]]
        point["checks"].update(checks_against(point["pairs"], "parent"))
        point["checks"]["all_runs_complete_at_episode_90"] = point["checkpoint"] == "checkpoint_90.pt" and all(
            r["episodes_completed"] == 90 and r["stop_reason"] == "completed" for r in report["completed_runs"])
        point["continue_to_expanded_validation"] = all(point["checks"].values())
        point["mean_delay_parent"] = statistics.mean(p["parent"]["delay"] for p in point["pairs"])
    report["primary_endpoint_complete"] = report["primary"]["checks"]["all_runs_complete_at_episode_90"]
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
