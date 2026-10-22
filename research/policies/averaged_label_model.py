"""Observed-input model and fixed protocol helpers for the averaged-label pilot."""
import hashlib
import itertools
import json

import numpy as np

from research.policies.action_rank_policy import FEATURES, RIDGE, TARGET_SCALE, action_features
from research.audits.audit_arrival_label_stability import gains
from research.calibration.calibrate_action_rank import choose
from research.evaluation.evaluate_averaged_action_labels import ARMS, aggregate, validate_futures


def configuration(smoke=False):
    return dict(parents=(101,) if smoke else (101, 202, 303),
                fit_seeds=(96901, 96902) if smoke else (96301, 96302, 96303, 96304),
                probe_seeds=(96903,) if smoke else (96401, 96402),
                fit_ids=tuple(range(100, 108)) if smoke else tuple(range(8)),
                probe_ids=tuple(range(108, 116)) if smoke else tuple(range(8, 16)), smoke=smoke)


def cells(config, names, role):
    if role not in ("fit", "probe"):
        raise ValueError("Unknown data role")
    return [(parent, name, seed) for seed in config[f"{role}_seeds"]
            for parent, name in itertools.product(config["parents"], sorted(names))]


def selected_steps(source, parent):
    if source["split"] != "train":
        raise ValueError("Training sources only")
    eligible = [e["step"] for e in source["events"] if sum(e["mask"]) >= 2 and e["step"] + 400 <= 1200]
    if len(eligible) != len(set(eligible)) or len(eligible) < 2:
        raise ValueError("Need two distinct eligible decision gates")
    def priority(step):
        key = ["averaged-label-pilot-v1", parent, source["scenario"], source["seed"], step]
        return hashlib.sha256(json.dumps(key).encode()).hexdigest(), step
    return sorted(sorted(eligible, key=priority)[:2])


def features(event, action):
    return action_features(event["policy_observation"], event["phase"], event["phase_age"],
                           event["q_values"], event["policy_proposal"], action)


