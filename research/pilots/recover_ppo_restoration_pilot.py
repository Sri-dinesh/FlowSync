"""Recover an externally interrupted PPO panel into a new, auditable directory.

Keep the original untouched. Refit completed optimizer batches exactly and
advance the local sampler from recorded probabilities, including dropped final
proposals. Repeated episode prefixes must reproduce; they are not new samples.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import multiprocessing
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import torch

from research.pilots import run_ppo_restoration_pilot as pilot
from research.policies.ppo import ActorCritic, save_checkpoint
from research.training.ppo import collect_episode, update
from research.training.train_policy import RunBudget, BudgetExceeded

RECOVERY_SECONDS = 300


def advance_sampler(generator, summaries):
    for summary in summaries:
        for proposal in summary["proposals"]:
            action = int(torch.multinomial(torch.tensor(proposal["probabilities"], dtype=torch.float32),
                                           1, generator=generator)[0])
            if action != proposal["proposed"]:
                raise ValueError("Sampler replay differs from recorded proposal")


def rebuild(folder, parent, budget):
    torch.manual_seed(int(parent))
    model = ActorCritic.from_parent(pilot.PARENT_ROOT/pilot.PARENTS[parent][0])
    actor, critic = pilot.optimizers(model)
    updates = json.loads((folder/"updates.json").read_text()) if (folder/"updates.json").exists() else []
    summaries = [json.loads(line) for line in (folder/"episodes.jsonl").read_text().splitlines()]
    for index, batch in enumerate(updates):
        if batch["episode"] != (index+1)*6:
            raise ValueError("Incomplete saved update sequence")
        path = folder/f"batch_{batch['episode']}.npz"
        if pilot.sha(path) != batch["batch_sha256"]:
            raise ValueError("Saved batch hash mismatch")
        logs = update(model, pilot.load_batch(path), actor, critic, budget, warmup=batch["episode"] == 6)
        if logs != batch["updates"]:
            raise ValueError("Optimizer replay differs during recovery")
        checkpoint = folder/f"checkpoint_{batch['episode']}.pt"
        if checkpoint.exists():
            payload = torch.load(checkpoint, weights_only=True, map_location="cpu")
            if any(not torch.equal(v, payload["state_dict"][k]) for k, v in model.state_dict().items()):
                raise ValueError("Checkpoint reconstruction differs")
    completed = updates[-1]["episode"] if updates else 0
    generator = torch.Generator().manual_seed(int(parent))
    advance_sampler(generator, summaries[:completed])
    return model, actor, critic, generator, updates, summaries, completed


def existing_evaluations(folder, parent, arm, baseline=None):
    rows = []
    for path in sorted(folder.glob("*.json.gz")):
        with gzip.open(path, "rt") as stream:
            raw = json.load(stream)
        result, case = raw["result"], raw["case"]
        rows.append(dict(parent=parent, arm=arm, stage="baseline" if baseline else int(path.name.split("_", 1)[0]), baseline=baseline,
            case_id=case["case_id"], delay=result["avg_delay"], p95=result["p95_delay"],
            passed=result["total_vehicles_passed"], violations=result["executed_conflict_violations"]+result["executed_clearance_violations"],
            samples=result["safety_samples"], arrival_trace_hash=result["arrival_trace_hash"], checkpoint_hash=result["checkpoint_hash"],
            raw_file=str(path.relative_to(folder.parent)), raw_sha256=pilot.sha(path)))
    return rows


def recover_baseline(folder, parent, arm, name, development, deadline):
    if not folder.exists():
        return pilot.baseline_worker(folder, parent, arm, name, development, deadline)
    torch.set_num_threads(1)
    rows = existing_evaluations(folder, parent, arm, baseline=name)
    missing = [case for case in development if not any(r["case_id"] == case["case_id"] for r in rows)]
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    try:
        rows.extend(pilot.evaluate(folder, parent, arm, "baseline", missing, budget, baseline=name))
    except BudgetExceeded:
        pass
    pilot.write(folder/"baseline.json", rows)
    return rows


def recover_worker(folder, parent, arm, cases, development, deadline):
    if not folder.exists():
        return pilot.train_worker(folder, parent, arm, cases, development, deadline)
    torch.set_num_threads(1)
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    model, actor, critic, generator, updates, original_summaries, completed = rebuild(folder, parent, budget)
    summaries = original_summaries[:completed]
    # The old directory remains intact; the new copy rolls back only to its last
    # fully persisted update. Every repeated prefix is compared below.
    (folder/"episodes.jsonl").write_text("".join(json.dumps(s, allow_nan=False)+"\n" for s in summaries))
    evaluations = existing_evaluations(folder, parent, arm)
    pending = []
    repeated = []

    def evaluate_stage(stage):
        checkpoint = folder/f"checkpoint_{stage}.pt"
        if not checkpoint.exists():
            metadata = dict(episode=stage, training_seed=int(parent), input_arm=arm,
                parent_checkpoint_sha256=pilot.PARENTS[parent][1],
                restoration_sha256=pilot.RESTORER_HASHES[parent] if arm == "restored" else None,
                actor_updates=sum(r["kind"] == "actor" for b in updates for r in b["updates"]),
                critic_updates=sum(r["kind"] == "critic" for b in updates for r in b["updates"]))
            save_checkpoint(checkpoint, model, metadata)
        missing = [case for case in development if not any(r["stage"] == stage and r["case_id"] == case["case_id"] for r in evaluations)]
        evaluations.extend(pilot.evaluate(folder, parent, arm, stage, missing, budget, checkpoint=checkpoint))

    try:
        for stage in pilot.STAGES:
            if stage <= completed:
                evaluate_stage(stage)
        for case in cases[completed:]:
            rows, summary = collect_episode(model, pilot.ScenarioConfig.from_dict(case["scenario"]), case["seed"],
                pilot.injector(arm, parent, case["fault"], case["seed"]), generator, budget)
            summary.update(episode=case["episode"], fault=case["fault"])
            if case["episode"] <= len(original_summaries):
                if summary != original_summaries[case["episode"]-1]:
                    raise ValueError("Repeated interrupted training prefix differs")
                repeated.append(case["episode"])
            summaries.append(summary)
            with (folder/"episodes.jsonl").open("a") as stream:
                stream.write(json.dumps(summary, allow_nan=False)+"\n")
            pending.append(rows)
            completed = case["episode"]
            if completed % 6 == 0:
                path = folder/f"batch_{completed}.npz"
                pilot.store_batch(path, pending)
                logs = update(model, pending, actor, critic, budget, warmup=completed == 6)
                updates.append(dict(episode=completed, batch_sha256=pilot.sha(path), updates=logs))
                pilot.write(folder/"updates.json", updates)
                pending = []
            if completed in pilot.STAGES:
                evaluate_stage(completed)
                print(f"Recovered PPO {parent}/{arm}: episode {completed}/90", flush=True)
        complete = True
    except BudgetExceeded:
        complete = False
    result = dict(parent=parent, arm=arm, output=folder.name, complete=complete, episodes=completed,
        updates=updates, evaluations=evaluations, training_arrivals=[s["arrival_trace_hash"] for s in summaries],
        training_signal_audit=all(s["signal_samples"] == 1200 and s["signal_violations"] == 0 for s in summaries),
        recovered=True, exactly_repeated_prefix_episodes=repeated)
    pilot.write(folder/"worker.json", result)
    return result


def recover(source, output):
    source, output = source.resolve(), output.resolve()
    if output.exists() or (source/"report.json").exists():
        raise ValueError("Recovery needs an unsealed interrupted source and a new output directory")
    manifest = json.loads((source/"manifest.json").read_text())
    if manifest["plan"] != json.loads(json.dumps(pilot.PLAN)):
        raise ValueError("Original frozen protocol changed")
    if manifest["python_version"] != sys.version or manifest["torch_version"] != torch.__version__:
        raise ValueError("Recovery requires the original runtime")
    for parent, (name, expected) in pilot.PARENTS.items():
        if (pilot.sha(pilot.PARENT_ROOT/name) != expected or
                pilot.sha(pilot.RESTORATION/f"restorer_{parent}.pt") != pilot.RESTORER_HASHES[parent]):
            raise ValueError("Frozen parent/restorer changed")
    for name, expected in manifest["source_sha256"].items():
        if pilot.sha(pilot.ROOT/name) != expected:
            raise ValueError("Original executable source changed")
    inventory = {str(p.relative_to(source)): pilot.sha(p) for p in sorted(source.rglob("*")) if p.is_file()}
    shutil.copytree(source, output)
    (output/"recovery_source.py").write_bytes(Path(__file__).read_bytes())
    pilot.write(output/"recovery.json", dict(original_directory=str(source), original_file_sha256=inventory,
        recovery_source_sha256=pilot.sha(Path(__file__)), recovery_git_commit=pilot.ExperimentRunner.get_git_commit(),
        recovery_seconds=RECOVERY_SECONDS, processes=3,
        scope="Interrupted process recovery, unchanged model/seed/episode endpoints and scientific screen; completed results reused, exactly repeated prefixes are not independent samples. Original elapsed wall time was not sealed; report elapsed_seconds measures recovery only."))
    started = time.monotonic()
    deadline = started+RECOVERY_SECONDS
    workers, baselines, tasks = [], [], []
    for parent in pilot.PARENTS:
        for arm in ("raw", "restored"):
            folder = output/f"{parent}_{arm}"
            if (folder/"worker.json").exists():
                saved = json.loads((folder/"worker.json").read_text())
                if saved["complete"]:
                    workers.append(saved)
                    continue
            tasks.append((parent, arm))
    # Schedule by remaining episode count, before any performance inspection.
    def remaining(job):
        folder = output/f"{job[0]}_{job[1]}"
        updates = json.loads((folder/"updates.json").read_text()) if (folder/"updates.json").exists() else []
        return 90-(updates[-1]["episode"] if updates else 0)
    tasks.sort(key=remaining, reverse=True)
    with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(recover_worker, output/f"{p}_{a}", p, a, manifest["training_cases"],
                               manifest["validation_cases"], deadline): "worker" for p, a in tasks}
        for p, arm, name in pilot.baseline_jobs():
            futures[pool.submit(recover_baseline, output/f"baseline_{p}_{name}", p, arm, name,
                                manifest["validation_cases"], deadline)] = "baseline"
        for future in as_completed(futures):
            result = future.result()
            if futures[future] == "worker":
                workers.append(result)
            else:
                baselines.extend(result)
    workers.sort(key=lambda w: (w["parent"], w["arm"]))
    baselines.sort(key=lambda r: (r["baseline"], r["parent"], r["case_id"]))
    comparison = pilot.comparison(workers, baselines)
    report = dict(complete=comparison["primary_endpoint_complete"], comparison=comparison, workers=workers, baselines=baselines,
        elapsed_seconds=time.monotonic()-started, elapsed_scope="Recovery only; original run interrupted before sealing elapsed time",
        automatic_promotion=False, publication_ready=False)
    if inventory != {str(p.relative_to(source)): pilot.sha(p) for p in sorted(source.rglob("*")) if p.is_file()}:
        raise ValueError("Interrupted source changed during recovery")
    report["output_sha256"] = {str(p.relative_to(output)): pilot.sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    pilot.write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("workers", "baselines", "output_sha256")}


def verify_recovery(output, refit=False):
    result = pilot.verify(output, refit=refit)
    recovery = json.loads((output/"recovery.json").read_text())
    original = Path(recovery["original_directory"])
    inventory = {str(p.relative_to(original)): pilot.sha(p) for p in sorted(original.rglob("*")) if p.is_file()}
    if inventory != recovery["original_file_sha256"]:
        raise ValueError("Interrupted original was modified")
    if pilot.sha(output/"recovery_source.py") != recovery["recovery_source_sha256"]:
        raise ValueError("Recovery source snapshot mismatch")
    report = json.loads((output/"report.json").read_text())
    repeats = 0
    for worker in report["workers"]:
        if not worker.get("recovered"):
            continue
        current = [json.loads(line) for line in (output/worker["output"]/"episodes.jsonl").read_text().splitlines()]
        old = [json.loads(line) for line in (original/worker["output"]/"episodes.jsonl").read_text().splitlines()]
        for episode in worker["exactly_repeated_prefix_episodes"]:
            if current[episode-1] != old[episode-1]:
                raise ValueError("Recovered prefix is not an exact repeat")
            repeats += 1
        generator = torch.Generator().manual_seed(int(worker["parent"]))
        advance_sampler(generator, current)
    return {**result, "interrupted_original_unchanged": True, "exact_repeated_episodes": repeats,
            "elapsed_scope": report["elapsed_scope"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Interrupted directory, or completed recovery with --verify")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--refit", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if args.output:
            parser.error("--verify cannot also create output")
        result = verify_recovery(args.source, args.refit)
    else:
        if not args.output or args.refit:
            parser.error("Recovery needs --output; --refit requires --verify")
        result = recover(args.source, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
