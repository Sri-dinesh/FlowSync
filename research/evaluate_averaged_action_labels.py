#!/usr/bin/env python3
"""Freeze single/mean-eight hindsight choices, then score on fresh training futures."""
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

from research.audit_arrival_label_stability import (
    SOURCE_SEED, future_seed, gains, harmful, qualified, resample_branches,
    summarize as summarize_panel, verify_original,
)
from research.audit_policy_decisions import audit_run
from research.calibrate_action_rank import choose
from research.collect_action_rank_dataset import HORIZON, PARENTS
from research.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, file_hash, load_split

PROTOCOL = ROOT / "research/docs/protocols/AVERAGED_LABEL_PROTOCOL_20261021.md"
FIT_IDS = tuple(range(8))
EVAL_IDS = tuple(range(8, 16))
SMOKE_IDS = tuple(range(100, 108))
ARMS = ("parent", "single", "mean8")


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def key(row, step):
    return row["training_seed"], row["scenario"], row["seed"], step


def validate_futures(row, event, indices):
    expected = {i for i, valid in enumerate(event["mask"]) if valid}
    original = event["all_action_branches"]
    first = {b["proposal"]: b["first_execution"] for b in original}
    if set(first) != expected or len(original) != len(first) or event["policy_proposal"] not in expected:
        raise ValueError("Invalid original action coverage")
    futures = event["branch_diagnostic"]
    if len(futures) != 8 or {f["replicate"] for f in futures} != set(indices):
        raise ValueError("Wrong future split or duplicate replicate")
    for f in futures:
        seed = future_seed(row["training_seed"], row["scenario"], row["seed"], event["step"], f["replicate"])
        if f["arrival_seed"] != seed:
            raise ValueError("Future seed mismatch")
    for branches in [original] + [f["branches"] for f in futures]:
        if len(branches) != len(first) or {b["proposal"]: b["first_execution"] for b in branches} != first:
            raise ValueError("Changed candidate coverage or first execution")
        traces = {b["outcome"]["arrival_trace_hash"] for b in branches}
        if len(traces) != 1 or not next(iter(traces)):
            raise ValueError("Unpaired arrivals")
        for b in branches:
            out = b["outcome"]
            values = [out[n] for n in ("incremental_delay_vehicle_seconds", "vehicles_passed", "upstream_max_wait_s")]
            if not np.isfinite(values).all() or min(values) < 0 or out["signal_samples"] != HORIZON or out["signal_violations"]:
                raise ValueError("Invalid branch measurements")


def freeze_choices(rows):
    choices, seen = [], set()
    for row in rows:
        if row["split"] != "train" or row["data_role"] != "fit" or row["seed"] != SOURCE_SEED or row["fault"]["name"] != "clean":
            raise ValueError("Only designated fitting sources allowed")
        for event in row["events"]:
            if "branch_diagnostic" not in event:
                continue
            validate_futures(row, event, FIT_IDS)
            k = key(row, event["step"])
            if k in seen:
                raise ValueError("Duplicate decision gate")
            seen.add(k)
            parent = event["policy_proposal"]
            original = gains(event["all_action_branches"], parent)
            samples = [gains(f["branches"], parent) for f in event["branch_diagnostic"]]
            mean = {a: np.mean([g[a] for g in samples], axis=0).tolist() for a in original}
            choices.append(dict(training_seed=k[0], scenario=k[1], seed=k[2], step=k[3],
                                parent=parent, single=choose(original, parent), mean8=choose(mean, parent),
                                mean_gains=mean))
    return choices


def without_diagnostic(row):
    return dict(row, events=[{k: v for k, v in e.items() if k != "branch_diagnostic"} for e in row["events"]])


def score_source(row, choices, indices, *, expected_gates=3):
    lookup = {key(c, c["step"]): c for c in choices}
    if len(lookup) != len(choices):
        raise ValueError("Duplicate frozen choices")
    records = []
    for event in row["events"]:
        if "branch_diagnostic" not in event:
            continue
        validate_futures(row, event, indices)
        c = lookup[key(row, event["step"])]
        parent = event["policy_proposal"]
        if c["parent"] != parent:
            raise ValueError("Frozen parent changed")
        for f in event["branch_diagnostic"]:
            outcomes = gains(f["branches"], parent)
            executed = {b["proposal"]: b["first_execution"] for b in f["branches"]}
            for arm in ARMS:
                action = c[arm]
                if action not in executed:
                    raise ValueError("Frozen choice is not valid")
                gain = outcomes[action] if action != parent else [0., 0., 0.]
                records.append(dict(training_seed=row["training_seed"], scenario=row["scenario"],
                                    seed=row["seed"], step=event["step"], replicate=f["replicate"],
                                    arm=arm, parent=parent, choice=action, gain=gain,
                                    changed=action != parent, executed_change=executed[action] != executed[parent],
                                    qualified=qualified(gain), harmful=harmful(gain)))
    if len(records) != expected_gates * 8 * len(ARMS):
        raise ValueError("Incorrect number of scored decision gates per source")
    source = dict(training_seed=row["training_seed"], scenario=row["scenario"], seed=row["seed"], arms={})
    for arm in ARMS:
        selected = [r for r in records if r["arm"] == arm]
        source["arms"][arm] = dict(mean_gain=np.mean([r["gain"] for r in selected], axis=0).tolist(),
                                   cases=len(selected), changed_cases=sum(r["changed"] for r in selected),
                                   executed_change_cases=sum(r["executed_change"] for r in selected),
                                   qualified_cases=sum(r["qualified"] for r in selected),
                                   harmful_cases=sum(r["harmful"] for r in selected))
    return source, records


