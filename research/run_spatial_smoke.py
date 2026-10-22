#!/usr/bin/env python3
"""Bounded, training-only mechanics smoke for the two matched v9 policy arms."""
import argparse
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.evaluate_averaged_action_labels import write
from research.noise.fault_injector import PerceptionFaultInjector
from research.spatial_baselines import UpstreamMaxPressureController
from research.temporal_initialization import initialize_parent
from research.train_policy import (
    BudgetExceeded, RunBudget, VALIDATION_FAULTS, collect_episode, file_hash,
    fixed_episode_updates, load_split, training_fault, training_scenario,
)
from server.app.controllers import get_controller
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import SPATIAL_CONTROL_VERSION, SPATIAL_VERSION, SPATIAL_SCHEMA

PROTOCOL = ROOT / "research/SPATIAL_INPUT_EXPERIMENT_PLAN_20261021.md"
SEED = 97301
EVALUATION_SEED = 97302
ARMS = {"control": SPATIAL_CONTROL_VERSION, "spatial": SPATIAL_VERSION}


def schedule():
    scenarios, rng = load_split("train"), np.random.default_rng(SEED)
    demos = [(training_scenario(scenarios[i % len(scenarios)], rng, 1200, True),
              100000 + SEED * 1000 + i, training_fault(rng, True)) for i in range(24)]
    online = (training_scenario(scenarios[int(rng.integers(len(scenarios)))], rng, 1200, True),
              500000 + SEED * 1000 + 1, training_fault(rng, True))
    return demos, online


def train_arm(parent, version, output, budget, demos, online):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    agent = DQNAgent(48, version)
    agent.reward_version = "v5_single_switch_delay"
    initialize_parent(agent, parent, expand_v7=True)
    agent.prepare_for_finetuning(1e-4)
    agent.demonstration_loss_weight = .5
    initial = {k: v.clone() for k, v in agent.online_net.state_dict().items()}
    output.mkdir()

    def save(name):
        payload = agent.get_checkpoint_state()
        payload.update(training_seed=SEED, observation_schema=SPATIAL_SCHEMA,
                       parent_checkpoint_sha256=parent["audit_parent_sha256"], mechanics_smoke=True)
        path = output / f"checkpoint_{name}.pt"
        torch.save(payload, path)
        return path

    paths = dict(initial=save("initial"))
    teacher = get_controller("max_pressure")
    with (output / "collection.jsonl").open("x") as stream:
        for index, (scenario, seed, fault) in enumerate(demos):
            budget.check("spatial_smoke_demonstrations")
            row = collect_episode(agent, scenario, seed, fault, epsilon=0., teacher=teacher,
                                  learn=False, train_with_shield=True, budget=budget)
            stream.write(json.dumps(dict(row, role="demonstration", episode=index), allow_nan=False) + "\n")
            stream.flush()
        scenario, seed, fault = online
        row = collect_episode(agent, scenario, seed, fault, epsilon=.05, learn=False,
                              train_with_shield=True, budget=budget)
        stream.write(json.dumps(dict(row, role="online", episode=1), allow_nan=False) + "\n")
    loss = fixed_episode_updates(agent, 4, 25, budget)
    paths["trained"] = save("trained")
    current = agent.online_net.state_dict()
    metrics = dict(replay_transitions=len(agent.replay_buffer), optimizer_updates=agent.step_count,
                   loss=loss, diagnostics=agent.latest_q_stats,
                   weights_changed=any(not torch.equal(current[k], v) for k, v in initial.items()),
                   extension_max_absolute_weight=float(current["feature_layer.0.weight"][:, 36:].abs().max()))
    write(output / "summary.json", metrics)
    return paths, metrics


