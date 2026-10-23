#!/usr/bin/env python3
"""Fixed, grouped fitting-data screen: joint benefit versus outcome regression."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np

from research.policies.action_rank_policy import FEATURES, RIDGE, TARGET_SCALE
from research.audits.audit_arrival_label_stability import gains, qualified
from research.policies.averaged_label_model import cells, configuration, features, selected_steps
from research.calibration.calibrate_action_rank import choose
from research.evaluation.evaluate_averaged_action_labels import aggregate, score_source, validate_futures, write
from research.training.train_policy import VALIDATION_FAULTS, file_hash, load_split

PROTOCOL = ROOT / "research/docs/protocols/JOINT_BENEFIT_PROTOCOL_20261021.md"
FIT_HASH = "11f2cd40cd0b72389e81237c5d680453e3833df79b327aa142b4e0d59d7286a2"
ARMS = ("parent", "regression", "joint")
# Reuse the existing paired-future scorer without changing its historical API.
SCORE_NAMES = {"parent": "parent", "single": "regression", "mean8": "joint"}


def sigmoid(value):
    return np.exp(-np.logaddexp(0., -np.asarray(value)))


def logistic(z, labels, base_weight, *, max_iterations=100):
    """Class-balanced penalized loss; the final intercept is NOT penalized."""
    z, y, w = np.asarray(z, float), np.asarray(labels, float), np.asarray(base_weight, float)
    if (z.ndim != 2 or z.shape[1] != 8 or not len(z) or y.shape != (len(z),)
            or w.shape != y.shape or not all(np.isfinite(a).all() for a in (z, y, w))
            or (w <= 0).any() or not np.isin(y, [0, 1]).all()):
        raise ValueError("Invalid logistic fitting arrays")
    if len(np.unique(y)) == 1:
        return dict(constant=float(y[0]), coefficients=None, iterations=0, gradient_max=0., converged=True)
    w = w.copy()
    for label in (0., 1.):
        w[y == label] /= w[y == label].sum()
    w /= w.mean()
    x = np.column_stack((z, np.ones(len(z))))
    penalty = np.diag([RIDGE] * 8 + [0.])
    beta = np.zeros(9)

    def loss(b):
        eta = x @ b
        return float(w @ (np.logaddexp(0., eta) - y * eta) + .5 * b @ penalty @ b)

    for iteration in range(max_iterations + 1):
        p = sigmoid(x @ beta)
        gradient = x.T @ (w * (p - y)) + penalty @ beta
        norm = float(np.max(np.abs(gradient)))
        if norm <= 1e-7:
            return dict(constant=None, coefficients=beta.tolist(), iterations=iteration,
                        gradient_max=norm, converged=True)
        if iteration == max_iterations:
            break
        hessian = x.T @ ((w * p * (1. - p))[:, None] * x) + penalty
        direction = np.linalg.solve(hessian, gradient)
        old_loss, step = loss(beta), 1.
        for _ in range(50):
            candidate = beta - step * direction
            if loss(candidate) <= old_loss - 1e-4 * step * float(gradient @ direction):
                beta = candidate
                break
            step *= .5
        else:
            raise RuntimeError("Joint optimizer line search failed")
    raise RuntimeError("Joint optimizer did not converge")


def fit_pair(x, target, groups):
    """Receives fitting arrays ONLY; no held-out outcomes or normalization."""
    x, target, groups = np.asarray(x, float), np.asarray(target, float), np.asarray(groups)
    if (x.ndim != 2 or x.shape[1] != 8 or not len(x) or target.shape != (len(x), 3)
            or groups.shape != (len(x),) or not np.isfinite(x).all() or not np.isfinite(target).all()):
        raise ValueError("Invalid fitting arrays")
    unique, counts = np.unique(groups, return_counts=True)
    count = dict(zip(unique, counts))
    weight = np.array([1. / count[g] for g in groups])
    scale = np.maximum(np.sqrt(np.average(x * x, axis=0, weights=weight)), .05)
    weight /= weight.mean()
    z = x / scale
    point = np.linalg.solve(z.T @ (weight[:, None] * z) + RIDGE * np.eye(8),
                            z.T @ (weight[:, None] * (target / TARGET_SCALE)))
    common = dict(features=list(FEATURES), scale=scale.tolist(), ridge=RIDGE,
                  fit_seeds=unique.tolist(), fit_examples=len(x), training_only=True)
    return dict(regression=dict(common, version="joint_screen_ridge_v1", point=point.tolist(),
                                target_scale=TARGET_SCALE.tolist()),
                joint=dict(common, version="joint_screen_logistic_v1",
                           **logistic(z, [qualified(t) for t in target], weight),
                           score_semantics="Class-balanced score, NOT calibrated probability or uncertainty bound"))


def predict(model, x):
    x, scale = np.asarray(x, float), np.asarray(model["scale"], float)
    if (x.shape != (8,) or scale.shape != (8,) or not np.isfinite(x).all()
            or not np.isfinite(scale).all() or (scale <= 0).any() or model["features"] != list(FEATURES)):
        raise ValueError("Invalid prediction inputs/model")
    if model["version"] == "joint_screen_ridge_v1":
        point = np.asarray(model["point"], float)
        if point.shape != (8, 3) or not np.isfinite(point).all() or model["target_scale"] != TARGET_SCALE.tolist():
            raise ValueError("Invalid regression model")
        return ((x / scale) @ point * TARGET_SCALE).tolist()
    if model["version"] != "joint_screen_logistic_v1" or not model["converged"]:
        raise ValueError("Invalid joint model")
    if model["constant"] is not None:
        if model["constant"] not in (0., 1.):
            raise ValueError("Invalid single-class model")
        return float(model["constant"])
    beta = np.asarray(model["coefficients"], float)
    if beta.shape != (9,) or not np.isfinite(beta).all():
        raise ValueError("Invalid joint coefficients")
    return float(sigmoid(np.append(x / scale, 1.) @ beta))


def choose_joint(estimates, parent):
    if any(not np.isfinite(s) or not 0. <= s <= 1. for s in estimates.values()):
        raise ValueError("Invalid joint scores")
    eligible = [a for a, score in estimates.items() if score > .5]
    return min(eligible, key=lambda a: (-estimates[a], a)) if eligible else parent


def gate_targets(event):
    samples = [gains(f["branches"], event["policy_proposal"]) for f in event["branch_diagnostic"]]
    return {a: np.mean([s[a] for s in samples], axis=0).tolist() for a in samples[0]}


def fit_fold(rows, parent, excluded_seed):
    training = [r for r in rows if r["training_seed"] == parent and r["seed"] != excluded_seed]
    expected = set(configuration()["fit_seeds"]) - {excluded_seed}
    if excluded_seed not in configuration()["fit_seeds"] or {r["seed"] for r in training} != expected:
        raise ValueError("Incorrect grouped fold")
    if (any(r["data_role"] != "fit" or r["split"] != "train" for r in training)
            or len({r["checkpoint_hash"] for r in training}) != 1):
        raise ValueError("Incorrect fitting role/parent")
    x, y, groups = [], [], []
    for row in training:
        for event in row["events"]:
            if "branch_diagnostic" not in event:
                continue
            for action, target in sorted(gate_targets(event).items()):
                x.append(features(event, action))
                y.append(target)
                groups.append(row["seed"])
    result = fit_pair(x, y, groups)
    for model in result.values():
        model.update(parent=parent, excluded_seed=excluded_seed,
                     parent_sha256=training[0]["checkpoint_hash"],
                     fit_sources=[dict(scenario=r["scenario"], seed=r["seed"]) for r in training])
    return result


def predict_source(row, pair):
    if set(pair) != {"regression", "joint"} or any(
            m["parent"] != row["training_seed"] or m["parent_sha256"] != row["checkpoint_hash"]
            or m["excluded_seed"] != row["seed"] or row["seed"] in m["fit_seeds"] for m in pair.values()):
        raise ValueError("Held-out source/model mismatch")
    records = []
    for event in row["events"]:
        if event["step"] not in row["selected_steps"]:
            continue
        parent = event["policy_proposal"]
        if not event["mask"][parent]:
            raise ValueError("Invalid parent action")
        estimates = {arm: {a: predict(model, features(event, a)) for a, valid in enumerate(event["mask"])
                          if valid and a != parent} for arm, model in pair.items()}
        records.append(dict(training_seed=row["training_seed"], scenario=row["scenario"], seed=row["seed"],
                            step=event["step"], parent=parent, predictions=estimates,
                            regression=choose(estimates["regression"], parent),
                            joint=choose_joint(estimates["joint"], parent)))
    if len(records) != 2 or {c["step"] for c in records} != set(row["selected_steps"]):
        raise ValueError("Invalid held-out gates")
    return records


def score(row, predictions):
    historical = [dict(c, single=c["regression"], mean8=c["joint"]) for c in predictions]
    source, records = score_source(row, historical, range(8), expected_gates=2)
    source["arms"] = {SCORE_NAMES[a]: v for a, v in source["arms"].items()}
    for record in records:
        record["arm"] = SCORE_NAMES[record["arm"]]
    return source, records


def summarize(scores, folds):
    config = configuration()
    scenarios = {s.scenario_id for s in load_split("train")}
    expected = set(cells(config, scenarios, "fit"))
    keys = [(r["training_seed"], r["scenario"], r["seed"]) for r in scores]
    if len(keys) != len(set(keys)) or not set(keys) <= expected or len(folds) != len(set(folds)):
        raise ValueError("Invalid score/fold cells")
    complete = set(keys) == expected and set(folds) == {(p, s) for p in config["parents"] for s in config["fit_seeds"]}
    arms = {a: aggregate(scores, a) for a in ARMS}
    parents = {str(p): {a: aggregate([r for r in scores if r["training_seed"] == p], a) for a in ARMS}
               for p in config["parents"]}
    joint, reg = arms["joint"], arms["regression"]
    gain = joint["mean_gain"]
    checks = dict(full_panel_complete=complete, positive_delay_gain=bool(gain and gain[0] > 0),
                  better_than_regression=bool(gain and gain[0] > reg["mean_gain"][0]),
                  no_throughput_loss=bool(gain and gain[1] >= 0),
                  no_endpoint_wait_loss=bool(gain and gain[2] >= 0),
                  harmful_fraction_not_higher=(joint["harmful_cases"] * reg["changed_cases"] <=
                    reg["harmful_cases"] * joint["changed_cases"] if reg["changed_cases"] else joint["harmful_cases"] == 0),
                  every_parent_nonnegative_active_beneficial=all(
                    v["joint"]["mean_gain"] is not None and v["joint"]["mean_gain"][0] >= 0 and
                    v["joint"]["executed_change_cases"] > 0 and v["joint"]["qualified_cases"] > 0 for v in parents.values()))
    return dict(complete=complete, completed_folds=len(folds), fitted_models=2 * len(folds), sources=len(scores),
                arms=arms, per_parent=parents, checks=checks, continue_to_fresh_source_pilot=all(checks.values()),
                calibration_access=False, probe_access=False, validation_access=False, final_test_access=False,
                dqn_retrained=False, model_promoted=False, publication_ready=False,
                target_order=["delay_vehicle_seconds_saved", "throughput_gain_vehicles", "endpoint_wait_seconds_saved"],
                scope="Grouped fitting-data development screen; single action then parent continuation; not full-run performance")


def read_fit(path):
    """Read no probe/calibration/pilot scores, even for model selection."""
    if file_hash(path / "fit.jsonl") != FIT_HASH:
        raise ValueError("Fitting data differs from prespecified panel")
    manifest = json.loads((path / "manifest.json").read_text())
    rows = [json.loads(line) for line in (path / "fit.jsonl").read_text().splitlines()]
    config = configuration()
    scenarios = {s.scenario_id: s for s in load_split("train")}
    keys = [(r["training_seed"], r["scenario"], r["seed"]) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != set(cells(config, scenarios, "fit")):
        raise ValueError("Incomplete/duplicate fitting panel")
    for row in rows:
        if (row["data_role"] != "fit" or row["split"] != "train" or row["fault"] != VALIDATION_FAULTS[0].to_dict()
                or row["checkpoint_hash"] != manifest["parents"][str(row["training_seed"])]["sha256"]
                or row["scenario_hash"] != scenarios[row["scenario"]].compute_hash()
                or row["signal_samples"] != 1200 or row["signal_violations"]):
            raise ValueError("Incorrect fitting provenance or unsafe source")
        events = [e for e in row["events"] if "branch_diagnostic" in e]
        if [e["step"] for e in events] != row["selected_steps"] or selected_steps(row, row["training_seed"]) != row["selected_steps"]:
            raise ValueError("Incorrect fitting gates")
        for event in events:
            validate_futures(row, event, range(8))
    for item in manifest["parents"].values():
        if file_hash(item["path"]) != item["sha256"]:
            raise ValueError("Parent checkpoint changed")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pilot", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    rows = read_fit(args.pilot)
    args.output.mkdir(parents=True, exist_ok=False)
    sources = sorted((ROOT / "research").rglob("*.py")) + [PROTOCOL]
    source_hashes = {str(f.relative_to(ROOT)): file_hash(f) for f in sources}
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sources:
            z.write(f, str(f.relative_to(ROOT)))
    inputs = {str((args.pilot / name).resolve()): file_hash(args.pilot / name) for name in ("fit.jsonl", "manifest.json")}
    write(args.output / "manifest.json", dict(input_hashes=inputs, source_hashes=source_hashes,
                                              protocol_sha256=file_hash(PROTOCOL), config=configuration()))
    folds, scores, decisions = [], [], []
    confusion = {a: Counter(dict(true_positive=0, false_positive=0, false_negative=0, true_negative=0))
                 for a in ("regression", "joint")}
    with (args.output / "predictions.jsonl").open("x") as stream:
        for parent in configuration()["parents"]:
            for excluded in configuration()["fit_seeds"]:
                pair = fit_fold(rows, parent, excluded)
                for arm, model in pair.items():
                    write(args.output / f"model_{parent}_{excluded}_{arm}.json", model)
                for row in (r for r in rows if r["training_seed"] == parent and r["seed"] == excluded):
                    choices = predict_source(row, pair)
                    stream.write(json.dumps(choices, allow_nan=False) + "\n")
                    stream.flush()
                    source, records = score(row, choices)
                    scores.append(source)
                    decisions.extend(records)
                    by_step = {c["step"]: c for c in choices}
                    for event in (e for e in row["events"] if e["step"] in by_step):
                        for action, truth in gate_targets(event).items():
                            actual = qualified(truth)
                            for arm in confusion:
                                value = by_step[event["step"]]["predictions"][arm][action]
                                estimate = qualified(value) if arm == "regression" else value > .5
                                name = ("true_positive" if actual else "false_positive") if estimate else (
                                    "false_negative" if actual else "true_negative")
                                confusion[arm][name] += 1
                folds.append((parent, excluded))
    write(args.output / "source_scores.json", scores)
    with (args.output / "decisions.jsonl").open("x") as stream:
        for record in decisions:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
    if any(file_hash(path) != digest for path, digest in inputs.items()):
        raise ValueError("Input changed during comparison")
    result = summarize(scores, folds)
    result["joint_label_confusion"] = confusion
    result["output_hashes"] = {f.name: file_hash(f) for f in sorted(args.output.iterdir()) if f.is_file()}
    write(args.output / "report.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
