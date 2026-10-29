"""Frozen, bounded on-policy alternative to the unsuccessful DQN fine-tuning path."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import statistics
import sys
import time
import zipfile

import numpy as np
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.observation.count_restoration import RestorationInjector
from research.pilots.run_count_restoration_pilot import raw_controller
from research.pilots.run_switch_margin_pilot import PARENTS, PARENT_ROOT, ROOT, sha, write
from research.policies.ppo import ActorCritic, PPOController, save_checkpoint
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.ppo import Transition, collect_episode, update
from research.training.train_policy import (
    RunBudget, BudgetExceeded, load_split, training_scenario, VALIDATION_FAULTS,
)

RESTORATION = ROOT/"results/count_restoration/pilot_20261029"
RESTORER_HASHES = {
    "101": "04b43e25e3821dd73b2ab735b12e4c427b7c897cc79acc28f8cf9cc52b4d07ff",
    "202": "0d7cc9c9a01700e1cb162cfc88d3eb124f3d957e230d13306dad2dec5c88c48b",
    "303": "c954f705f02cbfe6c8bbf4d6855d0411488f7e195055cf6fa004131702334871",
}
STAGES = (0, 6, 30, 60, 90)
PLAN = dict(
    schema_version="ppo_restoration_pilot_v1", max_wall_seconds=600, processes=3,
    hypothesis="On-policy clipped policy gradients may improve the existing policy where bootstrapped DQN updates degraded it; test frozen restoration with a matched raw-input PPO control.",
    primary="Restored PPO at exactly episode 90, equal weight across all three parents. No checkpoint/replicate selection.",
    arms=["raw", "restored"], parents=PARENTS, restorers=RESTORER_HASHES,
    architecture="Copy entire 36-input dueling parent as categorical logits (temperature 1); freeze its common value head. Independent 36-64-64-1 tanh critic, zero output layer. Initial greedy policy exactly matches parent.",
    training=dict(episodes=90, horizon_ticks=1200, batch_episodes=6, actor_warmup_episodes=6,
        optimizer="Adam", actor_lr=.0001, critic_lr=.001, actor_epochs=4, critic_epochs=8,
        critic_warmup_epochs=20, clip=.2, entropy=.01, target_kl=.02, gradient_clip=.5,
        gamma=.99, gae_lambda=.95, decision_ticks=20, schedule_seed=1330001,
        episode_seed_rule="1331001 + zero-based episode index; paired across all workers",
        scenarios="Six train templates, shuffled once per batch; randomized demand using existing training_scenario.",
        faults="Known clean/mixed presets alternate by global episode index; raw/restored share packets and exogenous plans.",
        sampling="Independent local Torch generator per training replicate; sampled proposals stored before additional shield.",
        transitions="Completed decision-to-decision only; gamma and gamma*lambda raised to elapsed ticks/20; discard final partial macro; bootstrap last complete next gate; reset GAE at episode boundary.",
        targets="One frozen batch of old log probabilities, values and GAE returns per update. Full batch, normalized advantages, no demonstrations/TD/replay/target network.",
        limits="At most 56 actor and 132 critic updates per worker; actor KL early stop checked before each step, not a formal KL bound."),
    evaluation=dict(stages=STAGES, cases="Three existing validation templates, new traffic seeds 1333001+i, clean/mixed: six cases per stage; greedy inference.",
        baselines="Each original parent raw/restored/default UQ; matched shielded pressure raw/EMA/restored-per-model; bare raw pressure. 90 baseline runs plus 180 PPO curve runs.",
        screen="At fixed episode 90 restored PPO: >=2% aggregate delay gain vs raw PPO, original raw/restored parents, raw/EMA/restored shielded and bare pressure. No aggregate p95/throughput loss vs any reference; no replicate >1% delay loss vs corresponding learned/pressure reference; all workers/paired runs complete, warmup/initial parity and zero measured signal violations.",
        exposure="Development on known scenario/fault families, not fresh final confirmation or simulator/camera transfer."),
    scope="Established PPO/GAE with a project-specific SMDP/sensor/shield adapter; no algorithmic novelty, public deployment or superiority claim from implementation alone.",
    references=["https://arxiv.org/abs/1707.06347", "https://arxiv.org/abs/1506.02438"],
    automatic_promotion=False, publication_ready=False)


def training_cases():
    rng = np.random.default_rng(1330001)
    templates = load_split("train")
    if len(templates) != 6:
        raise ValueError("Expected six training templates")
    result = []
    for batch in range(15):
        for index in rng.permutation(6):
            episode = len(result)
            scenario = training_scenario(templates[index], rng, 1200, True)
            result.append(dict(episode=episode+1, seed=1331001+episode, scenario=scenario.to_dict(),
                               fault=asdict(VALIDATION_FAULTS[episode % 2])))
    return result


def validation_cases():
    templates = load_split("validation")
    if len(templates) != 3 or any(s.duration_steps != 1200 for s in templates):
        raise ValueError("Unexpected validation panel")
    return [dict(case_id=f"{s.scenario_id}_{fault.name}", scenario=s.to_dict(),
                 seed=1333001+i, fault=asdict(fault))
            for i, s in enumerate(templates) for fault in VALIDATION_FAULTS]


def injector(arm, parent, fault, seed):
    profile = FaultProfile(**fault)
    if arm == "restored":
        return RestorationInjector(profile, seed+90000, model_path=RESTORATION/f"restorer_{parent}.pt")
    if arm == "ema":
        return RestorationInjector(profile, seed+90000, alpha=.2)
    return PerceptionFaultInjector(profile, seed=seed+90000)


def evaluate(output, parent, arm, stage, cases, budget, checkpoint=None, baseline=None):
    rows = []
    for case in cases:
        budget.check("PPO development evaluation")
        if checkpoint:
            controller = ShieldedController(PPOController(checkpoint))
        else:
            controller = raw_controller("pressure" if baseline.startswith("pressure") else parent,
                                        uq=baseline == "uq", bare=baseline == "pressure_bare")
        result = ExperimentRunner().run(controller, ScenarioConfig.from_dict(case["scenario"]), case["seed"],
            record_trajectory=True, fault_injector=injector(arm, parent, case["fault"], case["seed"]))
        target = output/f"{stage}_{case['case_id']}.json.gz"
        with gzip.open(target, "wt") as stream:
            json.dump(dict(case=case, result=result.to_dict()), stream, allow_nan=False)
        rows.append(dict(parent=parent, arm=arm, stage=stage, baseline=baseline,
            case_id=case["case_id"], delay=result.avg_delay, p95=result.p95_delay,
            passed=result.total_vehicles_passed, violations=result.executed_conflict_violations+result.executed_clearance_violations,
            samples=result.safety_samples, arrival_trace_hash=result.arrival_trace_hash, checkpoint_hash=result.checkpoint_hash,
            raw_file=str(target.relative_to(output.parent)), raw_sha256=sha(target)))
    return rows


def store_batch(path, episodes):
    rows = [t for episode in episodes for t in episode]
    np.savez_compressed(path, lengths=np.asarray([len(e) for e in episodes]),
        states=np.stack([t.state for t in rows]), masks=np.stack([t.mask for t in rows]),
        next_states=np.stack([t.next_state for t in rows]),
        **{key: np.asarray([getattr(t, key) for t in rows])
           for key in ("action", "log_probability", "value", "reward", "ticks", "next_value")})


def load_batch(path):
    with np.load(path, allow_pickle=False) as data:
        rows = [Transition(data["states"][i], data["masks"][i], int(data["action"][i]),
            *[float(data[key][i]) for key in ("log_probability", "value", "reward")],
            int(data["ticks"][i]), float(data["next_value"][i]), data["next_states"][i]) for i in range(len(data["states"]))]
        if sum(data["lengths"]) != len(rows):
            raise ValueError("Batch episode lengths do not cover transitions")
        episodes, offset = [], 0
        for length in data["lengths"]:
            episodes.append(rows[offset:offset+length])
            offset += length
    return episodes


def optimizers(model):
    return (torch.optim.Adam([p for p in model.actor.parameters() if p.requires_grad], lr=.0001),
            torch.optim.Adam(model.critic.parameters(), lr=.001))


def train_worker(output, parent, arm, cases, development, deadline):
    torch.set_num_threads(1)
    torch.manual_seed(int(parent))
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    output.mkdir()
    model = ActorCritic.from_parent(PARENT_ROOT/PARENTS[parent][0])
    actor_optimizer, critic_optimizer = optimizers(model)
    generator = torch.Generator().manual_seed(int(parent))
    evaluations, updates, episodes, pending = [], [], [], []
    completed = 0

    def checkpoint(episode):
        path = output/f"checkpoint_{episode}.pt"
        metadata = dict(episode=episode, training_seed=int(parent), input_arm=arm,
            parent_checkpoint_sha256=PARENTS[parent][1],
            restoration_sha256=RESTORER_HASHES[parent] if arm == "restored" else None,
            actor_updates=sum(row["kind"] == "actor" for batch in updates for row in batch["updates"]),
            critic_updates=sum(row["kind"] == "critic" for batch in updates for row in batch["updates"]))
        save_checkpoint(path, model, metadata)
        evaluations.extend(evaluate(output, parent, arm, episode, development, budget, checkpoint=path))

    try:
        checkpoint(0)
        for case in cases:
            budget.check("PPO training episode")
            transitions, summary = collect_episode(model, ScenarioConfig.from_dict(case["scenario"]), case["seed"],
                injector(arm, parent, case["fault"], case["seed"]), generator, budget)
            summary.update(episode=case["episode"], fault=case["fault"])
            episodes.append(summary)
            with (output/"episodes.jsonl").open("a") as stream:
                stream.write(json.dumps(summary, allow_nan=False)+"\n")
            pending.append(transitions)
            completed = case["episode"]
            if completed % 6 == 0:
                batch_path = output/f"batch_{completed}.npz"
                store_batch(batch_path, pending)
                logs = update(model, pending, actor_optimizer, critic_optimizer, budget, warmup=completed == 6)
                updates.append(dict(episode=completed, batch_sha256=sha(batch_path), updates=logs))
                write(output/"updates.json", updates)
                pending = []
            if completed in STAGES:
                checkpoint(completed)
                print(f"PPO {parent}/{arm}: episode {completed}/90", flush=True)
        complete = True
    except BudgetExceeded:
        complete = False
    result = dict(parent=parent, arm=arm, output=output.name, complete=complete, episodes=completed,
                  updates=updates, evaluations=evaluations,
                  training_arrivals=[e["arrival_trace_hash"] for e in episodes],
                  training_signal_audit=all(e["signal_samples"] == 1200 and e["signal_violations"] == 0 for e in episodes))
    write(output/"worker.json", result)
    return result


def baseline_jobs():
    return [(parent, arm, name) for parent in PARENTS for arm, name in
            (("raw", "parent_raw"), ("restored", "parent_restored"), ("raw", "uq"), ("restored", "pressure_restored"))] + [
            ("101", "raw", "pressure_raw"), ("101", "ema", "pressure_ema"), ("101", "raw", "pressure_bare")]


def baseline_worker(output, parent, arm, name, cases, deadline):
    torch.set_num_threads(1)
    output.mkdir()
    rows = []
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    try:
        rows = evaluate(output, parent, arm, "baseline", cases, budget, baseline=name)
    except BudgetExceeded:
        pass
    write(output/"baseline.json", rows)
    return rows


def means(rows):
    return {key: statistics.mean(row[key] for row in rows) for key in ("delay", "p95", "passed")}


def comparison(workers, baselines):
    if (len(workers) != 6 or any(not w["complete"] or w["episodes"] != 90 or len(w["evaluations"]) != 30 for w in workers)
            or len(baselines) != 90):
        return dict(primary_endpoint_complete=False, continue_to_expanded_validation=False)
    rows = [r for w in workers for r in w["evaluations"]]
    candidate = [r for r in rows if r["arm"] == "restored" and r["stage"] == 90]
    references = {"ppo_raw": [r for r in rows if r["arm"] == "raw" and r["stage"] == 90]}
    for name in ("parent_raw", "parent_restored", "pressure_raw", "pressure_ema", "pressure_restored", "pressure_bare"):
        references[name] = [r for r in baselines if r["baseline"] == name]
    primary = means(candidate)
    checks = {}
    for name, group in references.items():
        base = means(group)
        checks[f"two_percent_delay_vs_{name}"] = primary["delay"] <= .98*base["delay"]
        checks[f"no_p95_loss_vs_{name}"] = primary["p95"] <= base["p95"]
        checks[f"no_throughput_loss_vs_{name}"] = primary["passed"] >= base["passed"]
        checks[f"no_replicate_over_one_percent_loss_vs_{name}"] = all(
            means([r for r in candidate if r["parent"] == parent])["delay"] <= 1.01*means(
                [r for r in group if r["parent"] == parent] if name not in ("pressure_raw", "pressure_ema", "pressure_bare") else group)["delay"]
            for parent in PARENTS)
    parity = []
    for worker in workers:
        for case in validation_cases():
            group = [r for r in worker["evaluations"] if r["case_id"] == case["case_id"] and r["stage"] in (0, 6)]
            parent = [r for r in baselines if r["parent"] == worker["parent"] and
                      r["baseline"] == f"parent_{worker['arm']}" and r["case_id"] == case["case_id"]]
            parity.append(len(group) == 2 and len(parent) == 1 and all(means([r]) == means(parent) for r in group))
    checks["initial_and_critic_warmup_parity"] = all(parity)
    all_rows = rows+baselines
    arrivals = {}
    for row in all_rows:
        arrivals.setdefault(row["case_id"], set()).add(row["arrival_trace_hash"])
    checks["paired_arrivals"] = all(len(value) == 1 for value in arrivals.values())
    checks["executed_signal_audit"] = all(r["samples"] == 1200 and r["violations"] == 0 for r in all_rows)
    checks["training_signal_audit"] = all(w["training_signal_audit"] for w in workers)
    checks["paired_training_arrivals"] = (all(len(w["training_arrivals"]) == 90 for w in workers)
        and all(len({w["training_arrivals"][i] for w in workers}) == 1 for i in range(90)))
    return dict(primary_endpoint_complete=True, primary=primary, reference_means={n: means(g) for n, g in references.items()},
        curve={f"{arm}_{stage}": means([r for r in rows if r["arm"] == arm and r["stage"] == stage])
               for arm in ("raw", "restored") for stage in STAGES},
        per_parent={p: {arm: means([r for r in rows if r["parent"] == p and r["arm"] == arm and r["stage"] == 90])
                       for arm in ("raw", "restored")} for p in PARENTS},
        checks=checks, continue_to_expanded_validation=all(checks.values()))


def run(output):
    torch.set_num_threads(1)
    for parent, (path, expected) in PARENTS.items():
        if sha(PARENT_ROOT/path) != expected or sha(RESTORATION/f"restorer_{parent}.pt") != RESTORER_HASHES[parent]:
            raise ValueError("Frozen parent or restoration model changed")
    training, development = training_cases(), validation_cases()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    paths = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    manifest = dict(plan=PLAN, training_cases=training, validation_cases=development,
        git_commit=ExperimentRunner.get_git_commit(), python_version=sys.version, torch_version=torch.__version__,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths})
    write(output/"manifest.json", manifest)
    with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, str(path.relative_to(ROOT)))
    start = time.monotonic()
    deadline = start+600
    workers, baselines = [], []
    with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {pool.submit(train_worker, output/f"{p}_{arm}", p, arm, training, development, deadline): output/f"{p}_{arm}"
                   for p in PARENTS for arm in ("raw", "restored")}
        for future in as_completed(futures):
            result = future.result()
            workers.append(result)
        if all(w["complete"] for w in workers) and time.monotonic() < deadline:
            jobs = [pool.submit(baseline_worker, output/f"baseline_{p}_{name}", p, arm, name, development, deadline)
                    for p, arm, name in baseline_jobs()]
            for future in as_completed(jobs):
                baselines.extend(future.result())
    workers.sort(key=lambda w: (w["parent"], w["arm"]))
    baselines.sort(key=lambda r: (r["baseline"], r["parent"], r["case_id"]))
    summary = comparison(workers, baselines)
    report = dict(complete=summary["primary_endpoint_complete"], comparison=summary, workers=workers, baselines=baselines,
        elapsed_seconds=time.monotonic()-start, automatic_promotion=False, publication_ready=False)
    report["output_sha256"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output/"report.json", report)
    return {key: value for key, value in report.items() if key not in ("workers", "baselines", "output_sha256")}


def smoke(output):
    """Training-only mechanics, never a continuation/performance screen."""
    torch.set_num_threads(1)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    budget = RunBudget(60)
    case = dict(case_id="training_mechanics", scenario=load_split("train")[0].to_dict(),
                seed=1330901, fault=asdict(VALIDATION_FAULTS[1]))
    results = []
    for arm in ("raw", "restored"):
        folder = output/arm
        folder.mkdir()
        torch.manual_seed(101)
        model = ActorCritic.from_parent(PARENT_ROOT/PARENTS["101"][0])
        initial = {k: v.clone() for k, v in model.state_dict().items()}
        metadata = dict(episode=0, training_seed=101, input_arm=arm, parent_checkpoint_sha256=PARENTS["101"][1],
                        restoration_sha256=RESTORER_HASHES["101"] if arm == "restored" else None)
        save_checkpoint(folder/"initial.pt", model, metadata)
        baseline = evaluate(folder, "101", arm, "parent", [case], budget, baseline=f"parent_{arm}")
        start = evaluate(folder, "101", arm, 0, [case], budget, checkpoint=folder/"initial.pt")
        transitions, summary = collect_episode(model, ScenarioConfig.from_dict(case["scenario"]), case["seed"],
            injector(arm, "101", case["fault"], case["seed"]), torch.Generator().manual_seed(101), budget)
        store_batch(folder/"batch.npz", [transitions])
        actor, critic = optimizers(model)
        logs = update(model, [transitions], actor, critic, budget)
        copy = ActorCritic()
        copy.load_state_dict(initial)
        copy_actor, copy_critic = optimizers(copy)
        refit = update(copy, load_batch(folder/"batch.npz"), copy_actor, copy_critic, budget)
        exact = logs == refit and all(torch.equal(v, copy.state_dict()[k]) for k, v in model.state_dict().items())
        save_checkpoint(folder/"updated.pt", model, {**metadata, "episode": 1})
        end = evaluate(folder, "101", arm, 1, [case], budget, checkpoint=folder/"updated.pt")
        results.append(dict(arm=arm, initial_parent_parity=means(start) == means(baseline),
            exact_optimizer_refit=exact, actor_weights_changed=any(not torch.equal(v, initial[k])
                for k, v in model.state_dict().items() if k.startswith("actor.")),
            rollout=summary, optimizer=logs, evaluations=baseline+start+end))
    checks = dict(initial_parent_parity=all(r["initial_parent_parity"] for r in results),
        exact_optimizer_refits=all(r["exact_optimizer_refit"] for r in results),
        actor_weights_move=all(r["actor_weights_changed"] for r in results),
        complete_signal_samples=all(r["rollout"]["signal_samples"] == 1200 and r["rollout"]["signal_violations"] == 0 and
            all(e["samples"] == 1200 and e["violations"] == 0 for e in r["evaluations"]) for r in results))
    report = dict(smoke=True, checks=checks, verified_mechanics=all(checks.values()), results=results,
        elapsed_seconds=budget.elapsed, publication_ready=False, automatic_promotion=False,
        scope="One parent, two arms, training-only mechanics; not a policy-performance screen")
    write(output/"smoke.json", report)
    if not report["verified_mechanics"]:
        raise ValueError("PPO integration smoke failed")
    return {k: v for k, v in report.items() if k != "results"}


def verify(output, refit=False):
    torch.set_num_threads(1)
    report = json.loads((output/"report.json").read_text())
    manifest = json.loads((output/"manifest.json").read_text())
    if not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)):
        raise ValueError("Incomplete panel or changed protocol")
    if manifest["python_version"] != sys.version or manifest["torch_version"] != torch.__version__:
        raise ValueError("Verification requires original runtime")
    files = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file() and p.name != "report.json"}
    if files != set(report["output_sha256"]) or any(sha(output/p) != h for p, h in report["output_sha256"].items()):
        raise ValueError("Output hash/coverage mismatch")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(manifest["source_sha256"]):
            raise ValueError("Source archive coverage mismatch")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Historical verification requires archived sources")
    if manifest["training_cases"] != training_cases() or manifest["validation_cases"] != validation_cases():
        raise ValueError("Changed case plan")
    for parent, (name, expected) in PARENTS.items():
        if sha(PARENT_ROOT/name) != expected or sha(RESTORATION/f"restorer_{parent}.pt") != RESTORER_HASHES[parent]:
            raise ValueError("Changed frozen model")
    expected_workers = {(p, a) for p in PARENTS for a in ("raw", "restored")}
    if len(report["workers"]) != 6 or {(w["parent"], w["arm"]) for w in report["workers"]} != expected_workers:
        raise ValueError("Worker coverage mismatch")
    all_rows = list(report["baselines"])
    refits = 0
    for worker in report["workers"]:
        path = output/f"{worker['parent']}_{worker['arm']}"
        summaries = [json.loads(line) for line in (path/"episodes.jsonl").read_text().splitlines()]
        if len(summaries) != 90 or len(worker["updates"]) != 15:
            raise ValueError("Incomplete training")
        for saved, case in zip(summaries, manifest["training_cases"]):
            if any(saved[k] != case[k] for k in ("episode", "seed", "scenario", "fault")) or saved["signal_samples"] != 1200:
                raise ValueError("Training plan/coverage mismatch")
        if worker["training_signal_audit"] != all(e["signal_samples"] == 1200 and e["signal_violations"] == 0 for e in summaries):
            raise ValueError("Training audit summary mismatch")
        if worker["training_arrivals"] != [e["arrival_trace_hash"] for e in summaries]:
            raise ValueError("Training arrival trace summary mismatch")
        expected_evaluations = {(stage, case["case_id"]) for stage in STAGES for case in validation_cases()}
        if (len(worker["evaluations"]) != 30 or
                {(r["stage"], r["case_id"]) for r in worker["evaluations"]} != expected_evaluations or
                any(r["parent"] != worker["parent"] or r["arm"] != worker["arm"] or r["baseline"] is not None for r in worker["evaluations"])):
            raise ValueError("Checkpoint curve coverage mismatch")
        for stage in STAGES:
            payload = torch.load(path/f"checkpoint_{stage}.pt", weights_only=True, map_location="cpu")
            metadata = payload["metadata"]
            if metadata["episode"] != stage or metadata["parent_checkpoint_sha256"] != PARENTS[worker["parent"]][1]:
                raise ValueError("Checkpoint lineage mismatch")
            if (metadata["training_seed"] != int(worker["parent"]) or metadata["input_arm"] != worker["arm"] or
                    metadata["restoration_sha256"] != (RESTORER_HASHES[worker["parent"]] if worker["arm"] == "restored" else None)):
                raise ValueError("Checkpoint arm mismatch")
        for batch in worker["updates"]:
            batch_path = path/f"batch_{batch['episode']}.npz"
            if sha(batch_path) != batch["batch_sha256"]:
                raise ValueError("Optimizer batch hash mismatch")
            episodes = load_batch(batch_path)
            summary = summaries[batch["episode"]-6:batch["episode"]]
            if len(episodes) != 6 or any(len(e) != s["transitions"] or
                any(t.action != p["proposed"] or t.mask.tolist() != p["mask"] for t, p in zip(e, s["proposals"]))
                for e, s in zip(episodes, summary)):
                raise ValueError("Saved proposals/transitions mismatch")
        if refit:
            torch.manual_seed(int(worker["parent"]))
            model = ActorCritic.from_parent(PARENT_ROOT/PARENTS[worker["parent"]][0])
            actor, critic = optimizers(model)
            for batch in worker["updates"]:
                episodes = load_batch(path/f"batch_{batch['episode']}.npz")
                transitions = [t for episode in episodes for t in episode]
                with torch.no_grad():
                    values = model.values(torch.as_tensor(np.stack([t.state for t in transitions])))
                    next_values = model.values(torch.as_tensor(np.stack([t.next_state for t in transitions])))
                if (not np.allclose(values.numpy(), [t.value for t in transitions], rtol=1e-4, atol=1e-4) or
                        not np.allclose(next_values.numpy(), [t.next_value for t in transitions], rtol=1e-4, atol=1e-4)):
                    raise ValueError("Recorded rollout critic values differ")
                logs = update(model, episodes, actor, critic, RunBudget(60), warmup=batch["episode"] == 6)
                if logs != batch["updates"]:
                    raise ValueError("Optimizer update refit differs")
                if batch["episode"] in STAGES:
                    payload = torch.load(path/f"checkpoint_{batch['episode']}.pt", weights_only=True, map_location="cpu")
                    if any(not torch.equal(value, payload["state_dict"][key]) for key, value in model.state_dict().items()):
                        raise ValueError("Refitted policy differs")
            refits += 1
        all_rows.extend(worker["evaluations"])
    expected_baselines = {(p, arm, name, c["case_id"]) for p, arm, name in baseline_jobs() for c in validation_cases()}
    if len(report["baselines"]) != 90 or {(r["parent"], r["arm"], r["baseline"], r["case_id"]) for r in report["baselines"]} != expected_baselines:
        raise ValueError("Baseline coverage mismatch")
    for row in all_rows:
        with gzip.open(output/row["raw_file"], "rt") as stream:
            raw = json.load(stream)
        case = next(c for c in validation_cases() if c["case_id"] == row["case_id"])
        if raw["case"] != case:
            raise ValueError("Raw evaluation case mismatch")
        result = raw["result"]
        values = dict(delay=result["avg_delay"], p95=result["p95_delay"], passed=result["total_vehicles_passed"],
            samples=result["safety_samples"], violations=result["executed_conflict_violations"]+result["executed_clearance_violations"],
            arrival_trace_hash=result["arrival_trace_hash"], checkpoint_hash=result["checkpoint_hash"])
        if any(row[k] != v for k, v in values.items()) or sha(output/row["raw_file"]) != row["raw_sha256"]:
            raise ValueError("Raw evaluation mismatch")
        if row["baseline"] is None:
            expected = sha(output/f"{row['parent']}_{row['arm']}"/f"checkpoint_{row['stage']}.pt")
        elif not row["baseline"].startswith("pressure"):
            expected = PARENTS[row["parent"]][1]
        else:
            expected = row["checkpoint_hash"]
        if row["checkpoint_hash"] != expected:
            raise ValueError("Evaluated checkpoint mismatch")
        if row["arm"] == "restored" and result["fault_diagnostics"]["restoration_sha256"] != RESTORER_HASHES[row["parent"]]:
            raise ValueError("Evaluated restorer mismatch")
    if report["comparison"] != comparison(report["workers"], report["baselines"]):
        raise ValueError("Summary/screen reconstruction differs")
    return dict(verified=True, training_workers=6, optimizer_refits=refits, development_runs=len(all_rows),
                independently_rerun_traffic_trajectories=0, comparison=report["comparison"], publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    mode.add_argument("--smoke-output", type=Path)
    parser.add_argument("--refit", action="store_true", help="Also replay all saved optimizer batches exactly")
    args = parser.parse_args()
    if args.refit and not args.verify:
        parser.error("--refit requires --verify")
    result = verify(args.verify, args.refit) if args.verify else smoke(args.smoke_output) if args.smoke_output else run(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
