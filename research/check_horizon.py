#!/usr/bin/env python3
"""Fixed-policy, 600-second sensitivity check; never selects/tunes a checkpoint."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evaluate_replicates import execute, summarize
from research.scenarios.scenario_schema import ScenarioConfig
from research.train_policy import file_hash


def extend_scenario(original, duration_steps=6000):
    data = original.to_dict()
    factor = duration_steps / original.duration_steps
    data.update(duration_steps=duration_steps, scenario_id=original.scenario_id + "_600s", scenario_hash="")
    for events in (data["demand_profile"]["burst_events"], data["demand_profile"]["incident_events"]):
        for event in events:
            event["start_step"] = round(event["start_step"] * factor)
            event["end_step"] = round(event["end_step"] * factor)
    return ScenarioConfig.from_dict(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen-run", type=Path, required=True)
    p.add_argument("--uq-calibration", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workers", type=int, default=3)
    args = p.parse_args()
    frozen = json.loads((args.frozen_run / "manifest.json").read_text())
    if file_hash(args.uq_calibration) != frozen["calibration_sha256"]:
        raise ValueError("Must use the same frozen calibration")
    for choice in frozen["choices"]:
        if file_hash(choice["path"]) != choice["sha256"]:
            raise ValueError("Frozen checkpoint changed")
    args.output.mkdir(parents=True, exist_ok=False)
    scenario_dir = args.output / "scenarios"
    scenario_dir.mkdir()
    seeds = [52001, 52002, 52003]
    jobs, scenarios = [], []
    for source in sorted((ROOT / "research/scenarios/test").glob("*.yaml")):
        sc = extend_scenario(ScenarioConfig.load(source))
        path = scenario_dir / (sc.scenario_id + ".yaml")
        sc.save(path)
        scenarios.append(sc)
        for seed in seeds:
            common = {"scenario_path": str(path.resolve()), "seed": seed, "condition": "clean",
                      "calibration": str(args.uq_calibration.resolve())}
            for baseline in ("fixed", "actuated", "greedy", "max_pressure"):
                jobs.append({**common, "controller": baseline, "label": baseline, "training_seed": None, "checkpoint": None})
            for choice in frozen["choices"]:
                for controller in ("d3qn", "flowsync_uq"):
                    jobs.append({**common, "controller": controller, "label": f"{controller}_seed{choice['training_seed']}",
                                 "training_seed": choice["training_seed"], "checkpoint": choice["path"]})
    manifest = {"choices": frozen["choices"], "traffic_seeds": seeds, "planned_runs": len(jobs),
                "calibration_sha256": frozen["calibration_sha256"],
                "scenario_hashes": {s.scenario_id: s.compute_hash() for s in scenarios},
                "method": "600s horizon; event start/end scaled by duration ratio; clean sensing only",
                "interpretation": "Sensitivity diagnostic: only three traffic seeds, not a replacement for the full evaluation",
                "source_hashes": {str(path.relative_to(ROOT)): file_hash(path)
                                  for base in (ROOT/"research", ROOT/"server/app") for path in sorted(base.rglob("*.py"))}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    rows = []
    print(f"Long-horizon sensitivity: {len(jobs)} runs, 600s each", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool, (args.output/"runs.jsonl").open("x") as stream:
        for i, row in enumerate(pool.map(execute, jobs), 1):
            rows.append(row)
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            if i % 20 == 0:
                print(f"Completed {i}/{len(jobs)}", flush=True)
    report = summarize(rows)
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print("Completed long-horizon sensitivity check", flush=True)


if __name__ == "__main__":
    main()
