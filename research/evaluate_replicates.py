#!/usr/bin/env python3
"""Frozen-checkpoint evaluation across independent training and traffic seeds.

No optimization or checkpoint selection occurs here. Report all training seeds,
not the best replicate. Bootstrap units are training runs and paired traffic
seeds, not individual frames or vehicles. Scenarios are a fixed benchmark set.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import PerceptionFaultInjector
from research.run_headless_evaluation import noise_profile
from research.scenarios.scenario_schema import ScenarioConfig
from research.train_policy import file_hash
from server.app.controllers import get_controller


def execute(job):
    torch.set_num_threads(1)
    scenario = ScenarioConfig.load(job["scenario_path"])
    kwargs = dict(job.get("controller_options", {}))
    if job["checkpoint"]:
        kwargs["checkpoint_path"] = job["checkpoint"]
    if job["controller"] == "flowsync_uq" and job["calibration"]:
        kwargs["calibration_path"] = job["calibration"]
    ctrl = get_controller(job["controller"], **kwargs)
    if job.get("baseline_shield", False):
        ctrl = ShieldedController(ctrl)
    profile = noise_profile(job["condition"])
    injector = PerceptionFaultInjector(profile, job["seed"]+90000) if profile else None
    result = ExperimentRunner().run(ctrl, scenario, job["seed"], record_trajectory=False, fault_injector=injector)
    row = result.to_dict(include_trajectory=False)
    row.update(label=job["label"], training_seed=job["training_seed"], condition=job["condition"])
    return row


def crossed_bootstrap(differences, draws=5000, seed=717):
    """Array [training replicate, traffic seed, fixed scenario-condition]."""
    data = np.asarray(differences, dtype=float)
    if data.ndim != 3 or 0 in data.shape or not np.isfinite(data).all():
        raise ValueError("Expected complete finite crossed replicate/seed/condition data")
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        training = rng.integers(data.shape[0], size=data.shape[0])
        traffic = rng.integers(data.shape[1], size=data.shape[1])
        means.append(data[training][:, traffic, :].mean())
    return {"mean_delay_saved_s": float(data.mean()),
            "bootstrap_ci95_s": np.quantile(means, [.025,.975]).tolist(),
            "training_replicates": data.shape[0], "traffic_seeds": data.shape[1],
            "fixed_conditions": data.shape[2], "draws": draws,
            "caution": "Few training replicates; descriptive interval, not universal superiority"}


def evaluation_seeds(start, count, prior_manifests=()):
    """Reject accidental reuse of explicitly declared, previously inspected seeds."""
    if start < 0 or count < 1:
        raise ValueError("Seed start must be nonnegative and seed count positive")
    seeds = list(range(start, start + count))
    for path in prior_manifests:
        previous = json.loads(Path(path).read_text())["traffic_seeds"]
        overlap = sorted(set(seeds).intersection(previous))
        if overlap:
            raise ValueError(f"Traffic seeds overlap prior evaluation {path}: {overlap}")
    return seeds


def summarize(rows, matched_shield=False):
    lookup = {(r["label"], r["scenario_id"], r["condition"], r["seed"]): r for r in rows}
    if len(lookup) != len(rows):
        raise ValueError("Duplicate experiment cells")
    conditions = sorted({(r["scenario_id"], r["condition"]) for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    training_seeds = sorted({r["training_seed"] for r in rows if r["training_seed"] is not None})
    grouped = {}
    for label in sorted({r["label"] for r in rows}):
        subset = [r for r in rows if r["label"] == label]
        grouped[label] = {"runs": len(subset), "mean_delay": float(np.mean([r["avg_delay"] for r in subset])),
                          "mean_within_run_p95": float(np.mean([r["p95_delay"] for r in subset])),
                          "mean_throughput": float(np.mean([r["total_vehicles_passed"] for r in subset])),
                          "starvations": sum(r["starvation_count"] for r in subset),
                          "shield_interventions": sum(r["shield_interventions"] for r in subset),
                          "fallback_steps": sum(r["fallback_steps"] for r in subset),
                          "signal_violations": sum(r["executed_conflict_violations"]+r["executed_clearance_violations"] for r in subset)}
    comparisons = {}
    policies = ("d3qn", "d3qn_shield", "flowsync_uq") if matched_shield else ("d3qn", "flowsync_uq")
    baselines = ("fixed", "actuated", "greedy", "max_pressure", "max_pressure_shield") if matched_shield else ("fixed", "actuated", "greedy", "max_pressure")
    expected = {(label, sc, cond, seed) for sc, cond in conditions for seed in seeds
                for label in [*baselines, *(f"{name}_seed{train}" for name in policies for train in training_seeds)]}
    if not training_seeds or set(lookup) != expected:
        raise ValueError("Incomplete or unexpected crossed evaluation cells")
    for row in rows:
        if row["safety_samples"] != row["num_steps"]:
            raise ValueError("Incomplete executed-signal audit coverage")
    for proposed in policies:
        for baseline in baselines:
            delta = [[[lookup[(baseline, sc, cond, traffic)]["avg_delay"] -
                       lookup[(f"{proposed}_seed{train}", sc, cond, traffic)]["avg_delay"]
                       for sc, cond in conditions] for traffic in seeds] for train in training_seeds]
            comparisons[f"{proposed}_vs_{baseline}"] = crossed_bootstrap(delta)
            clean = [i for i, (_, condition) in enumerate(conditions) if condition == "clean"]
            if clean:
                comparisons[f"clean_{proposed}_vs_{baseline}"] = crossed_bootstrap(np.asarray(delta)[:, :, clean])
    paired_uq = [[[lookup[(f"d3qn_seed{train}", sc, cond, traffic)]["avg_delay"] -
                   lookup[(f"flowsync_uq_seed{train}", sc, cond, traffic)]["avg_delay"]
                   for sc, cond in conditions] for traffic in seeds] for train in training_seeds]
    comparisons["flowsync_uq_vs_same_d3qn"] = crossed_bootstrap(paired_uq)
    if matched_shield:
        # Report component effects and tails, not only the most favorable mean.
        # Positive saved delay favors the first policy named in each comparison.
        for proposed, reference in (("d3qn_shield", "max_pressure_shield"),
                                    ("d3qn_shield", "max_pressure"),
                                    ("d3qn_shield", "d3qn"),
                                    ("flowsync_uq", "d3qn_shield"),
                                    ("max_pressure_shield", "max_pressure")):
            for metric in ("avg_delay", "p95_delay"):
                delta = [[[lookup[(reference if reference in baselines else f"{reference}_seed{train}", sc, cond, traffic)][metric] -
                           lookup[(proposed if proposed in baselines else f"{proposed}_seed{train}", sc, cond, traffic)][metric]
                           for sc, cond in conditions] for traffic in seeds] for train in training_seeds]
                result = crossed_bootstrap(delta)
                comparisons[f"{proposed}_vs_{reference}_{metric}"] = {**result, "metric": metric}
    arrivals = {}
    for row in rows:
        arrivals.setdefault((row["scenario_id"], row["seed"]), set()).add(row["arrival_trace_hash"])
    if any(len(h) != 1 for h in arrivals.values()):
        raise ValueError("Paired arrival traces differ")
    condition_means = []
    for scenario, condition in conditions:
        for label in sorted(grouped):
            subset = [r for r in rows if (r["scenario_id"], r["condition"], r["label"]) == (scenario, condition, label)]
            condition_means.append({"scenario": scenario, "condition": condition, "label": label,
                                    "mean_delay": float(np.mean([r["avg_delay"] for r in subset]))})
    return {"summary": grouped, "comparisons": comparisons, "condition_means": condition_means,
            "arrival_traces_match": True,
            "publication_ready": False,
            "readiness_note": "Requires independent simulator validation, sufficient training replicates, methodological review and scoped claims"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selections", nargs="+", type=Path, required=True)
    p.add_argument("--uq-calibration", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed-start", type=int, default=51001)
    p.add_argument("--exclude-seeds-from", type=Path, action="append", default=[],
                   help="Prior evaluation manifest; reject reused traffic seeds (repeatable)")
    p.add_argument("--protocol", type=Path, default=ROOT/"research/docs/protocols/RESEARCH_PROTOCOL_20261014.md")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--matched-shield", action="store_true",
                   help="Require shield-selected checkpoints; compare bare/shield/UQ and shielded Max-Pressure")
    args = p.parse_args()
    if min(args.seeds, args.workers) < 1:
        p.error("Seeds/workers must be positive")
    traffic_seeds = evaluation_seeds(args.seed_start, args.seeds, args.exclude_seeds_from)
    protocol_text = args.protocol.read_text()
    scenarios = [ScenarioConfig.load(path) for path in sorted((ROOT/"research/scenarios/test").glob("*.yaml"))]
    if any(sc.split != "test" for sc in scenarios):
        raise ValueError("Final evaluation requires test-labeled scenarios")
    choices, training_seeds = [], set()
    for selection in args.selections:
        selected = json.loads(selection.read_text())
        expected_controller = "d3qn_shield" if args.matched_shield else "d3qn"
        if selected.get("evaluation_controller", "d3qn") != expected_controller:
            raise ValueError(f"This benchmark requires {expected_controller} selection; choose the matching --matched-shield setting")
        cp = Path(selected["path"])
        if file_hash(cp) != selected["sha256"]:
            raise ValueError("Selected checkpoint hash changed")
        metadata = torch.load(cp, map_location="cpu", weights_only=True)
        train = metadata["training_seed"]
        if train in training_seeds:
            raise ValueError("Training replicates must have distinct training seeds")
        if metadata.get("parent_checkpoint_sha256"):
            raise ValueError("Independent fresh-training evidence may not share a pretrained parent")
        training_seeds.add(train)
        choices.append({"path": str(cp.resolve()), "sha256": selected["sha256"], "training_seed": train,
                        "selection_controller": expected_controller,
                        "selection_sha256": file_hash(selection), "selection_path": str(selection.resolve())})
    args.output.mkdir(parents=True, exist_ok=False)
    jobs = []
    for scenario in scenarios:
        conditions = ["clean"]
        if scenario.scenario_id == "test_clean_balanced_01":
            conditions += ["miss_30", "latency_1000ms", "combined_severe"]
        for condition in conditions:
            for seed in traffic_seeds:
                common = {"scenario_path": str(ROOT/"research/scenarios/test"/f"{scenario.scenario_id}.yaml"),
                          "seed": seed, "condition": condition,
                          "calibration": str(args.uq_calibration.resolve()) if args.uq_calibration else None}
                for baseline in ("fixed", "actuated", "greedy", "max_pressure"):
                    jobs.append({**common, "controller": baseline, "label": baseline, "training_seed": None, "checkpoint": None})
                if args.matched_shield:
                    jobs.append({**common, "controller": "max_pressure", "label": "max_pressure_shield",
                                 "training_seed": None, "checkpoint": None, "baseline_shield": True})
                for choice in choices:
                    for controller in ("d3qn", "flowsync_uq"):
                        jobs.append({**common, "controller": controller, "label": f"{controller}_seed{choice['training_seed']}",
                                     "training_seed": choice["training_seed"], "checkpoint": choice["path"]})
                    if args.matched_shield:
                        jobs.append({**common, "controller": "flowsync_uq", "label": f"d3qn_shield_seed{choice['training_seed']}",
                                     "training_seed": choice["training_seed"], "checkpoint": choice["path"],
                                     "controller_options": {"enable_shield": True, "enable_fallback": False}})
    manifest = {"choices": choices, "traffic_seeds": traffic_seeds,
                "matched_shield": args.matched_shield, "jobs": jobs,
                "protocol_sha256": file_hash(args.protocol),
                "excluded_seed_manifests": {str(path.resolve()): file_hash(path) for path in args.exclude_seeds_from},
                "calibration_sha256": file_hash(args.uq_calibration) if args.uq_calibration else None,
                "scenario_hashes": {s.scenario_id: s.compute_hash() for s in scenarios},
                "fault_profiles": {name: noise_profile(name).to_dict()
                                   for name in ("miss_30", "latency_1000ms", "combined_severe")},
                "planned_runs": len(jobs), "test_policy": "No post-test tuning; report all training replicates",
                "source_hashes": {str(path.relative_to(ROOT)): file_hash(path)
                                  for base in (ROOT/"research", ROOT/"server/app") for path in sorted(base.rglob("*.py"))}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (args.output / "protocol.md").write_text(protocol_text)
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as snapshot:
        for source in manifest["source_hashes"]:
            snapshot.write(ROOT/source, source)
        for path in sorted((ROOT/"research/scenarios").rglob("*.yaml")):
            snapshot.write(path, str(path.relative_to(ROOT)))
        snapshot.write(ROOT/"research/docs/protocols/RESEARCH_PROTOCOL_20261014.md", "research/docs/protocols/RESEARCH_PROTOCOL_20261014.md")
        snapshot.write(args.output/"protocol.md", "evaluation_protocol.md")
    print(f"Frozen evaluation: {len(jobs)} runs; {len(choices)} training seeds; traffic seeds {traffic_seeds[0]}–{traffic_seeds[-1]}", flush=True)
    rows = []
    # One worker uses ordinary calls, avoiding unnecessary IPC/socket dependencies.
    pool = ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else None
    try:
        with (args.output/"runs.jsonl").open("x") as stream:
            results = pool.map(execute, jobs) if pool else map(execute, jobs)
            for i, row in enumerate(results, 1):
                rows.append(row)
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                if i % 50 == 0:
                    print(f"Completed {i}/{len(jobs)}", flush=True)
    finally:
        if pool:
            pool.shutdown()
    report = summarize(rows, matched_shield=args.matched_shield)
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