def fit_models(rows, config, names, parents):
    keys = [(r["training_seed"], r["scenario"], r["seed"]) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != set(cells(config, names, "fit")):
        raise ValueError("Incomplete/duplicate fitting panel")
    models = {}
    for parent in config["parents"]:
        xs, single, means, groups = [], [], [], []
        for row in (r for r in rows if r["training_seed"] == parent):
            if (row["split"] != "train" or row["data_role"] != "fit" or row["fault"]["name"] != "clean"
                    or row["checkpoint_hash"] != parents[str(parent)]["sha256"]):
                raise ValueError("Wrong fitting role or checkpoint")
            events = [e for e in row["events"] if "branch_diagnostic" in e]
            if len(events) != 2 or [e["step"] for e in events] != row["selected_steps"]:
                raise ValueError("Incorrect fitting gates")
            for event in events:
                validate_futures(row, event, config["fit_ids"])
                original = gains(event["all_action_branches"], event["policy_proposal"])
                futures = [gains(f["branches"], event["policy_proposal"]) for f in event["branch_diagnostic"]]
                for action in sorted(original):
                    xs.append(features(event, action))
                    single.append(original[action])
                    means.append(np.mean([g[action] for g in futures], axis=0))
                    groups.append(row["seed"])
        x = np.asarray(xs, dtype=float)
        if x.ndim != 2 or x.shape[1] != 8 or not np.isfinite(x).all():
            raise ValueError("Invalid observed fitting inputs")
        unique, counts = np.unique(groups, return_counts=True)
        weight = np.array([1. / dict(zip(unique, counts))[g] for g in groups])
        scale = np.maximum(np.sqrt(np.average(x * x, axis=0, weights=weight)), .05)
        weight /= weight.mean()
        z = x / scale
        for arm, target in (("single", single), ("mean8", means)):
            y = np.asarray(target, dtype=float)
            if not np.isfinite(y).all():
                raise ValueError("Non-finite fitting targets")
            point = np.linalg.solve(z.T @ (weight[:, None] * z) + RIDGE * np.eye(8),
                                    z.T @ (weight[:, None] * (y / TARGET_SCALE)))
            models[(parent, arm)] = dict(version="averaged_label_ridge_v1", parent=parent, arm=arm,
                parent_sha256=parents[str(parent)]["sha256"], features=list(FEATURES), scale=scale.tolist(),
                point=point.tolist(), target_scale=TARGET_SCALE.tolist(), ridge=RIDGE,
                fit_seeds=list(config["fit_seeds"]), fit_scenarios=sorted(names), fit_examples=len(xs),
                fitting_sources=len(names) * len(config["fit_seeds"]), smoke=config["smoke"])
    return models


def predict(model, event, action):
    scale, point = np.asarray(model["scale"]), np.asarray(model["point"])
    if (model["version"] != "averaged_label_ridge_v1" or model["features"] != list(FEATURES)
            or model["target_scale"] != TARGET_SCALE.tolist() or scale.shape != (8,) or point.shape != (8, 3)
            or not np.isfinite(scale).all() or not np.isfinite(point).all() or (scale <= 0).any()):
        raise ValueError("Invalid frozen model")
    return ((features(event, action) / scale) @ point * TARGET_SCALE).tolist()


def predict_source(source, steps, models):
    """Uses only delivered gate observations; outcomes/labels never enter features."""
    result = []
    parent = source["training_seed"]
    for event in source["events"]:
        if event["step"] not in steps:
            continue
        proposal = event["policy_proposal"]
        predictions = {}
        choices = dict(training_seed=parent, scenario=source["scenario"], seed=source["seed"],
                       step=event["step"], parent=proposal)
        for arm in ("single", "mean8"):
            model = models[(parent, arm)]
            if model["parent_sha256"] != source["checkpoint_hash"] or model["parent"] != parent or model["arm"] != arm:
                raise ValueError("Frozen model/parent mismatch")
            estimates = {a: predict(model, event, a) for a, valid in enumerate(event["mask"]) if valid and a != proposal}
            if not event["mask"][proposal]:
                raise ValueError("Invalid parent action")
            choices[arm] = choose(estimates, proposal)
            predictions[arm] = estimates
        choices["predictions"] = predictions
        result.append(choices)
    if len(result) != 2 or {r["step"] for r in result} != set(steps):
        raise ValueError("Missing/duplicate probe gate")
    return result


def prediction_errors(record, choices):
    errors = {a: [] for a in ("single", "mean8")}
    by_step = {c["step"]: c for c in choices}
    for event in record["events"]:
        if event["step"] not in by_step:
            continue
        futures = [gains(f["branches"], event["policy_proposal"]) for f in event["branch_diagnostic"]]
        for arm in errors:
            for action, predicted in by_step[event["step"]]["predictions"][arm].items():
                target = np.mean([g[int(action)] for g in futures], axis=0)
                errors[arm].append(np.abs(target - np.asarray(predicted)))
    return {a: np.mean(v, axis=0).tolist() for a, v in errors.items()}


def summarize(scores, config, names, fit_count, models_count):
    planned_fit, planned_probe = len(cells(config, names, "fit")), len(cells(config, names, "probe"))
    keys = [(s["training_seed"], s["scenario"], s["seed"]) for s in scores]
    if len(set(keys)) != len(keys) or not set(keys) <= set(cells(config, names, "probe")):
        raise ValueError("Invalid/duplicate probe cells")
    complete = fit_count == planned_fit and len(scores) == planned_probe and models_count == 2 * len(config["parents"])
    arms = {a: aggregate(scores, a) for a in ARMS}
    parents = {str(p): {a: aggregate([s for s in scores if s["training_seed"] == p], a) for a in ARMS}
               for p in config["parents"]}
    mean, single = arms["mean8"], arms["single"]
    gain = mean["mean_gain"]
    checks = dict(full_pilot_complete=complete and not config["smoke"],
                  positive_delay_gain=bool(gain and gain[0] > 0),
                  better_than_single=bool(gain and gain[0] > single["mean_gain"][0]),
                  no_throughput_loss=bool(gain and gain[1] >= 0),
                  no_endpoint_wait_loss=bool(gain and gain[2] >= 0),
                  harmful_fraction_not_higher=(mean["harmful_cases"] * single["changed_cases"] <=
                    single["harmful_cases"] * mean["changed_cases"] if single["changed_cases"] else mean["harmful_cases"] == 0),
                  every_parent_nonnegative_active_beneficial=all(
                    p["mean8"]["mean_gain"] is not None and p["mean8"]["mean_gain"][0] >= 0 and
                    p["mean8"]["executed_change_cases"] > 0 and p["mean8"]["qualified_cases"] > 0 for p in parents.values()))
    errors = {a: np.mean([s["prediction_mae"][a] for s in scores], axis=0).tolist() if scores else None
              for a in ("single", "mean8")}
    return dict(complete=complete, full_pilot_complete=checks["full_pilot_complete"], smoke=config["smoke"],
                fit_sources=fit_count, planned_fit_sources=planned_fit, probe_sources=len(scores),
                planned_probe_sources=planned_probe, fitted_models=models_count, arms=arms, per_parent=parents,
                mean_source_prediction_mae=errors, checks=checks, continue_to_full_rollout_pilot=all(checks.values()),
                dqn_retrained=False, model_promoted=False, publication_ready=False,
                calibration_access=False, validation_access=False, final_test_access=False,
                target_order=["delay_vehicle_seconds_saved", "throughput_gain_vehicles", "endpoint_wait_seconds_saved"],
                scope="Observed-input model on excluded training-source branch outcomes; not full-run control")
