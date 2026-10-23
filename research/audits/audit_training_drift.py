#!/usr/bin/env python3
"""Training-only paired checkpoint diagnosis; never invokes an optimizer."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.pilots.compare_temporal_pilot import ARMS, SEEDS, compare
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.observations import encode_policy_observation

EPISODES = (1, 16, 31, 46, 61, 76)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    lookup = {r["episode"]: r for r in rows}
    if len(lookup) != len(rows) or not set(EPISODES) <= set(lookup):
        raise ValueError("Missing/duplicate recorded training episodes")
    cases = []
    for episode in EPISODES:
        row = lookup[episode]
        scenario = ScenarioConfig.from_dict(row["executed_scenario"])
        if scenario.split != "train":
            raise ValueError("Drift diagnosis may only replay training scenarios")
        cases.append(dict(episode=episode, scenario=scenario.to_dict(),
                          traffic_seed=row["seed"], fault=row["fault"]))
    return cases


def score_actions(network, observation, mask):
    if not np.asarray(mask).any():
        raise ValueError("Probe requires at least one valid action")
    with torch.no_grad():
        q = network(torch.as_tensor(observation, dtype=torch.float32).unsqueeze(0),
                    valid_action_mask=torch.as_tensor(mask, dtype=torch.bool).unsqueeze(0))[0].numpy()
    if not np.isfinite(q).all():
        raise ValueError("Non-finite probe Q values")
    valid = np.flatnonzero(mask)
    ranked = sorted(valid, key=lambda a: (-float(q[a]), int(a)))
    return dict(action=int(ranked[0]), q_values=q.tolist(),
                margin=float(q[ranked[0]]-q[ranked[1]]) if len(ranked) > 1 else None)


class ProbedPolicy(FlowSyncUQController):
    """Probe shadow networks without advancing their hold/action state."""

    def __init__(self, checkpoints, acting):
        super().__init__(checkpoint_path=str(checkpoints[acting]), enable_shield=True, enable_fallback=False)
        self.probes = {name: D3QNController(checkpoint_path=str(path)) for name, path in checkpoints.items()}
        if len({c.agent.obs_version for c in self.probes.values()}) != 1:
            raise ValueError("Initial/final observation versions differ")
        self.decision_probes = []

    def reset(self, seed=None):
        super().reset(seed)
        self.decision_probes = []

    def act(self, observation, context):
        if context.is_decision_step and context.timestep >= self.d3qn._next_decision_step:
            encoded = encode_policy_observation(observation, context, self.d3qn.agent.obs_version)
            self.decision_probes.append(dict(step=context.timestep, mask=context.valid_action_mask.tolist(),
                observation=encoded.tolist(), **{name: score_actions(c.agent.online_net, encoded, context.valid_action_mask)
                                                for name, c in self.probes.items()}))
        return super().act(observation, context)


def summarize(rows):
    lookup = {(r["arm"], r["training_seed"], r["episode"], r["acting"]): r for r in rows}
    expected = {(arm, seed, episode, acting) for arm in ARMS for seed in SEEDS
                for episode in EPISODES for acting in ("initial", "final")}
    if len(lookup) != len(rows) or set(lookup) != expected:
        raise ValueError("Incomplete/duplicate diagnostic cells")
    pairs = []
    for arm in ARMS:
        for seed in SEEDS:
            for episode in EPISODES:
                initial, final = (lookup[(arm, seed, episode, stage)]["result"] for stage in ("initial", "final"))
                if not initial["arrival_trace_hash"] or initial["arrival_trace_hash"] != final["arrival_trace_hash"]:
                    raise ValueError("Unpaired diagnostic arrivals")
                pairs.append(dict(arm=arm, training_seed=seed, episode=episode,
                    delay_saved=initial["avg_delay"]-final["avg_delay"],
                    reward_gained=final["total_reward"]-initial["total_reward"],
                    initial_delay=initial["avg_delay"], final_delay=final["avg_delay"],
                    p95_saved=initial["p95_delay"]-final["p95_delay"],
                    throughput_gained=final["total_vehicles_passed"]-initial["total_vehicles_passed"]))
    for r in rows:
        data = r["result"]
        if data["safety_samples"] != data["num_steps"] or data["safety_samples"] <= 0:
            raise ValueError("Incomplete signal audit")
        if not np.isfinite([data[k] for k in ("avg_delay", "p95_delay", "total_reward", "total_vehicles_passed")]).all():
            raise ValueError("Non-finite metrics")
    by_group = []
    for arm in ARMS:
        for seed in (*SEEDS, "all"):
            ps = [p for p in pairs if p["arm"] == arm and (seed == "all" or p["training_seed"] == seed)]
            by_group.append(dict(arm=arm, training_seed=seed, pairs=len(ps),
                **{k: statistics.mean(p[k] for p in ps) for k in
                   ("initial_delay", "final_delay", "delay_saved", "reward_gained", "p95_saved", "throughput_gained")},
                improved=sum(p["delay_saved"] > .001 for p in ps),
                worsened=sum(p["delay_saved"] < -.001 for p in ps),
                reward_delay_direction_disagreements=sum(p["delay_saved"]*p["reward_gained"] < 0 for p in ps)))
    probes = []
    for arm in ARMS:
        for acting in ("initial", "final"):
            events = [e for r in rows if r["arm"] == arm and r["acting"] == acting for e in r["probes"]]
            probes.append(dict(arm=arm, state_distribution=acting, decision_gates=len(events),
                changed_actions=sum(e["initial"]["action"] != e["final"]["action"] for e in events),
                **{f"{stage}_selected_q_mean": statistics.mean(e[stage]["q_values"][e[stage]["action"]] for e in events)
                   for stage in ("initial", "final")}))
    return dict(runs=len(rows), paired_runs=len(pairs), by_group=by_group, probes=probes, pairs=pairs,
        signal_samples=sum(r["result"]["safety_samples"] for r in rows),
        signal_violations=sum(r["result"]["executed_conflict_violations"]+r["result"]["executed_clearance_violations"] for r in rows),
        scope="Seen training traffic, deterministic shielded inference; diagnostic only, no significance claim",
        publication_ready=False, checkpoints_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.output.exists():
        raise FileExistsError("Choose a new diagnostic output directory")
    comparison = compare(args.batch)
    if comparison != json.loads((args.batch/"comparison.json").read_text()):
        raise ValueError("Original pilot comparison does not reproduce")
    cases, checkpoints, hashes = {}, {}, {"comparison.json": sha(args.batch/"comparison.json")}
    for seed in SEEDS:
        for arm in ARMS:
            key = f"{arm}_seed_{seed}"
            directory = args.batch/key
            cases[key] = load_cases(directory/"training.jsonl")
            checkpoints[key] = {stage: directory/f"checkpoint_{label}.pt" for stage, label in (("initial", "initial"), ("final", "90"))}
            for path in (directory/"training.jsonl", *checkpoints[key].values()):
                hashes[str(path.relative_to(args.batch))] = sha(path)
        if cases[f"control_seed_{seed}"] != cases[f"temporal_seed_{seed}"]:
            raise ValueError("Recorded training cases differ across arms")
    sources = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    protocol = ROOT/"research/docs/protocols/TRAINING_DRIFT_PROTOCOL_20261016.md"
    sources.append(protocol)
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(batch=str(args.batch.resolve()), cases=cases, input_sha256=hashes, planned_runs=72,
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources})
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, str(path.relative_to(ROOT)))
    rows = []
    with (args.output/"runs.jsonl").open("x") as stream:
        for seed in SEEDS:
            for arm in ARMS:
                key = f"{arm}_seed_{seed}"
                for case in cases[key]:
                    scenario = ScenarioConfig.from_dict(case["scenario"])
                    for acting in ("initial", "final"):
                        ctrl = ProbedPolicy(checkpoints[key], acting)
                        result = ExperimentRunner().run(ctrl, scenario, case["traffic_seed"], record_trajectory=False,
                            fault_injector=PerceptionFaultInjector(FaultProfile(**case["fault"]), seed=case["traffic_seed"]+90000))
                        if result.checkpoint_hash != hashes[str(checkpoints[key][acting].relative_to(args.batch))]:
                            raise ValueError("Checkpoint changed during diagnosis")
                        row = dict(arm=arm, training_seed=seed, episode=case["episode"], acting=acting,
                                   result=result.to_dict(include_trajectory=False), probes=ctrl.decision_probes)
                        rows.append(row)
                        stream.write(json.dumps(row, allow_nan=False)+"\n")
                        stream.flush()
                    print(f"Training drift audit: {len(rows)}/72", flush=True)
    report = summarize(rows)
    (args.output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: v for k, v in report.items() if k != "pairs"}, indent=2))


if __name__ == "__main__":
    main()