def aggregate(sources, arm):
    rows = [s["arms"][arm] for s in sources]
    result = {k: sum(r[k] for r in rows) for k in
              ("cases", "changed_cases", "executed_change_cases", "qualified_cases", "harmful_cases")}
    result["mean_gain"] = np.mean([r["mean_gain"] for r in rows], axis=0).tolist() if rows else None
    result["changed_gates"] = result["changed_cases"] // 8
    result["harmful_fraction_of_changed"] = result["harmful_cases"] / result["changed_cases"] if result["changed_cases"] else None
    return result


def summarize(sources, planned, smoke):
    ids = [(s["training_seed"], s["scenario"], s["seed"]) for s in sources]
    if len(set(ids)) != len(ids) or any(p not in PARENTS or seed != SOURCE_SEED for p, _, seed in ids):
        raise ValueError("Duplicate or invalid source cells")
    names = {s["scenario"] for s in sources}
    full_cells = len(names) == 6 and set(ids) == {(p, s, SOURCE_SEED) for p in PARENTS for s in names}
    arms = {a: aggregate(sources, a) for a in ARMS}
    parents = {str(p): {a: aggregate([s for s in sources if s["training_seed"] == p], a) for a in ARMS} for p in PARENTS}
    single, mean = arms["single"], arms["mean8"]
    gain = mean["mean_gain"]
    checks = dict(full_panel_complete=len(sources) == planned == 18 and full_cells and not smoke,
                  positive_delay_gain=bool(gain and gain[0] > 0),
                  better_delay_than_single=bool(gain and gain[0] > single["mean_gain"][0]),
                  no_throughput_loss=bool(gain and gain[1] >= 0),
                  no_endpoint_wait_loss=bool(gain and gain[2] >= 0),
                  harmful_fraction_not_higher=(mean["harmful_cases"] * single["changed_cases"] <=
                                              single["harmful_cases"] * mean["changed_cases"]
                                              if single["changed_cases"] else mean["harmful_cases"] == 0),
                  every_parent_nonnegative_active_beneficial=all(
                      p["mean8"]["mean_gain"] is not None and p["mean8"]["mean_gain"][0] >= 0 and
                      p["mean8"]["executed_change_cases"] > 0 and p["mean8"]["qualified_cases"] > 0
                      for p in parents.values()))
    return dict(complete=len(sources) == planned, full_panel_complete=checks["full_panel_complete"],
                smoke=smoke, completed_sources=len(sources), planned_sources=planned, arms=arms,
                per_parent=parents, checks=checks, continue_to_label_model_pilot=all(checks.values()),
                target_order=["delay_vehicle_seconds_saved", "throughput_gain_vehicles", "endpoint_wait_seconds_saved"],
                calibration_access=False, probe_access=False, validation_access=False, final_test_access=False,
                model_trained=False, publication_ready=False,
                scope="Frozen hindsight label choices at training states; not a learned policy or full-run traffic improvement")


