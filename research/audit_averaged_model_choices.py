#!/usr/bin/env python3
"""Verify a completed model pilot and diagnose fixed-threshold abstention; never tune."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audit_arrival_label_stability import gains, verify_original
from research.audit_policy_decisions import audit_run
from research.averaged_label_model import (
    cells, configuration, fit_models, predict_source, prediction_errors, selected_steps, summarize,
)
from research.evaluate_averaged_action_labels import score_source, validate_futures, without_diagnostic, write
from research.run_averaged_label_model_pilot import signal_samples
from research.train_policy import VALIDATION_FAULTS, file_hash, load_split

CONSTRAINTS = ("delay", "throughput", "endpoint_wait")


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def flags(values):
    if len(values) != 3 or not np.isfinite(values).all():
        raise ValueError("Invalid gain vector")
    return dict(zip(CONSTRAINTS, (bool(values[0] > 1.), bool(values[1] >= 0.), bool(values[2] >= -1.))))


def diagnose(rows, models):
    """Descriptive error analysis only; no feature, threshold or model selection."""
    counters, details = {}, []
    for row in rows:
        parent = row["training_seed"]
        choices = {c["step"]: c for c in predict_source(row, row["selected_steps"], models)}
        for event in row["events"]:
            if event["step"] not in choices:
                continue
            outcomes = [gains(f["branches"], event["policy_proposal"]) for f in event["branch_diagnostic"]]
            actual = {a: np.mean([g[a] for g in outcomes], axis=0).tolist() for a in outcomes[0]}
            for arm in ("single", "mean8"):
                keys = (arm, f"{parent}/{arm}")
                for key in keys:
                    c = counters.setdefault(key, Counter())
                    c["gates"] += 1
                    c["changed_gates"] += choices[event["step"]][arm] != event["policy_proposal"]
                    c["gates_with_actual_mean_qualified_alternative"] += any(all(flags(v).values()) for v in actual.values())
                for action, predicted in choices[event["step"]]["predictions"][arm].items():
                    truth = actual[action]
                    good, predicted_good = flags(truth), flags(predicted)
                    qualifies, estimated = all(good.values()), all(predicted_good.values())
                    for key in keys:
                        c = counters[key]
                        c["alternatives"] += 1
                        c["actual_mean_qualified"] += qualifies
                        c["predicted_qualified"] += estimated
                        c["true_positive"] += qualifies and estimated
                        c["false_positive"] += estimated and not qualifies
                        c["false_negative"] += qualifies and not estimated
                        c["true_negative"] += not qualifies and not estimated
                        for name in CONSTRAINTS:
                            c[f"predicted_{name}_pass"] += predicted_good[name]
                            c[f"actual_{name}_pass"] += good[name]
                            c[f"missed_qualified_rejected_by_{name}"] += qualifies and not predicted_good[name]
                        c["predicted_delay_and_throughput_pass"] += predicted_good["delay"] and predicted_good["throughput"]
                        c["predicted_delay_pass_but_throughput_reject"] += predicted_good["delay"] and not predicted_good["throughput"]
                    details.append(dict(role=row["data_role"], training_seed=parent, scenario=row["scenario"],
                        seed=row["seed"], step=event["step"], arm=arm, action=action,
                        predicted=predicted, actual_mean=truth, predicted_constraints=predicted_good,
                        actual_constraints=good, predicted_qualified=estimated, actual_mean_qualified=qualifies))
    return {k: dict(v) for k, v in counters.items()}, details


def verify_pilot(path):
    manifest, report = read(path / "manifest.json"), read(path / "report.json")
    if not report["full_pilot_complete"] or report["smoke"]:
        raise ValueError("Complete non-smoke model pilot required")
    config = configuration(False)
    if manifest["config"] != json.loads(json.dumps(config)):
        raise ValueError("Pilot configuration changed")
    inputs = {str(p.resolve()): file_hash(p) for p in path.iterdir() if p.is_file()}
    for name, digest in manifest["input_hashes"].items():
        if file_hash(name) != digest:
            raise ValueError("Upstream input changed")
    for name, digest in report["output_hashes"].items():
        if file_hash(path / name) != digest:
            raise ValueError("Pilot output changed")
    with zipfile.ZipFile(path / "source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(n)).hexdigest() != h for n, h in manifest["source_hashes"].items()):
            raise ValueError("Source archive mismatch")
    for name in ("research/averaged_label_model.py", "research/action_rank_policy.py",
                 "research/evaluate_averaged_action_labels.py", "research/calibrate_action_rank.py"):
        if file_hash(ROOT / name) != manifest["source_hashes"][name]:
            raise ValueError("Live scoring/fitting implementation differs from archived pilot")
    scenarios = {s.scenario_id: s for s in load_split("train")}
    if manifest["scenarios"] != {n: s.to_dict() for n, s in scenarios.items()}:
        raise ValueError("Scenario configuration changed")
    roles = {role: lines(path / f"{role}.jsonl") for role in ("fit", "probe")}
    samples = 0
    for role, rows in roles.items():
        keys = [(r["training_seed"], r["scenario"], r["seed"]) for r in rows]
        if len(keys) != len(set(keys)) or set(keys) != set(cells(config, scenarios, role)):
            raise ValueError("Incomplete/duplicate role cells")
        for row in rows:
            if (row["data_role"] != role or row["split"] != "train" or row["fault"] != VALIDATION_FAULTS[0].to_dict()
                    or row["checkpoint_hash"] != manifest["parents"][str(row["training_seed"])]["sha256"]
                    or row["scenario_hash"] != scenarios[row["scenario"]].compute_hash()
                    or row["signal_samples"] != 1200 or row["signal_violations"]):
                raise ValueError("Incorrect role/parent/scenario or unsafe source")
            events = [e for e in row["events"] if "branch_diagnostic" in e]
            if [e["step"] for e in events] != row["selected_steps"] or selected_steps(row, row["training_seed"]) != row["selected_steps"]:
                raise ValueError("Incorrect selected gates")
            for event in events:
                validate_futures(row, event, config[f"{role}_ids"])
            samples += signal_samples(row)
    for item in manifest["parents"].values():
        if file_hash(item["path"]) != item["sha256"]:
            raise ValueError("Parent checkpoint changed")
    models = fit_models(roles["fit"], config, scenarios, manifest["parents"])
    frozen = read(path / "frozen_models.json")
    for (parent, arm), model in models.items():
        name = f"model_{parent}_{arm}.json"
        if file_hash(path / name) != frozen[name] or model != read(path / name):
            raise ValueError("Frozen model does not exactly refit")
    predictions = lines(path / "predictions_before_outcomes.jsonl")
    scores, decisions = [], []
    for row, choices in zip(roles["probe"], predictions, strict=True):
        reproduced = predict_source(row, row["selected_steps"], models)
        if json.loads(json.dumps(reproduced)) != choices:
            raise ValueError("Persisted pre-outcome prediction mismatch")
        score, records = score_source(row, choices, config["probe_ids"], expected_gates=2)
        score["prediction_mae"] = prediction_errors(row, choices)
        scores.append(score)
        decisions.extend(records)
    if scores != read(path / "source_scores.json") or decisions != lines(path / "decisions.jsonl"):
        raise ValueError("Probe score mismatch")
    expected = summarize(scores, config, scenarios, len(roles["fit"]), len(models))
    if any(report[k] != v for k, v in expected.items()) or report["source_and_branch_signal_samples"] != samples:
        raise ValueError("Report mismatch")
    return manifest, report, roles, models, inputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pilot", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--replay", action="store_true", help="Independently replay first source per parent and role")
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh audit directory")
    torch.set_num_threads(1)
    manifest, pilot_report, roles, models, inputs = verify_pilot(args.pilot)
    replayed = []
    if args.replay:
        scenarios = {s.scenario_id: s for s in load_split("train")}
        for role, rows in roles.items():
            for parent in configuration(False)["parents"]:
                row = min((r for r in rows if r["training_seed"] == parent), key=lambda r: (r["seed"], r["scenario"]))
                reference = audit_run(manifest["parents"][str(parent)]["path"], scenarios[row["scenario"]],
                    row["seed"], VALIDATION_FAULTS[0], 400, 2, all_actions=True, branch_steps=row["selected_steps"])
                verify_original(row, reference)
                replayed.append(dict(role=role, parent=parent, scenario=row["scenario"], seed=row["seed"]))
                print(f"Verified original source/branch replay: {replayed[-1]}", flush=True)
    summaries, details = {}, []
    for role, rows in roles.items():
        summaries[role], records = diagnose(rows, models)
        details.extend(records)
    if any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Pilot changed during audit")
    args.output.mkdir(parents=True)
    write(args.output / "manifest.json", dict(input_hashes=inputs, audit_source_sha256=file_hash(__file__)))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(__file__, str(Path(__file__).relative_to(ROOT)))
    with (args.output / "alternatives.jsonl").open("x") as stream:
        for row in details:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    result = dict(verified=True, pilot_continue_to_full_rollout=pilot_report["continue_to_full_rollout_pilot"],
                  diagnostics=summaries, replayed_sources=replayed, all_sources_replayed=False,
                  verification_refits=6, models_modified=False, thresholds_changed=False,
                  publication_ready=False, final_test_access=False,
                  alternatives_sha256=file_hash(args.output / "alternatives.jsonl"),
                  scope="Descriptive diagnosis of already observed fit/probe outcomes, not new model selection")
    write(args.output / "report.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "diagnostics"}, indent=2))
    print(json.dumps({r: {a: s[a] for a in ("single", "mean8")} for r, s in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
