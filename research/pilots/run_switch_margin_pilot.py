"""Bounded episode-level calibration with a frozen training prerequisite."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import zipfile

import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import PerceptionFaultInjector
from research.policies.switch_margin import SwitchMarginD3QN, SwitchMarginPressure
from research.training.train_policy import load_split, VALIDATION_FAULTS, RunBudget, BudgetExceeded
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.simulation.benchmark_harness import seed_everything

ROOT = Path(__file__).resolve().parents[2]
PARENT_ROOT = ROOT/"results/research_training/pilot_v5_kbW0lsY3"
PARENTS = {
    "101": ("seed_101/checkpoint_warmup.pt", "1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725"),
    "202": ("seed_202/checkpoint_50.pt", "a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4"),
    "303": ("seed_303/checkpoint_100.pt", "e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052"),
}
GRIDS = {**{seed: [0., .25, .5, 1., 2.] for seed in PARENTS}, "pressure": [0., .05, .1, .2, .4]}
PLAN = dict(
    schema_version="switch_margin_pilot_v1", max_wall_seconds=600, horizon_ticks=1200,
    premise="Episode-level calibration of switch reluctance may improve frozen policies without unstable TD targets or future-specific branch labels.",
    method="Grid search of a single raw-score advantage threshold; keep current phase if its competitor's advantage is at most the positive threshold. Zero exactly preserves the original policy.",
    grids=GRIDS, parent_checkpoints=PARENTS,
    fit="Six existing train templates, one new traffic realization each, clean and fixed mixed faults, matched shield.",
    fit_seeds=[1301001+i for i in range(6)],
    development="Three existing validation templates, two new traffic realizations each, clean and mixed. Known families; not a fresh final test.",
    development_seeds=[1302001+i*100+j for i in range(3) for j in range(2)],
    selection="Minimum equal-case mean delay subject to no aggregate p95 or throughput loss against zero on fit; ties prefer smaller margin.",
    prerequisite="At least two of three D3QN parents select positive margins, aggregate fit delay improves at least 1%, all fit runs complete, no measured violations.",
    development_screen="At least 2% aggregate delay gain against parents, bare pressure, shielded pressure and calibrated shielded pressure; no parent over 1% worse against any reference; no aggregate p95/throughput loss; complete runs, paired arrivals and no violations.",
    no_network_updates=True, automatic_promotion=False, publication_ready=False,
    parameter_units="D3QN Q-value units versus normalized pressure units; five settings and identical fit cases per policy, not identical numeric score scales.",
    related_work="https://www.mdpi.com/2071-1050/17/10/4492 (switching losses in pressure control; related work, not a reproduced algorithm)",
)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(rows):
    return {key: statistics.mean(row[key] for row in rows) for key in ("delay", "p95", "passed")}


def select(rows):
    selection, curves = {}, {}
    for model, grid in GRIDS.items():
        curve = {str(margin): aggregate([r for r in rows if r["model"] == model and r["margin"] == margin]) for margin in grid}
        base = curve["0.0"]
        feasible = [margin for margin in grid if curve[str(margin)]["p95"] <= base["p95"]
                    and curve[str(margin)]["passed"] >= base["passed"]]
        selection[model] = min(feasible, key=lambda m: (curve[str(m)]["delay"], m))
        curves[model] = curve
    base = statistics.mean(curves[s]["0.0"]["delay"] for s in PARENTS)
    tuned = statistics.mean(curves[s][str(selection[s])]["delay"] for s in PARENTS)
    checks = dict(two_nonzero=sum(selection[s] > 0 for s in PARENTS) >= 2,
                  one_percent_fit_gain=tuned <= .99*base,
                  no_fit_violations=all(r["violations"] == 0 for r in rows))
    return dict(parameters=selection, curves=curves, mean_fit_parent=base, mean_fit_candidate=tuned,
                checks=checks, continue_to_development=all(checks.values()))


def summarize_development(rows):
    candidates = [r for r in rows if r["arm"] == "candidate"]
    summary = {arm: aggregate([r for r in rows if r["arm"] == arm]) for arm in sorted({r["arm"] for r in rows})}
    checks = {}
    for reference in ("parent", "bare_pressure", "shield_pressure", "tuned_pressure"):
        base, new = summary[reference], summary["candidate"]
        checks[f"two_percent_delay_gain_vs_{reference}"] = new["delay"] <= .98*base["delay"]
        checks[f"no_p95_loss_vs_{reference}"] = new["p95"] <= base["p95"]
        checks[f"no_throughput_loss_vs_{reference}"] = new["passed"] >= base["passed"]
        checks[f"no_parent_over_one_percent_loss_vs_{reference}"] = all(
            aggregate([r for r in candidates if r["model"] == seed])["delay"] <= 1.01*aggregate(
                [r for r in rows if r["arm"] == reference and (reference != "parent" or r["model"] == seed)])["delay"]
            for seed in PARENTS)
    checks["no_violations"] = all(r["violations"] == 0 for r in rows)
    return dict(means=summary, per_parent={s: aggregate([r for r in candidates if r["model"] == s]) for s in PARENTS},
                checks=checks, continue_to_expanded_validation=all(checks.values()))


def controller(model, margin, arm):
    if model == "pressure":
        base = MaxPressureController() if arm == "bare_pressure" else SwitchMarginPressure(margin)
    else:
        path = str(PARENT_ROOT/PARENTS[model][0])
        if arm == "uq":
            return FlowSyncUQController(checkpoint_path=path)
        base = D3QNController(checkpoint_path=path) if arm == "parent" else SwitchMarginD3QN(path, margin)
    return base if arm == "bare_pressure" else ShieldedController(base)


def run(output):
    torch.set_num_threads(1)
    for name, expected in PARENTS.values():
        if sha(PARENT_ROOT/name) != expected:
            raise ValueError("Frozen parent hash mismatch.")
    fit, development = [], []
    for split, cases, count in (("train", fit, 1), ("validation", development, 2)):
        scenarios = load_split(split)
        if len(scenarios) != (6 if split == "train" else 3):
            raise ValueError("Unexpected scenario panel.")
        for i, scenario in enumerate(scenarios):
            if scenario.duration_steps != 1200:
                raise ValueError("Unexpected horizon.")
            for j in range(count):
                seed = 1301001+i if split == "train" else 1302001+i*100+j
                for fault in VALIDATION_FAULTS:
                    cases.append(dict(case_id=f"{scenario.scenario_id}_{seed}_{fault.name}",
                                      scenario=scenario.to_dict(), seed=seed, fault=asdict(fault)))
    output.mkdir(parents=True, exist_ok=False)
    (output/"raw").mkdir()
    paths = [p for directory in (ROOT/"research", ROOT/"server/app") for p in sorted(directory.rglob("*.py"))]
    manifest = dict(plan=PLAN, fit_cases=fit, development_cases=development,
                    git_commit=ExperimentRunner.get_git_commit(), python_version=sys.version, torch_version=torch.__version__,
                    source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths})
    write(output/"manifest.json", manifest)
    with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, str(path.relative_to(ROOT)))
    budget, runner, rows = RunBudget(600), ExperimentRunner(), []
    from research.scenarios.scenario_schema import ScenarioConfig
    from research.noise.fault_injector import FaultProfile
    def episode(stage, case, model, margin, arm):
        budget.check("whole-run switch calibration")
        seed_everything(case["seed"])
        result = runner.run(controller(model, margin, arm), ScenarioConfig.from_dict(case["scenario"]), case["seed"],
                            fault_injector=PerceptionFaultInjector(FaultProfile(**case["fault"]), seed=case["seed"]+90000),
                            record_trajectory=True)
        target = output/"raw"/f"{len(rows):04}.json.gz"
        with gzip.open(target, "wt") as raw:
            json.dump(dict(case=case, result=result.to_dict()), raw, allow_nan=False)
        row = dict(stage=stage, case_id=case["case_id"], model=model, margin=margin, arm=arm,
                   delay=result.avg_delay, p95=result.p95_delay, passed=result.total_vehicles_passed,
                   violations=result.executed_conflict_violations+result.executed_clearance_violations,
                   samples=result.safety_samples, arrival_trace_hash=result.arrival_trace_hash,
                   checkpoint_hash=result.checkpoint_hash, raw_file=str(target.relative_to(output)), raw_sha256=sha(target),
                   diagnostics=result.controller_diagnostics)
        rows.append(row)
        with (output/"runs.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False)+"\n")
    selection, development_report, stop_reason = None, None, "completed"
    try:
        for model, grid in GRIDS.items():
            for margin in grid:
                for case in fit:
                    episode("fit", case, model, margin, "fit")
                print(f"Fit {model} margin {margin}: {aggregate(rows[-len(fit):])}", flush=True)
        selection = select(rows)
        write(output/"frozen_selection.json", selection)
        if selection["continue_to_development"]:
            print("Training prerequisite passed; frozen development panel begins.", flush=True)
            for case in development:
                for model in PARENTS:
                    for arm in ("candidate", "parent", "uq"):
                        episode("development", case, model, selection["parameters"][model] if arm == "candidate" else 0., arm)
                for arm in ("bare_pressure", "shield_pressure", "tuned_pressure"):
                    episode("development", case, "pressure", selection["parameters"]["pressure"] if arm == "tuned_pressure" else 0., arm)
            development_report = summarize_development([r for r in rows if r["stage"] == "development"])
        else:
            stop_reason = "training_prerequisite_failed"
    except BudgetExceeded:
        stop_reason = "budget_exceeded"
    report = dict(complete=stop_reason != "budget_exceeded", stop_reason=stop_reason, runs=len(rows),
                  signal_samples=sum(r["samples"] for r in rows), elapsed_seconds=budget.elapsed,
                  selection=selection, development=development_report, publication_ready=False, automatic_promotion=False,
                  continue_to_expanded_validation=bool(development_report and development_report["continue_to_expanded_validation"]))
    write(output/"report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify) if args.verify else run(args.output), indent=2))


def verify(output):
    manifest = json.loads((output/"manifest.json").read_text())
    report = json.loads((output/"report.json").read_text())
    rows = [json.loads(line) for line in (output/"runs.jsonl").read_text().splitlines()]
    if manifest["plan"] != json.loads(json.dumps(PLAN)) or not report["complete"]:
        raise ValueError("Incomplete panel or protocol differs; partial runs cannot pass.")
    fit = [r for r in rows if r["stage"] == "fit"]
    expected_fit = {(c["case_id"], model, margin) for c in manifest["fit_cases"] for model, grid in GRIDS.items() for margin in grid}
    if len(fit) != len(expected_fit) or {(r["case_id"], r["model"], r["margin"]) for r in fit} != expected_fit:
        raise ValueError("Incomplete or duplicate fit rows.")
    selection = select(fit)
    if selection != report["selection"] or selection != json.loads((output/"frozen_selection.json").read_text()):
        raise ValueError("Frozen selection does not reconstruct.")
    dev = [r for r in rows if r["stage"] == "development"]
    expected_dev = {(c["case_id"], model, arm) for c in manifest["development_cases"] for model in PARENTS for arm in ("candidate","parent","uq")}
    expected_dev |= {(c["case_id"], "pressure", arm) for c in manifest["development_cases"] for arm in ("bare_pressure","shield_pressure","tuned_pressure")}
    if selection["continue_to_development"]:
        if len(dev) != len(expected_dev) or {(r["case_id"],r["model"],r["arm"]) for r in dev} != expected_dev:
            raise ValueError("Incomplete or duplicate development rows.")
        if report["development"] != summarize_development(dev) or report["stop_reason"] != "completed":
            raise ValueError("Development report mismatch.")
    elif dev or report["development"] is not None or report["stop_reason"] != "training_prerequisite_failed":
        raise ValueError("Development proceeded without its prerequisite.")
    cases = {c["case_id"]: c for c in manifest["fit_cases"]+manifest["development_cases"]}
    arrivals = {}
    for row in rows:
        path = output/row["raw_file"]
        if sha(path) != row["raw_sha256"]:
            raise ValueError("Raw result hash mismatch.")
        with gzip.open(path,"rt") as stream: raw=json.load(stream)
        result = raw["result"]
        values = dict(delay=result["avg_delay"],p95=result["p95_delay"],passed=result["total_vehicles_passed"],
                      violations=result["executed_conflict_violations"]+result["executed_clearance_violations"],
                      samples=result["safety_samples"],checkpoint_hash=result["checkpoint_hash"],
                      arrival_trace_hash=result["arrival_trace_hash"],diagnostics=result["controller_diagnostics"])
        if raw["case"] != cases[row["case_id"]] or any(row[k] != v for k,v in values.items()) or result["num_steps"] != 1200 or row["samples"] != 1200:
            raise ValueError("Raw metrics, case or executed coverage mismatch.")
        if row["model"] in PARENTS and row["checkpoint_hash"] != PARENTS[row["model"]][1]:
            raise ValueError("Evaluated checkpoint hash mismatch.")
        arrivals.setdefault(row["case_id"],set()).add(row["arrival_trace_hash"])
    if any(len(hashes) != 1 for hashes in arrivals.values()) or len(rows) != report["runs"] or len(fit)+len(dev) != len(rows):
        raise ValueError("Unpaired arrivals or run-count mismatch.")
    if report["signal_samples"] != sum(row["samples"] for row in rows) or report["continue_to_expanded_validation"] != bool(report["development"] and report["development"]["continue_to_expanded_validation"]):
        raise ValueError("Coverage or continuation flag mismatch.")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(manifest["source_sha256"]):
            raise ValueError("Incomplete archived sources.")
        for name, expected in manifest["source_sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected or sha(ROOT/name) != expected:
                raise ValueError("Historical audit needs its archived implementation/runtime.")
    return dict(verified=True,runs=len(rows),paired_arrivals=True,
                independently_rerun_trajectories=0,scope="Raw outcome hashes, coverage, selection and comparison reconstruction.",
                publication_ready=False,continue_to_expanded_validation=report["continue_to_expanded_validation"])


if __name__ == "__main__":
    main()
