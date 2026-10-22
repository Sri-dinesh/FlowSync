#!/usr/bin/env python3
"""Training-only fixed-state diagnostic of action-label sensitivity to future arrivals."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audit_control_interventions import fork_state, rollout_branch
from research.audit_policy_decisions import alternative_branch, audit_run
from research.calibrate_action_rank import choose, read_role
from research.collect_action_rank_dataset import HORIZON, PARENTS
from research.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, file_hash, load_split

PROTOCOL = ROOT / "research/docs/protocols/ARRIVAL_LABEL_PROTOCOL_20261020.md"
REPLICATES = 8
SOURCE_SEED = 95001


def future_seed(parent, scenario, source_seed, step, replicate):
    key = ["arrival-label-v1", parent, scenario, source_seed, step, replicate]
    return int.from_bytes(hashlib.sha256(json.dumps(key).encode()).digest()[:8], "big")


def replace_future_rng(state, seed):
    """Research-only mutation of an already copied state; preserve demand backlog."""
    state[0].intersection.spawner._rng = np.random.default_rng(seed)


def resample_branches(parent, env, sensor, injector, controller, context,
                     scenario, step, horizon, original_action, budget=None, *, replicate_indices=None,
                     source_seed=SOURCE_SEED):
    indices = tuple(range(REPLICATES) if replicate_indices is None else replicate_indices)
    if (len(indices) != REPLICATES or len(set(indices)) != REPLICATES or
            any(type(i) is not int or i < 0 for i in indices)):
        raise ValueError("Expected eight distinct nonnegative future indices")
    if type(source_seed) is not int or source_seed < 0:
        raise ValueError("Expected nonnegative source seed")
    proposal = controller.d3qn.get_diagnostics()["selected_action"]
    original_rng = copy.deepcopy(env.intersection.spawner._rng.bit_generator.state)
    result = []
    for replicate in indices:
        seed = future_seed(parent, scenario.scenario_id, source_seed, step, replicate)
        branches = []
        for candidate, valid in enumerate(context.valid_action_mask):
            if not valid:
                continue
            if budget:
                budget.check("arrival_label_branch")
            state = fork_state(env, sensor, injector, controller)
            replace_future_rng(state, seed)
            first_action = original_action
            if candidate != proposal:
                state, first_action = alternative_branch(state, candidate, context)
            outcome = rollout_branch(state, scenario, step, horizon, first_action)
            if outcome["signal_samples"] != horizon or outcome["signal_violations"]:
                raise ValueError("Incomplete/unsafe arrival branch")
            branches.append(dict(proposal=candidate, first_execution=first_action, outcome=outcome))
        if len({b["outcome"]["arrival_trace_hash"] for b in branches}) != 1:
            raise ValueError("Unpaired future arrivals")
        result.append(dict(replicate=replicate, arrival_seed=seed, branches=branches))
    if env.intersection.spawner._rng.bit_generator.state != original_rng:
        raise ValueError("Resampling mutated source RNG")
    return result


def gains(branches, parent):
    by_action = {b["proposal"]: b["outcome"] for b in branches}
    if len(by_action) != len(branches) or parent not in by_action:
        raise ValueError("Missing parent or duplicate branch")
    base = by_action[parent]
    return {a: [base["incremental_delay_vehicle_seconds"] - out["incremental_delay_vehicle_seconds"],
                out["vehicles_passed"] - base["vehicles_passed"],
                base["upstream_max_wait_s"] - out["upstream_max_wait_s"]]
            for a, out in by_action.items() if a != parent}


def qualified(gain):
    return bool(gain[0] > 1. and gain[1] >= 0. and gain[2] >= -1.)


def harmful(gain):
    return bool(gain[0] < -1. or gain[1] < 0. or gain[2] < -1.)


def summarize_event(event):
    parent = event["policy_proposal"]
    original = gains(event["all_action_branches"], parent)
    futures = event["branch_diagnostic"]
    if len(futures) != REPLICATES or {f["replicate"] for f in futures} != set(range(REPLICATES)):
        raise ValueError("Incomplete/duplicate future replicates")
    samples = [gains(f["branches"], parent) for f in futures]
    if any(set(g) != set(original) for g in samples):
        raise ValueError("Changed candidate coverage")
    alternatives, means = [], {}
    for action in sorted(original):
        values = np.array([g[action] for g in samples], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite gains")
        means[action] = values.mean(0).tolist()
        alternatives.append(dict(action=action, original_gain=original[action],
                                 mean_gain=means[action], sample_sd=values.std(0, ddof=1).tolist(),
                                 delay_sign_flip=bool((values[:, 0] > 1.).any() and (values[:, 0] < -1.).any()),
                                 qualified_futures=sum(qualified(v) for v in values),
                                 harmful_futures=sum(harmful(v) for v in values)))
    original_choice = choose(original, parent)
    chosen = next((a for a in alternatives if a["action"] == original_choice), None)
    return dict(step=event["step"], parent=parent, alternatives=alternatives,
                original_choice=original_choice, original_qualified_change=original_choice != parent,
                original_choice_qualified_futures=chosen["qualified_futures"] if chosen else 0,
                original_choice_harmful_futures=chosen["harmful_futures"] if chosen else 0,
                future_choices=[choose(g, parent) for g in samples], mean_choice=choose(means, parent),
                distinct_arrival_traces=len({f["branches"][0]["outcome"]["arrival_trace_hash"] for f in futures}))


def summarize(rows, planned, smoke, stop_reason):
    events, samples = [], 0
    for row in rows:
        samples += row["signal_samples"]
        for event in row["events"]:
            if "branch_diagnostic" not in event:
                continue
            item = summarize_event(event)
            item.update(training_seed=row["training_seed"], scenario=row["scenario"], source_seed=row["seed"])
            events.append(item)
            branches = event["all_action_branches"] + [
                b for future in event["branch_diagnostic"] for b in future["branches"]]
            for b in branches:
                out = b["outcome"]
                if out["signal_samples"] != HORIZON or out["signal_violations"]:
                    raise ValueError("Incomplete/unsafe signals")
                samples += out["signal_samples"]
        if row["signal_samples"] != 1200 or row["signal_violations"]:
            raise ValueError("Incomplete/unsafe source")
    alts = [a for e in events for a in e["alternatives"]]
    chosen = [e for e in events if e["original_qualified_change"]]
    report = dict(
        complete=len(rows) == planned, full_panel_complete=len(rows) == planned and not smoke,
        smoke=smoke, completed_sources=len(rows), planned_sources=planned, gates=len(events),
        alternatives=len(alts), future_replicates=REPLICATES,
        alternatives_with_delay_sign_flip=sum(a["delay_sign_flip"] for a in alts),
        original_qualified_choice_gates=len(chosen),
        original_choices_qualified_future_cases=sum(e["original_choice_qualified_futures"] for e in chosen),
        original_choices_harmful_future_cases=sum(e["original_choice_harmful_futures"] for e in chosen),
        original_choice_future_cases=len(chosen) * REPLICATES,
        original_choices_qualified_in_at_least_six_futures=sum(e["original_choice_qualified_futures"] >= 6 for e in chosen),
        gates_with_different_future_choices=sum(len(set(e["future_choices"])) > 1 for e in events),
        source_and_branch_signal_samples=samples, signal_violations=0,
        stop_reason=stop_reason, calibration_access=False, probe_access=False,
        validation_access=False, final_test_access=False, model_trained=False, publication_ready=False)
    return report, events


def verify_original(record, old):
    cleaned = {k: v for k, v in record.items() if k not in ("data_role", "training_seed", "selected_steps")}
    cleaned["events"] = [{k: v for k, v in e.items() if k != "branch_diagnostic"} for e in record["events"]]
    expected = {k: v for k, v in old.items() if k not in ("data_role", "training_seed", "selected_steps")}
    # JSON makes integer phase-timer keys strings. Compare the same serialized
    # representation, without rounding floats or omitting any outcome fields.
    if json.loads(json.dumps(cleaned, allow_nan=False)) != json.loads(json.dumps(expected, allow_nan=False)):
        raise ValueError("Original trajectory or branch labels changed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-wall-seconds", type=float, default=300.)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    if not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0:
        raise ValueError("A finite positive budget is required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    collection = json.loads((args.dataset / "report.json").read_text())
    if not collection["full_dataset_complete"] or file_hash(args.dataset / "fit.jsonl") != collection["output_hashes"]["fit.jsonl"]:
        raise ValueError("Incomplete or changed fitting data")
    for name, digest in manifest["input_hashes"].items():
        if file_hash(name) != digest:
            raise ValueError("Collection input changed")
    with zipfile.ZipFile(args.dataset / "source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(n)).hexdigest() != h for n, h in manifest["source_hashes"].items()):
            raise ValueError("Collection archive mismatch")
    fit = read_role(args.dataset, "fit", manifest)
    cases = sorted((r for r in fit if r["seed"] == SOURCE_SEED and r["fault"]["name"] == VALIDATION_FAULTS[0].name),
                   key=lambda r: (r["training_seed"], r["scenario"]))
    scenarios = {s.scenario_id: s for s in load_split("train")}
    expected = {(p, s) for p in PARENTS for s in scenarios}
    if len(cases) != 18 or {(r["training_seed"], r["scenario"]) for r in cases} != expected:
        raise ValueError("Wrong diagnostic source panel")
    if args.smoke:
        cases = cases[:1]
    sources = [p for folder in (ROOT / "research", ROOT / "server/app") for p in sorted(folder.rglob("*.py"))]
    sources += [PROTOCOL] + sorted((ROOT / "research/scenarios/train").glob("*.yaml"))
    inputs = {str((args.dataset / name).resolve()): file_hash(args.dataset / name)
              for name in ("fit.jsonl", "manifest.json", "report.json", "source_snapshot.zip")}
    inputs.update(manifest["input_hashes"])
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in sources}
    args.output.mkdir(parents=True)
    print(f"Output: {args.output.resolve()}; planned sources: {len(cases)}", flush=True)
    run_manifest = dict(parents=manifest["parents"], input_hashes=inputs, source_hashes=hashes,
                        protocol=str(PROTOCOL.relative_to(ROOT)), planned_sources=len(cases),
                        replicates=REPLICATES, horizon=HORIZON, smoke=args.smoke,
                        max_wall_seconds=args.max_wall_seconds,
                        cells=[dict(parent=r["training_seed"], scenario=r["scenario"],
                                    seed=r["seed"], steps=r["selected_steps"]) for r in cases])
    (args.output / "manifest.json").write_text(json.dumps(run_manifest, indent=2))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path, str(path.relative_to(ROOT)))
    budget, rows, error = RunBudget(args.max_wall_seconds), [], None
    try:
        with (args.output / "runs.jsonl").open("x") as stream:
            for old in cases:
                budget.check("arrival_label_source")
                parent = old["training_seed"]
                scenario = scenarios[old["scenario"]]
                if scenario.compute_hash() != old["scenario_hash"]:
                    raise ValueError("Source scenario changed")
                def diagnostic(*arguments):
                    return resample_branches(parent, *arguments)
                record = audit_run(manifest["parents"][str(parent)]["path"], scenario,
                                   SOURCE_SEED, VALIDATION_FAULTS[0], HORIZON, 3, all_actions=True,
                                   budget=budget, branch_steps=old["selected_steps"], branch_diagnostic=diagnostic)
                record.update(training_seed=parent, data_role="fit", selected_steps=old["selected_steps"])
                verify_original(record, old)
                rows.append(record)
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                stream.flush()
                print(f"[{len(rows)}/{len(cases)}] parent {parent}, {scenario.scenario_id}; {budget.elapsed:.1f}s", flush=True)
    except BudgetExceeded as exc:
        error = str(exc)
    if any(file_hash(name) != digest for name, digest in inputs.items()):
        raise ValueError("Diagnostic input changed")
    if any(file_hash(ROOT / name) != digest for name, digest in hashes.items()):
        raise ValueError("Diagnostic source changed")
    report, events = summarize(rows, len(cases), args.smoke, error)
    (args.output / "events.json").write_text(json.dumps(events, indent=2, allow_nan=False))
    report.update(elapsed_seconds=budget.elapsed, output_hashes={
        name: file_hash(args.output / name) for name in ("runs.jsonl", "events.json")})
    (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
