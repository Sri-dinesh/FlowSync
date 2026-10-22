#!/usr/bin/env python3
"""Collect averaged training labels, freeze models, then score excluded-source probes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audit_arrival_label_stability import resample_branches
from research.audit_policy_decisions import audit_run
from research.averaged_label_model import (
    cells, configuration, fit_models, predict_source, prediction_errors, selected_steps, summarize,
)
from research.collect_action_rank_dataset import verify_replay
from research.evaluate_averaged_action_labels import (
    score_source, summarize as evidence_summary, validate_futures, without_diagnostic, write,
)
from research.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, file_hash, load_split

PROTOCOL = ROOT / "research/docs/protocols/AVERAGED_LABEL_MODEL_PROTOCOL_20261021.md"


def load_evidence(path):
    manifest = json.loads((path / "manifest.json").read_text())
    report = json.loads((path / "report.json").read_text())
    if not report["full_panel_complete"] or not report["continue_to_label_model_pilot"] or report["smoke"]:
        raise ValueError("Complete passed averaged-label evidence is required")
    inputs = {str((path / name).resolve()): file_hash(path / name) for name in
              ("manifest.json", "report.json", "source_snapshot.zip", "runs.jsonl",
               "source_scores.json", "decisions.jsonl", "frozen_choices.json")}
    inputs.update(manifest["input_hashes"])
    if any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Evidence input changed")
    if any(file_hash(path / n) != h for n, h in report["output_hashes"].items()):
        raise ValueError("Evidence output changed")
    with zipfile.ZipFile(path / "source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(n)).hexdigest() != h for n, h in manifest["source_hashes"].items()):
            raise ValueError("Evidence archive mismatch")
    reproduced = evidence_summary(json.loads((path / "source_scores.json").read_text()), 18, False)
    if any(report[k] != v for k, v in reproduced.items()):
        raise ValueError("Evidence summary does not reproduce")
    if file_hash(path / "frozen_choices.json") != manifest["frozen_choices_sha256"]:
        raise ValueError("Evidence choices changed")
    for item in manifest["parents"].values():
        if file_hash(item["path"]) != item["sha256"]:
            raise ValueError("Parent checkpoint changed")
        inputs[str(Path(item["path"]).resolve())] = item["sha256"]
    return manifest["parents"], inputs


def collect_source(parent, scenario, seed, checkpoint, role, indices, budget, models=None, prediction_stream=None):
    budget.check(f"{role}_prescan")
    source = audit_run(checkpoint, scenario, seed, VALIDATION_FAULTS[0], 400, 0,
                       all_actions=True, budget=budget)
    steps = selected_steps(source, parent)
    choices = None
    if role == "probe":
        if not models or prediction_stream is None:
            raise ValueError("Probe requires frozen models and prediction recording")
        choices = predict_source(dict(source, training_seed=parent), steps, models)
        # Persist before collecting ANY action outcome for this probe source.
        prediction_stream.write(json.dumps(choices, allow_nan=False) + "\n")
        prediction_stream.flush()
    elif role != "fit" or models is not None:
        raise ValueError("Invalid collection role")
    def diagnostic(*arguments):
        return resample_branches(parent, *arguments, replicate_indices=indices, source_seed=seed)
    record = audit_run(checkpoint, scenario, seed, VALIDATION_FAULTS[0], 400, 2,
                       all_actions=True, budget=budget, branch_steps=steps, branch_diagnostic=diagnostic)
    verify_replay(source, without_diagnostic(record), steps)
    record.update(training_seed=parent, data_role=role, selected_steps=steps)
    for event in record["events"]:
        if "branch_diagnostic" in event:
            validate_futures(record, event, indices)
    return record, choices


def signal_samples(row):
    return row["signal_samples"] + sum(
        b["outcome"]["signal_samples"] for e in row["events"] if "branch_diagnostic" in e
        for branches in [e["all_action_branches"]] + [f["branches"] for f in e["branch_diagnostic"]]
        for b in branches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--max-wall-seconds", type=float, default=5400.)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    if not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0:
        raise ValueError("A finite positive budget is required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    parents, inputs = load_evidence(args.evidence)
    config = configuration(args.smoke)
    scenarios = {s.scenario_id: s for s in load_split("train")}
    if len(scenarios) != 6 or any(s.duration_steps != 1200 for s in scenarios.values()):
        raise ValueError("Expected six 1200-tick training templates")
    if args.smoke:
        scenarios = {"train_ew_asymmetric_01": scenarios["train_ew_asymmetric_01"]}
    plan = {role: cells(config, scenarios, role) for role in ("fit", "probe")}
    sources = [p for folder in (ROOT / "research", ROOT / "server/app") for p in sorted(folder.rglob("*.py"))]
    sources += [PROTOCOL] + sorted((ROOT / "research/scenarios/train").glob("*.yaml"))
    hashes = {str(p.relative_to(ROOT)): file_hash(p) for p in sources}
    args.output.mkdir(parents=True)
    write(args.output / "manifest.json", dict(config=config, input_hashes=inputs, source_hashes=hashes,
          parents=parents, plan=plan, max_wall_seconds=args.max_wall_seconds,
          scenarios={n: s.to_dict() for n, s in scenarios.items()}, models_frozen_before_probe=True))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sources:
            z.write(p, str(p.relative_to(ROOT)))
    print(f"Output: {args.output.resolve()}; fit/probe sources: {len(plan['fit'])}/{len(plan['probe'])}", flush=True)
    budget = RunBudget(args.max_wall_seconds)
    fit_rows, scores, decisions, model_hashes = [], [], [], {}
    models, error, samples = {}, None, 0
    try:
        with (args.output / "fit.jsonl").open("x") as stream:
            for parent, name, seed in plan["fit"]:
                row, _ = collect_source(parent, scenarios[name], seed, parents[str(parent)]["path"],
                                        "fit", config["fit_ids"], budget)
                fit_rows.append(row)
                samples += signal_samples(row)
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                print(f"Fit [{len(fit_rows)}/{len(plan['fit'])}] parent {parent}, {name}, seed {seed}; {budget.elapsed:.1f}s", flush=True)
        budget.check("model_fitting")
        models = fit_models(fit_rows, config, scenarios, parents)
        for (parent, arm), model in models.items():
            path = args.output / f"model_{parent}_{arm}.json"
            write(path, model)
            model_hashes[path.name] = file_hash(path)
        write(args.output / "frozen_models.json", model_hashes)
        print(f"Frozen {len(models)} models before probe simulation", flush=True)
        with (args.output / "probe.jsonl").open("x") as stream, (args.output / "predictions_before_outcomes.jsonl").open("x") as predictions:
            for parent, name, seed in plan["probe"]:
                row, choices = collect_source(parent, scenarios[name], seed, parents[str(parent)]["path"],
                    "probe", config["probe_ids"], budget, models, predictions)
                source_score, records = score_source(row, choices, config["probe_ids"], expected_gates=2)
                source_score["prediction_mae"] = prediction_errors(row, choices)
                scores.append(source_score)
                decisions.extend(records)
                samples += signal_samples(row)
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                stream.flush()
                print(f"Probe [{len(scores)}/{len(plan['probe'])}] parent {parent}, {name}, seed {seed}; {budget.elapsed:.1f}s", flush=True)
    except BudgetExceeded as exc:
        error = str(exc)
    if any(file_hash(n) != h for n, h in inputs.items()) or any(file_hash(ROOT / n) != h for n, h in hashes.items()):
        raise ValueError("Inputs or sources changed during pilot")
    if any(file_hash(args.output / n) != h for n, h in model_hashes.items()):
        raise ValueError("Frozen model changed")
    write(args.output / "source_scores.json", scores)
    with (args.output / "decisions.jsonl").open("x") as stream:
        for row in decisions:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    report = summarize(scores, config, scenarios, len(fit_rows), len(models))
    report.update(stop_reason=error, elapsed_seconds=budget.elapsed,
                  source_and_branch_signal_samples=samples, signal_violations=0,
                  output_hashes={p.name: file_hash(p) for p in sorted(args.output.iterdir())
                                 if p.suffix in (".json", ".jsonl") and p.name != "manifest.json"})
    write(args.output / "report.json", report)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
