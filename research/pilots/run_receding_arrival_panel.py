"""One frozen cadence-alignment hypothesis on new training-family traffic seeds."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np

from research.audits.audit_arrival_reference_gap import ANCHORS, csv_file, csv_matches, load_reference, load_raw, require_anchor_match
from research.experiments.track_runtime import rollout_tracks, replay_tracks
from research.pilots import run_arrival_window_panel as v1
from research.policies.receding_arrival import CadencedArrival, PRIMARY, SPECS, VERSION
from research.policies.arrival_extension import Timing
from research.training.train_policy import RunBudget, BudgetExceeded

ROOT, sha, write = v1.ROOT, v1.sha, v1.write
METHODS = tuple(SPECS)
PLAN = dict(schema_version=VERSION, invocation_budget_seconds=180, max_invocations=2, processes=3,
    basis="The preceding matched control measured +0.482836 s mean delay for all-visible MP at 2 s vs 10 Hz; fresh primary matched native on 255 cached disagreement ticks. This does not prove a faster primary improves control.",
    hypothesis="Keep arrival equations, position history, uncertainty windows, 2 s lookahead and all physical rules fixed; replace the 2 s policy cache with 10 Hz receding decisions.",
    methods=SPECS, primary=PRIMARY, traffic_seeds=[1342001+i for i in range(6)],
    panel="Six existing train templates x 3 unchanged sensing presets x 11 methods = 198 full 1200-tick runs. New traffic realizations, known templates/faults, not an independent final test.",
    adaptation="Advanced-MP variants share the 2 s running-demand horizon but now act at 10 Hz; this is an explicit control-rate adaptation, not an exact published-network reproduction. Weights 1/2/4 remain frozen.",
    anchors="Two previously consumed mechanics cases, native all-visible MP and original 2 s window rule: 4 exact semantic anchors, with only explicit method-label mapping when needed.",
    screen="Primary >=2% delay gain vs all classical references and original2s window; >=1% vs receding point/no-age ablations. No aggregate p95/throughput loss vs any reference; no case >5% delay loss. Clean mean/p95<=1% loss and no throughput loss vs receding age-gated reference. Complete paired coverage, exact anchors and zero measured signal violations.",
    scope="Cadence alignment is an engineering hypothesis, not a new algorithmic novelty claim. No fitting, training, parameter grid, source changes after outcomes, automatic promotion or final-test access.",
    no_training=True, automatic_promotion=False, publication_ready=False)


def cases():
    original = v1.panel_cases()
    mapping = {name: 1342001+i for i, name in enumerate(sorted({c["scenario"]["scenario_id"] for c in original}))}
    return [{**case, "seed": mapping[case["scenario"]["scenario_id"]],
             "case_id": f"{case['scenario']['scenario_id']}_{mapping[case['scenario']['scenario_id']]}_{case['fault']['name']}"}
            for case in original]


def controller(method, case):
    return CadencedArrival(method, Timing(all_red=case["scenario"]["red_duration"]))


def comparison(rows):
    expected = {(c["case_id"], method) for c in cases() for method in METHODS}
    if len(rows) != len(expected) or {(r["case_id"], r["method"]) for r in rows} != expected:
        return dict(primary_endpoint_complete=False, continue_to_fresh_development=False)
    groups = {method: [r for r in rows if r["method"] == method] for method in METHODS}
    means = {method: v1.means(group) for method, group in groups.items()}
    primary, checks = means[PRIMARY], {}
    for method, group in groups.items():
        if method == PRIMARY:
            continue
        gain = .01 if method in ("receding_point", "receding_no_age") else .02
        checks[f"delay_vs_{method}"] = primary["delay"] <= (1-gain)*means[method]["delay"]
        checks[f"p95_vs_{method}"] = primary["p95"] <= means[method]["p95"]
        checks[f"throughput_vs_{method}"] = primary["passed"] >= means[method]["passed"]
        lookup = {r["case_id"]: r for r in group}
        checks[f"case_loss_vs_{method}"] = all(r["delay"] <= 1.05*lookup[r["case_id"]]["delay"] for r in groups[PRIMARY])
    clean = {c["case_id"] for c in cases() if c["fault"]["name"] == "clean_tracks"}
    new = v1.means([r for r in groups[PRIMARY] if r["case_id"] in clean])
    base = v1.means([r for r in groups["age_gated_advanced_mp"] if r["case_id"] in clean])
    checks.update(clean_delay=new["delay"] <= 1.01*base["delay"], clean_p95=new["p95"] <= 1.01*base["p95"],
        clean_throughput=new["passed"] >= base["passed"],
        paired_arrivals=all(len({r["arrival_trace_hash"] for r in rows if r["case_id"] == c["case_id"]}) == 1 for c in cases()),
        signal_audit=all(r["samples"] == 1200 and r["violations"] == 0 for r in rows))
    return dict(primary_endpoint_complete=True, means=means, checks=checks, continue_to_fresh_development=all(checks.values()))


def case_worker(output, case, deadline, invocation):
    target = output/"raw"/case["case_id"]
    target.mkdir(parents=True, exist_ok=True)
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    for method in METHODS:
        path = target/f"{method}.json.gz"
        if path.exists():
            continue
        try:
            raw = rollout_tracks(case, controller(method, case), budget)
        except BudgetExceeded:
            return
        partial = target/f"{method}.{invocation}.partial.gz"
        with gzip.open(partial, "wt") as stream:
            json.dump(raw, stream, allow_nan=False)
        partial.replace(path)
    print(f"Completed receding case: {case['case_id']}", flush=True)


def collect_rows(output):
    rows = []
    for case in cases():
        for method in METHODS:
            path = output/"raw"/case["case_id"]/f"{method}.json.gz"
            if not path.exists():
                continue
            with gzip.open(path, "rt") as stream:
                raw = json.load(stream)
            if raw["case"] != case or raw["method"] != method:
                raise ValueError("Receding bundle case/method mismatch")
            rows.append(dict(case_id=case["case_id"], method=method, **raw["result"], raw_file=str(path.relative_to(output)), sha256=sha(path)))
    return rows


def run(reference, output, resume=False, basis=None):
    reference, output = reference.resolve(), output.resolve()
    old_manifest, old_report = load_reference(reference)
    if resume:
        manifest = json.loads((output/"manifest.json").read_text())
        basis = Path(manifest["basis_report"])
        if (output/"report.json").exists():
            raise ValueError("Sealed receding panel cannot be resumed")
        if manifest["plan"] != json.loads(json.dumps(PLAN)):
            raise ValueError("Resume protocol changed")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected:
                raise ValueError("Resume requires original sources")
    else:
        basis = basis.resolve()
        diagnostic = json.loads(basis.read_text())
        if not diagnostic["complete"] or not diagnostic["audit_integrity_passed"]:
            raise ValueError("Cadence hypothesis needs its completed integrity-checked diagnostic")
        if subprocess.check_output(["git", "status", "--porcelain", "--", "research", "server/app"], cwd=ROOT, text=True).strip():
            raise ValueError("Commit executable sources before performance collection")
        output.mkdir(parents=True, exist_ok=False)
        paths = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
        manifest = dict(plan=PLAN, cases=cases(), reference_directory=str(reference), reference_report_sha256=sha(reference/"report.json"),
            basis_report=str(basis), basis_report_sha256=sha(basis),
            python_version=sys.version, numpy_version=np.__version__,
            git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths})
        write(output/"manifest.json", manifest)
        with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, str(path.relative_to(ROOT)))
    if (manifest["cases"] != cases() or manifest["reference_report_sha256"] != sha(reference/"report.json")
            or manifest["basis_report_sha256"] != sha(basis)
            or manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__):
        raise ValueError("Receding cases/reference/runtime changed")
    invocation_path = output/"invocations.json"
    invocations = json.loads(invocation_path.read_text()) if invocation_path.exists() else []
    if len(invocations) >= PLAN["max_invocations"]:
        raise ValueError("Frozen invocation budget exhausted")
    invocations.append(dict(status="unsealed", started_unix=time.time(), budget_seconds=PLAN["invocation_budget_seconds"]))
    write(invocation_path, invocations)
    started = time.monotonic()
    deadline, anchors = started+PLAN["invocation_budget_seconds"], []
    (output/"anchors").mkdir(exist_ok=True)
    for identifier in ANCHORS:
        case = next(c for c in old_manifest["cases"] if c["case_id"] == identifier)
        for method, old_method in (("mp_all_native", "mp_all_native"), ("window_2s", "window_extension")):
            path = output/"anchors"/f"{identifier}_{method}.json.gz"
            if path.exists():
                with gzip.open(path, "rt") as stream:
                    raw = json.load(stream)
            else:
                raw = rollout_tracks(case, controller(method, case), RunBudget(max(.000001, deadline-time.monotonic())))
                with gzip.open(path, "wt") as stream:
                    json.dump(raw, stream, allow_nan=False)
            previous = load_raw(reference, next(r for r in old_report["rows"] if r["case_id"] == identifier and r["method"] == old_method))
            require_anchor_match({**raw, "method": old_method}, previous)
            anchors.append(dict(case_id=identifier, method=method, old_method=old_method, raw_file=str(path.relative_to(output)), sha256=sha(path)))
    with ProcessPoolExecutor(max_workers=PLAN["processes"], mp_context=multiprocessing.get_context("spawn")) as pool:
        jobs = [pool.submit(case_worker, output, case, deadline, len(invocations)) for case in cases()]
        for job in as_completed(jobs):
            job.result()
    rows = collect_rows(output)
    result = comparison(rows)
    invocations[-1].update(status="finished", elapsed_seconds=time.monotonic()-started)
    write(invocation_path, invocations)
    csv_file(output/"cases.csv", [{k:v for k,v in r.items() if k != "shield"} for r in rows])
    report = dict(complete=result["primary_endpoint_complete"], comparison=result, rows=rows, anchors=anchors,
        publication_ready=False, automatic_promotion=False, previous_screen_changed=False)
    report["output_sha256"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output/"report.json", report)
    return {k:v for k,v in report.items() if k not in ("rows", "anchors", "output_sha256")}


def verify(output):
    manifest = json.loads((output/"manifest.json").read_text())
    report = json.loads((output/"report.json").read_text())
    if not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)) or manifest["cases"] != cases():
        raise ValueError("Incomplete or changed receding study")
    if manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__:
        raise ValueError("Verification requires original runtime")
    files = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file() and p != output/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(output/name) != value for name,value in report["output_sha256"].items()):
        raise ValueError("Receding output hashes/coverage mismatch")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(manifest["source_sha256"]):
            raise ValueError("Receding source archive coverage mismatch")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Historical replay requires archived sources")
    reference = Path(manifest["reference_directory"])
    _, previous = load_reference(reference)
    if sha(reference/"report.json") != manifest["reference_report_sha256"]:
        raise ValueError("Anchor reference changed")
    if sha(Path(manifest["basis_report"])) != manifest["basis_report_sha256"]:
        raise ValueError("Hypothesis diagnostic changed")
    expected_anchors = {(identifier, method) for identifier in ANCHORS for method in ("mp_all_native", "window_2s")}
    if len(report["anchors"]) != 4 or {(a["case_id"], a["method"]) for a in report["anchors"]} != expected_anchors:
        raise ValueError("Missing runtime equivalence anchors")
    for anchor in report["anchors"]:
        if sha(output/anchor["raw_file"]) != anchor["sha256"]:
            raise ValueError("Runtime anchor hash mismatch")
        with gzip.open(output/anchor["raw_file"], "rt") as stream:
            raw = json.load(stream)
        replay_tracks(raw, controller(anchor["method"], raw["case"]))
        old = load_raw(reference, next(r for r in previous["rows"] if r["case_id"] == anchor["case_id"] and r["method"] == anchor["old_method"]))
        require_anchor_match({**raw, "method": anchor["old_method"]}, old)
    rows = collect_rows(output)
    if rows != report["rows"] or comparison(rows) != report["comparison"]:
        raise ValueError("Receding summary/screen reconstruction mismatch")
    if not csv_matches(output/"cases.csv", [{k:v for k,v in row.items() if k != "shield"} for row in rows]):
        raise ValueError("Receding CSV reconstruction mismatch")
    frames = 0
    for row in rows:
        with gzip.open(output/row["raw_file"], "rt") as stream:
            raw = json.load(stream)
        replay_tracks(raw, controller(row["method"], raw["case"]))
        frames += len(raw["frames"])
    if report["publication_ready"] or report["automatic_promotion"] or report["previous_screen_changed"]:
        raise ValueError("Incorrect promotion/scope flags")
    return dict(verified=True, runs=len(rows), semantic_anchor_replays=4, recorded_frames_replayed=frames+4800,
        verification_new_traffic_reruns=0, continue_to_fresh_development=report["comparison"]["continue_to_fresh_development"], publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--resume", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--basis", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
    elif args.resume:
        manifest = json.loads((args.resume/"manifest.json").read_text())
        result = run(Path(manifest["reference_directory"]), args.resume, resume=True)
    else:
        if not args.reference or not args.basis:
            parser.error("Creation requires --reference anchors and --basis diagnostic report")
        result = run(args.reference, args.output, basis=args.basis)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