def evaluate(paths, parent_path, budget, cells, stream):
    runner = ExperimentRunner()
    labels = ["parent", *paths, "max_pressure_shield", "max_pressure_upstream_shield"]
    for scenario in load_split("train"):
        for fault in VALIDATION_FAULTS:
            for label in labels:
                budget.check("spatial_smoke_evaluation")
                if label == "max_pressure_shield":
                    controller = ShieldedController(get_controller("max_pressure"))
                elif label == "max_pressure_upstream_shield":
                    controller = ShieldedController(UpstreamMaxPressureController())
                else:
                    checkpoint = parent_path if label == "parent" else paths[label]
                    controller = get_controller("flowsync_uq", checkpoint_path=str(checkpoint), enable_fallback=False)
                result = runner.run(controller, scenario, EVALUATION_SEED, record_trajectory=False,
                    spatial_observation=True, fault_injector=PerceptionFaultInjector(fault, EVALUATION_SEED + 90000))
                cells.append(dict(label=label, scenario=scenario.scenario_id, fault=fault.name, seed=EVALUATION_SEED,
                    avg_delay=result.avg_delay, p95_delay=result.p95_delay, throughput=result.total_vehicles_passed,
                    arrival_hash=result.arrival_trace_hash, checkpoint_hash=result.checkpoint_hash,
                    signal_samples=result.safety_samples, signal_violations=result.executed_conflict_violations + result.executed_clearance_violations,
                    sensor_model=result.scenario_diagnostics["sensor_model"], fault_diagnostics=result.fault_diagnostics))
                stream.write(json.dumps(cells[-1], allow_nan=False) + "\n")
                stream.flush()
    for scenario in load_split("train"):
        for fault in VALIDATION_FAULTS:
            rows = {r["label"]: r for r in cells if r["scenario"] == scenario.scenario_id and r["fault"] == fault.name}
            if len({r["arrival_hash"] for r in rows.values()}) != 1:
                raise ValueError("Unpaired arrivals in smoke")
            for label in ("control_initial", "spatial_initial"):
                for key in ("avg_delay", "p95_delay", "throughput", "signal_samples", "signal_violations"):
                    if rows[label][key] != rows["parent"][key]:
                        raise ValueError("Zero-expanded initial policy differs from parent")
    return cells


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("parents", type=Path, help="Frozen batch manifest containing parent 101")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-wall-seconds", type=float, default=300.)
    args = p.parse_args()
    if not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0:
        raise ValueError("Smoke requires a positive bounded budget")
    budget = RunBudget(args.max_wall_seconds)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    parent_meta = json.loads(args.parents.read_text())["parents"]["101"]
    if file_hash(parent_meta["path"]) != parent_meta["sha256"]:
        raise ValueError("Parent checkpoint changed")
    parent = torch.load(parent_meta["path"], map_location="cpu", weights_only=True)
    parent["audit_parent_sha256"] = parent_meta["sha256"]
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [f for base in (ROOT / "research", ROOT / "server/app") for f in sorted(base.rglob("*.py"))] + [PROTOCOL]
    hashes = {str(f.relative_to(ROOT)): file_hash(f) for f in sources}
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path, str(path.relative_to(ROOT)))
    demos, online = schedule()
    inputs = {str(args.parents.resolve()): file_hash(args.parents), parent_meta["path"]: parent_meta["sha256"]}
    write(args.output / "manifest.json", dict(parent=parent_meta, seed=SEED, evaluation_seed=EVALUATION_SEED,
        arms=ARMS, source_hashes=hashes, input_hashes=inputs, observation_schema=SPATIAL_SCHEMA,
        budget_seconds=args.max_wall_seconds, training_only=True, protocol_sha256=file_hash(PROTOCOL),
        schedule=[dict(scenario=s.to_dict(), seed=seed, fault=f.to_dict()) for s, seed, f in [*demos, online]]))
    paths, metrics, cells, stop = {}, {}, [], None
    try:
        for arm, version in ARMS.items():
            arm_paths, metrics[arm] = train_arm(parent, version, args.output / arm, budget, demos, online)
            paths.update({f"{arm}_{stage}": path for stage, path in arm_paths.items()})
            print(f"{arm}: {metrics[arm]}", flush=True)
        with (args.output / "evaluation.jsonl").open("x") as stream:
            evaluate(paths, parent_meta["path"], budget, cells, stream)
    except BudgetExceeded as exc:
        stop = str(exc)
    write(args.output / "evaluation.json", cells)
    if any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Input changed during smoke")
    counts = {label: [r for r in cells if r["label"] == label] for label in sorted({r["label"] for r in cells})}
    result = dict(complete=stop is None and len(cells) == 84 and len(metrics) == 2, stop_reason=stop,
        mechanics_only=True, model_promoted=False, publication_ready=False, validation_access=False, final_test_access=False,
        metrics=metrics, evaluation_sources=len(cells), elapsed_seconds=budget.elapsed,
        evaluation_means={label: {k: float(np.mean([r[k] for r in rows])) for k in ("avg_delay", "p95_delay", "throughput")} for label, rows in counts.items()},
        signal_samples=sum(r["signal_samples"] for r in cells), signal_violations=sum(r["signal_violations"] for r in cells),
        output_hashes={str(f.relative_to(args.output)): file_hash(f) for f in args.output.rglob("*") if f.is_file()})
    write(args.output / "report.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