def read_panel(path):
    manifest = json.loads((path / "manifest.json").read_text())
    report = json.loads((path / "report.json").read_text())
    if not report["full_panel_complete"] or report["smoke"]:
        raise ValueError("A complete non-smoke input panel is required")
    inputs = {str((path / n).resolve()): file_hash(path / n)
              for n in ("manifest.json", "report.json", "source_snapshot.zip", "runs.jsonl", "events.json")}
    inputs.update(manifest["input_hashes"])
    if any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Panel input changed")
    if any(file_hash(path / n) != h for n, h in report["output_hashes"].items()):
        raise ValueError("Panel output changed")
    with zipfile.ZipFile(path / "source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(n)).hexdigest() != h for n, h in manifest["source_hashes"].items()):
            raise ValueError("Panel source archive mismatch")
    rows = [json.loads(line) for line in (path / "runs.jsonl").read_text().splitlines()]
    expected, events = summarize_panel(rows, 18, False, None)
    if any(report[k] != v for k, v in expected.items()) or events != json.loads((path / "events.json").read_text()):
        raise ValueError("Panel summary does not reproduce")
    scenarios = {s.scenario_id: s for s in load_split("train")}
    if len(rows) != 18 or {(r["training_seed"], r["scenario"]) for r in rows} != {(p, s) for p in PARENTS for s in scenarios}:
        raise ValueError("Wrong parent/scenario panel")
    fit_paths = [Path(n) for n in manifest["input_hashes"] if Path(n).name == "fit.jsonl"]
    if len(fit_paths) != 1:
        raise ValueError("Ambiguous fitting source")
    fit = [json.loads(line) for line in fit_paths[0].read_text().splitlines()]
    for row in rows:
        old = [r for r in fit if (r["training_seed"], r["scenario"], r["seed"], r["fault"]) ==
               (row["training_seed"], row["scenario"], row["seed"], row["fault"])]
        if len(old) != 1:
            raise ValueError("Missing fitting source")
        verify_original(row, old[0])
        if row["checkpoint_hash"] != manifest["parents"][str(row["training_seed"])]["sha256"] or row["scenario_hash"] != scenarios[row["scenario"]].compute_hash():
            raise ValueError("Parent/scenario provenance changed")
    return manifest, inputs, sorted(rows, key=lambda r: (r["training_seed"], r["scenario"])), scenarios


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("panel", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--max-wall-seconds", type=float, default=1800.)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    if not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0:
        raise ValueError("A positive finite budget is required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    original, inputs, rows, scenarios = read_panel(args.panel)
    choices = freeze_choices(rows)
    if len(choices) != 54:
        raise ValueError("Expected all 54 frozen choices")
    indices = SMOKE_IDS if args.smoke else EVAL_IDS
    for c in choices:
        old = {future_seed(c["training_seed"], c["scenario"], c["seed"], c["step"], i) for i in FIT_IDS}
        new = {future_seed(c["training_seed"], c["scenario"], c["seed"], c["step"], i) for i in indices}
        if old & new or len(new) != 8:
            raise ValueError("Overlapping future streams")
    cases = rows[:1] if args.smoke else rows
    sources = [f for base in (ROOT / "research", ROOT / "server/app") for f in sorted(base.rglob("*.py"))]
    sources += [PROTOCOL] + sorted((ROOT / "research/scenarios/train").glob("*.yaml"))
    hashes = {str(f.relative_to(ROOT)): file_hash(f) for f in sources}
    args.output.mkdir(parents=True)
    frozen = args.output / "frozen_choices.json"
    write(frozen, choices)
    frozen_hash = file_hash(frozen)
    write(args.output / "manifest.json", dict(input_hashes=inputs, source_hashes=hashes,
          parents=original["parents"], frozen_choices_sha256=frozen_hash, planned_sources=len(cases),
          evaluation_replicates=indices, selection_replicates=FIT_IDS, smoke=args.smoke,
          max_wall_seconds=args.max_wall_seconds, choices_frozen_before_evaluation=True))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sources:
            z.write(f, str(f.relative_to(ROOT)))
    print(f"Output: {args.output.resolve()}; choices frozen: {len(choices)}; sources: {len(cases)}", flush=True)
    budget, summaries, decisions, error = RunBudget(args.max_wall_seconds), [], [], None
    samples = 0
    try:
        with (args.output / "runs.jsonl").open("x") as stream:
            for old in cases:
                budget.check("averaged_label_source")
                parent = old["training_seed"]
                def diagnostic(*arguments):
                    return resample_branches(parent, *arguments, replicate_indices=indices)
                record = audit_run(original["parents"][str(parent)]["path"], scenarios[old["scenario"]],
                                   SOURCE_SEED, VALIDATION_FAULTS[0], HORIZON, 3, all_actions=True,
                                   branch_steps=old["selected_steps"], branch_diagnostic=diagnostic, budget=budget)
                record.update(training_seed=parent, data_role="fit", selected_steps=old["selected_steps"])
                verify_original(record, without_diagnostic(old))
                source, scored = score_source(record, choices, indices)
                summaries.append(source)
                decisions.extend(scored)
                samples += record["signal_samples"] + sum(
                    b["outcome"]["signal_samples"] for e in record["events"] if "branch_diagnostic" in e
                    for branches in [e["all_action_branches"]] + [f["branches"] for f in e["branch_diagnostic"]]
                    for b in branches)
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                stream.flush()
                print(f"[{len(summaries)}/{len(cases)}] parent {parent}, {old['scenario']}; {budget.elapsed:.1f}s", flush=True)
    except BudgetExceeded as exc:
        error = str(exc)
    if file_hash(frozen) != frozen_hash or any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Choices or inputs changed during evaluation")
    if any(file_hash(ROOT / n) != h for n, h in hashes.items()):
        raise ValueError("Source changed during evaluation")
    write(args.output / "source_scores.json", summaries)
    with (args.output / "decisions.jsonl").open("x") as stream:
        for row in decisions:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    report = summarize(summaries, len(cases), args.smoke)
    report.update(stop_reason=error, elapsed_seconds=budget.elapsed,
                  source_and_branch_signal_samples=samples, signal_violations=0,
                  output_hashes={n: file_hash(args.output / n) for n in
                                 ("runs.jsonl", "source_scores.json", "decisions.jsonl", "frozen_choices.json")})
    write(args.output / "report.json", report)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
