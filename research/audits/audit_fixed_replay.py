#!/usr/bin/env python3
"""Bounded training-only fixed-data learning diagnostic; no checkpoint promotion."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
import torch.nn.functional as F

from research.pilots.compare_update_pressure_pilot import compare, SEEDS
from research.experiments.runtime import RESEARCH_REWARD_VERSION
from research.noise.fault_injector import FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.temporal_initialization import initialize_parent
from research.training.train_policy import BudgetExceeded, RunBudget, collect_episode
from server.app.controllers import get_controller
from server.app.rl.dqn_agent import DQNAgent

ARMS = ("fixed_labels", "moving_selector", "moving_target")
ONLINE_CASES = (1, 16, 31, 46, 61, 76)
STEPS = (0, 25, 50, 100, 200)
PROTOCOL = ROOT/"research/docs/protocols/FIXED_REPLAY_PROTOCOL_20261017.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_agent(checkpoint):
    agent = DQNAgent(36, "v7_36dim_observed")
    initialize_parent(agent, checkpoint)
    agent.prepare_for_finetuning(.0001)
    agent.demonstration_loss_weight = .5
    agent.reward_version = RESEARCH_REWARD_VERSION
    return agent


def tensorize(transitions):
    if not transitions:
        raise ValueError("Empty diagnostic dataset")
    names = ("states", "actions", "rewards", "next_states", "dones", "masks", "next_masks", "discounts", "demos")
    dtypes = (torch.float32, torch.long, torch.float32, torch.float32, torch.float32,
              torch.bool, torch.bool, torch.float32, torch.float32)
    data = {name: torch.as_tensor(np.asarray(column), dtype=dtype)
            for name, column, dtype in zip(names, zip(*transitions), dtypes)}
    if not all(torch.isfinite(x).all() for x in data.values()):
        raise ValueError("Non-finite replay")
    if not data["masks"].any(1).all() or not data["next_masks"].any(1).all():
        raise ValueError("Empty action mask")
    if not data["masks"].gather(1, data["actions"][:, None]).all():
        raise ValueError("Invalid recorded action")
    return data


@torch.no_grad()
def bellman_targets(agent, data):
    next_q = agent.online_net(data["next_states"], valid_action_mask=data["next_masks"])
    actions = next_q.masked_fill(~data["next_masks"], -torch.inf).argmax(1)
    target_q = agent.target_net(data["next_states"], valid_action_mask=data["next_masks"])
    return data["rewards"] + data["discounts"] * (1-data["dones"]) * target_q.gather(1, actions[:, None]).squeeze(1)


def batch_for(data, indices, fixed_labels=None):
    """Empty priority indices deliberately prevent mutation of a PER tree."""
    rewards = data["rewards"][indices] if fixed_labels is None else fixed_labels[indices]
    dones = data["dones"][indices] if fixed_labels is None else torch.ones_like(rewards)
    discounts = data["discounts"][indices] if fixed_labels is None else torch.zeros_like(rewards)
    return (data["states"][indices], data["actions"][indices], rewards,
            data["next_states"][indices], dones, torch.ones_like(rewards), [],
            data["masks"][indices], data["next_masks"][indices], discounts, data["demos"][indices])


@torch.no_grad()
def metrics(agent, data, labels, original_actions):
    q = agent.online_net(data["states"], valid_action_mask=data["masks"])
    chosen = q.gather(1, data["actions"][:, None]).squeeze(1)
    live = bellman_targets(agent, data)
    other = q.masked_fill(~data["masks"], -torch.inf).scatter(1, data["actions"][:, None], -torch.inf)
    alternative = data["masks"].sum(1) > 1
    margin = torch.where(alternative, F.relu(.5 + other.max(1).values-chosen), torch.zeros_like(chosen))
    demo_weights = data["demos"] * alternative.float()
    demo_loss = (margin*demo_weights).sum()/demo_weights.sum().clamp(min=1)
    fixed_huber = F.smooth_l1_loss(chosen, labels)
    result = dict(fixed_label_mae=(chosen-labels).abs().mean().item(), fixed_label_huber=fixed_huber.item(),
        live_td_mae=(chosen-live).abs().mean().item(), target_drift_mae=(live-labels).abs().mean().item(),
        demonstration_margin=demo_loss.item(), frozen_joint_objective=(fixed_huber+.5*demo_loss).item(),
        action_disagreement=(q.masked_fill(~data["masks"], -torch.inf).argmax(1)!=original_actions).float().mean().item())
    if not all(np.isfinite(v) for v in result.values()):
        raise ValueError("Non-finite full-dataset diagnostic")
    return result


def load_cases(path):
    demos = [json.loads(s) for s in (path/"demonstrations.jsonl").read_text().splitlines()]
    online = [json.loads(s) for s in (path/"training.jsonl").read_text().splitlines()]
    lookup = {row["episode"]: row for row in online}
    if len(lookup) != len(online) or len(demos) < 6 or not set(ONLINE_CASES) <= set(lookup):
        raise ValueError("Missing/duplicate training records")
    cases = []
    for origin, rows in (("demo", demos[:6]), ("online", [lookup[e] for e in ONLINE_CASES])):
        for i, row in enumerate(rows):
            scenario = ScenarioConfig.from_dict(row["executed_scenario"])
            if scenario.split != "train":
                raise ValueError("Only training scenarios allowed")
            cases.append(dict(origin=origin, case=i, partition="fit" if i < 4 else "probe",
                scenario=scenario.to_dict(), seed=row["seed"], fault=row["fault"]))
    return cases


def collect_dataset(checkpoint, cases, budget):
    agent = new_agent(checkpoint)
    transitions, records = {"fit": [], "probe": []}, []
    for case in cases:
        before = len(agent.replay_buffer)
        result = collect_episode(agent, ScenarioConfig.from_dict(case["scenario"]), case["seed"],
            FaultProfile(**case["fault"]), 0., teacher=get_controller("max_pressure") if case["origin"]=="demo" else None,
            learn=False, budget=budget, train_with_shield=True)
        after = len(agent.replay_buffer)
        if after <= before or after >= agent.replay_buffer.capacity:
            raise ValueError("Missing or wrapped diagnostic replay")
        transitions[case["partition"]].extend(agent.replay_buffer.tree.data[before:after])
        records.append(dict(**case, transitions=after-before, result=result))
    if agent.step_count or any(not torch.equal(v, agent.online_net.state_dict()[k])
                               for k,v in checkpoint["online_net"].items()):
        raise ValueError("Collection altered parent policy")
    return {part: tensorize(rows) for part,rows in transitions.items()}, records


def run_seed(seed, checkpoint, datasets, output, budget):
    initial = new_agent(checkpoint)
    labels = {part: bellman_targets(initial, data).clone() for part,data in datasets.items()}
    with torch.no_grad():
        actions = {part: initial.online_net(d["states"], valid_action_mask=d["masks"])
                   .masked_fill(~d["masks"], -torch.inf).argmax(1) for part,d in datasets.items()}
    schedule = torch.from_numpy(np.random.default_rng(77000+seed).integers(
        len(datasets["fit"]["states"]), size=(200, 128)))
    dataset_path = output/f"seed_{seed}_dataset.pt"
    torch.save(dict(datasets=datasets, labels=labels, initial_actions=actions, schedule=schedule), dataset_path)
    digest = sha(dataset_path)
    for arm in ARMS:
        agent = new_agent(checkpoint)
        for step in range(201):
            budget.check("fixed_replay_updates")
            if step:
                batch = batch_for(datasets["fit"], schedule[step-1], labels["fit"] if arm=="fixed_labels" else None)
                loss, _ = agent.train_step(batch)
                if not np.isfinite(loss):
                    raise ValueError("Non-finite training loss")
                if arm == "moving_target" and step % 25 == 0:
                    agent.sync_target_network()
            if step in STEPS:
                row = dict(seed=seed, arm=arm, updates=step, dataset_sha256=digest,
                    metrics={part: metrics(agent, d, labels[part], actions[part]) for part,d in datasets.items()})
                with (output/"curves.jsonl").open("a") as stream:
                    stream.write(json.dumps(row, allow_nan=False)+"\n")
        if arm != "moving_target" and any(not torch.equal(v, agent.target_net.state_dict()[k])
                                           for k,v in checkpoint["online_net"].items()):
            raise ValueError("Held target changed")
        print(f"seed={seed} arm={arm}: 200 updates complete", flush=True)
    if sha(dataset_path) != digest:
        raise ValueError("Frozen dataset changed")


def summarize(rows):
    expected = {(s,a,u) for s in SEEDS for a in ARMS for u in STEPS}
    if len(rows) != len(expected) or {(r["seed"],r["arm"],r["updates"]) for r in rows} != expected:
        raise ValueError("Incomplete/duplicate learning curves")
    for seed in SEEDS:
        initial = [r for r in rows if r["seed"]==seed and r["updates"]==0]
        if not all(r["metrics"]==initial[0]["metrics"] for r in initial):
            raise ValueError("Unmatched initial metrics")
        if len({r["dataset_sha256"] for r in rows if r["seed"]==seed}) != 1:
            raise ValueError("Unmatched datasets")
    aggregate = []
    for arm in ARMS:
        for step in (0,200):
            selected = [r for r in rows if r["arm"]==arm and r["updates"]==step]
            aggregate.append(dict(arm=arm, updates=step, metrics={part:{key:float(np.mean(
                [r["metrics"][part][key] for r in selected])) for key in selected[0]["metrics"][part]}
                for part in ("fit","probe")}))
    return dict(complete=True, aggregate=aggregate, curves=len(rows), publication_ready=False,
                scope="Fixed training replay fitting diagnostics, not traffic-performance evidence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output directory")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    comparison = compare(args.batch)
    if comparison != json.loads((args.batch/"comparison.json").read_text()):
        raise ValueError("Input comparison does not reproduce")
    batch = json.loads((args.batch/"batch_manifest.json").read_text())
    cases = {s:load_cases(args.batch/f"control_seed_{s}") for s in SEEDS}
    inputs = [args.batch/"comparison.json", args.batch/"batch_manifest.json", args.batch/"source_snapshot.zip"]
    for seed in SEEDS:
        inputs.extend([Path(batch["parents"][str(seed)]["path"]),
                       args.batch/f"control_seed_{seed}/training.jsonl",
                       args.batch/f"control_seed_{seed}/demonstrations.jsonl"])
    hashes = {str(p.resolve()):sha(p) for p in inputs}
    sources = [p for base in (ROOT/"research",ROOT/"server/app") for p in sorted(base.rglob("*.py"))]+[PROTOCOL]
    args.output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(source, str(source.relative_to(ROOT)))
    manifest = dict(input_hashes=hashes, cases=cases, source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},
                    max_wall_seconds=240, seeds=SEEDS, arms=ARMS, steps=STEPS, test_access=False)
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    budget = RunBudget(240)
    try:
        collected, checkpoints = {}, {}
        for seed in SEEDS:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            checkpoint = torch.load(batch["parents"][str(seed)]["path"], map_location="cpu", weights_only=True)
            datasets, records = collect_dataset(checkpoint, cases[seed], budget)
            (args.output/f"seed_{seed}_collection.json").write_text(json.dumps(records, indent=2))
            collected[seed], checkpoints[seed] = datasets, checkpoint
        for seed in SEEDS:
            run_seed(seed, checkpoints[seed], collected[seed], args.output, budget)
        rows = [json.loads(s) for s in (args.output/"curves.jsonl").read_text().splitlines()]
        report = summarize(rows)
    except BudgetExceeded as exc:
        report = dict(complete=False, stop_reason=str(exc), publication_ready=False)
    if any(sha(Path(p)) != digest for p,digest in hashes.items()):
        raise ValueError("Diagnostic input changed during execution")
    report["elapsed_seconds"] = budget.elapsed
    (args.output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
