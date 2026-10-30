"""Saved-trace diagnosis and the missing all-visible pressure cadence control."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np

from research.analysis.arrival_reference_gap import analyze_run
from research.observation.arrival_tracks import TrackSensor, TrackFaults, Track, Packet
from research.pilots import run_arrival_window_panel as panel
from research.policies.arrival_extension import ArrivalExtension, Timing
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import RunBudget, BudgetExceeded
from server.app.simulation.traffic_signal import TrafficSignal

ROOT, sha, write = panel.ROOT, panel.sha, panel.write
ANCHORS = ("train_ew_asymmetric_01_clean_tracks", "train_mod_balanced_01_intermittent_tracks")
PLAN = dict(schema_version="arrival_reference_gap_v1", max_wall_seconds=120,
    premise="The closed prototype's gap to native all-visible pressure may involve decision cadence, reference choices or service assumptions; quantify these before proposing another learning change.",
    trace_scope="All18 saved primary trajectories. Same delivered states: native all/upstream pressure, fresh primary, actual cached primary, age-gated/ungated references. Counts are descriptive/nonindependent, not causal traffic savings.",
    service_scope="Every support ID at all27 saved extension gates. Future pre-corruption captures score actual stop-line discharge during the chosen2s hold only. Already-postline/missing/censored observations remain explicit; no future data enter reconstructed decisions.",
    control="All18 consumed cases: all-visible pressure at2s cadence. Same counts, score, faults, seed, shield, physical FSM and metrics as original native all-visible pressure. No parameter fitting, candidate changes or test-set access.",
    anchors=ANCHORS, anchor_selection="First clean source case plus the previously documented worst primary case; both are mechanics replay anchors, not fresh or favorable-selected confirmation.",
    arithmetic="Report the two-by-two visible-count semantics/native-vs2s cadence table. Decompose primary-native mean gap algebraically into primary-matched and matched-native; interaction does not identify the effect of changing the primary's cadence.",
    completion="Both native replay anchors match full semantic bundles exactly; all18 new matched controls complete, paired requested arrivals and zero measured violations. No performance promotion gate is introduced.",
    no_training=True, original_screen_changed=False, policy_promoted=False, publication_ready=False)


class AllVisiblePressure(ArrivalExtension):
    """Unchanged pressure rule, with only its post-decision cache interval changed."""
    def __init__(self, timing, cadence_ticks):
        if cadence_ticks not in (1, 20):
            raise ValueError("Cadence audit supports only the declared native and two-second controls")
        super().__init__("mp_all_native", timing)
        self.cadence_ticks = cadence_ticks

    def act(self, state, context):
        proposal = super().act(state, context)
        if self.diagnostics["gate"]:
            self.next_decision = context.timestep+self.cadence_ticks
        return proposal


def csv_file(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def csv_matches(path, rows):
    if not rows:
        return path.read_text() == ""
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        actual, fields = list(reader), reader.fieldnames
    expected = [{key: "" if value is None else str(value) for key, value in row.items()} for row in rows]
    return fields == list(rows[0]) and actual == expected


def load_reference(source):
    manifest = json.loads((source/"manifest.json").read_text())
    report = json.loads((source/"report.json").read_text())
    if manifest["plan"] != json.loads(json.dumps(panel.PLAN)) or report["smoke"] or not report["complete"]:
        raise ValueError("Reference must be the completed frozen arrival-window panel")
    if manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__:
        raise ValueError("Reference control replay requires the original runtime")
    files = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file() and p != source/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(source/name) != value for name, value in report["output_sha256"].items()):
        raise ValueError("Reference output hashes/coverage changed")
    for name, expected in manifest["source_sha256"].items():
        if sha(ROOT/name) != expected:
            raise ValueError("Reference analysis requires original executable sources")
    rows = panel.collect_rows(source, manifest["cases"], manifest["methods"])
    if rows != report["rows"] or panel.compare(rows, manifest["cases"], manifest["methods"]) != report["comparison"]:
        raise ValueError("Reference raw summary does not reproduce")
    if manifest["cases"] != panel.panel_cases():
        raise ValueError("Reference case definitions changed")
    return manifest, report


def load_raw(source, row):
    with gzip.open(source/row["raw_file"], "rt") as stream:
        return json.load(stream)


def require_anchor_match(live, saved):
    # Compare the complete serialized value, preserving floats exactly. Frozen
    # packet tuples become JSON arrays; this is not a traffic/state difference.
    if json.loads(json.dumps(live, allow_nan=False)) != saved:
        raise ValueError("Native anchor does not exactly reproduce the frozen full semantic bundle")


def trace_analysis(source, reference):
    analyses = [analyze_run(load_raw(source, row)) for row in reference["rows"] if row["method"] == "window_extension"]
    cases = [dict(case_id=a["case_id"], **a["counts"]) for a in analyses]
    services = [w for a in analyses for w in a["service_witnesses"]]
    disagreements = [dict(case_id=a["case_id"], **d) for a in analyses for d in a["disagreements"]]
    counts = {key: sum(a["counts"][key] for a in analyses) for key in analyses[0]["counts"]}
    status = dict(Counter(w["status"] for w in services))
    return analyses, cases, services, disagreements, dict(same_state=counts, service_status=status,
        service_claims=len(services), evaluation_speed_exceeds_interval=sum(w["evaluation_speed_exceeds_estimated_upper"] for w in services),
        service_claims_with_unobserved_leaders=sum(bool(w["evaluation_unobserved_leaders"]) for w in services))


def rollout(case, cadence_ticks, budget):
    """Explicit audit loop; native anchors test equivalence to the frozen runner."""
    scenario = ScenarioConfig.from_dict(case["scenario"])
    env, profile = panel.build_environment(scenario)
    env.reset(seed=case["seed"])
    timing = Timing(all_red=scenario.red_duration)
    sensor = TrackSensor(panel.CALIBRATION, TrackFaults(**case["fault"]), case["seed"]+90000)
    controller, protection, audit = AllVisiblePressure(timing, cadence_ticks), panel.shield(timing), panel.SignalAudit()
    waits, frames, arrivals = dict.fromkeys(range(4), 0.), [], hashlib.sha256()
    gates = 0
    for step in range(scenario.duration_steps):
        budget.check("matched pressure cadence control")
        panel.apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        state = sensor.observe(env.intersection, step)
        before = panel.feedback(env.intersection.signal)
        context, waits = panel.build_context(state, before, step, waits, timing)
        proposal = controller.act(state, context)
        decision = protection.filter_context(proposal, context)
        env.step(decision.executed_action)
        signal = env.intersection.signal
        audit.observe((before["phase"], before["color"], before["age"]), signal)
        generated = env.intersection.spawner.generated_movements_last_tick
        arrivals.update(json.dumps([step, generated]).encode())
        gates += int(controller.diagnostics["gate"])
        frames.append(dict(step=step, capture=[asdict(t) for t in sensor.last_snapshot], packet=state.packet.to_dict(),
            before=before, after=panel.feedback(signal), proposed=proposal, executed=decision.executed_action,
            policy=controller.diagnostics.copy(), shield=decision.to_dict(), generated=generated))
    population = dict(completed=list(env.intersection.completed_wait_times),
        active=[v.wait_time for queue in env.intersection.lanes.values() for v in queue if v.state != "passed"],
        backlog=env.intersection.spawner.get_backlog_waits())
    values = [v for category in population.values() for v in category]
    metrics = panel.wait_metrics(values, env.intersection.total_passed, env.intersection.total_spawned)
    if not panel.math_close(metrics["delay"], env.intersection.get_avg_wait_time()):
        raise ValueError("Audit delay disagrees with simulator")
    result = dict(**metrics, samples=audit.samples, violations=audit.conflicts+audit.clearance_violations,
        signal_conflicts=audit.conflicts, clearance_violations=audit.clearance_violations,
        arrival_trace_hash=arrivals.hexdigest(), policy_gates=gates, extension_proposals=0,
        shield=protection.get_audit_metrics())
    return dict(case=case, method="mp_all_native" if cadence_ticks == 1 else "mp_all_2s",
                result=result, wait_population=population, frames=frames)


def control_summary(reference, controls):
    if len(controls) != 18:
        return None
    table = {name: panel.means([r for r in reference["rows"] if r["method"] == name])
             for name in ("mp_all_native", "mp_upstream_native", "mp_upstream_2s", "window_extension")}
    table["mp_all_2s"] = panel.means(controls)
    primary, native, matched = (table[name]["delay"] for name in ("window_extension", "mp_all_native", "mp_all_2s"))
    return dict(means=table, delay_gap_seconds=dict(primary_minus_native=primary-native,
        primary_minus_matched=primary-matched, all_visible_cadence_cost=matched-native,
        upstream_cadence_cost=table["mp_upstream_2s"]["delay"]-table["mp_upstream_native"]["delay"],
        cadence_by_count_semantics_interaction=(matched-native)-(table["mp_upstream_2s"]["delay"]-table["mp_upstream_native"]["delay"])),
        interpretation="Algebraic reference-gap decomposition and a controlled classical cadence comparison. It does not estimate the effect of changing the prototype cadence or prove useful missing information.")


def run(source, output):
    source, output = source.resolve(), output.resolve()
    reference_manifest, reference = load_reference(source)
    if subprocess.check_output(["git", "status", "--porcelain", "--", "research", "server/app"], cwd=ROOT, text=True).strip():
        raise ValueError("Commit executable audit sources before collecting controls")
    output.mkdir(parents=True, exist_ok=False)
    (output/"raw").mkdir()
    paths = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    manifest = dict(plan=PLAN, source_directory=str(source), source_report_sha256=sha(source/"report.json"),
        source_manifest_sha256=sha(source/"manifest.json"), cases=reference_manifest["cases"], python_version=sys.version,
        numpy_version=np.__version__, git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths})
    write(output/"manifest.json", manifest)
    with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, str(path.relative_to(ROOT)))
    budget = RunBudget(120)
    analyses, cases, services, disagreements, trace = trace_analysis(source, reference)
    write(output/"trace_analysis.json", analyses)
    csv_file(output/"same_state_cases.csv", cases)
    csv_file(output/"service_witnesses.csv", services)
    csv_file(output/"disagreement_ticks.csv", disagreements)
    controls, anchors = [], []
    reason = "completed"
    try:
        for case_id in ANCHORS:
            case = next(c for c in manifest["cases"] if c["case_id"] == case_id)
            raw = rollout(case, 1, budget)
            old = load_raw(source, next(r for r in reference["rows"] if r["case_id"] == case_id and r["method"] == "mp_all_native"))
            require_anchor_match(raw, old)
            path = output/"raw"/f"anchor_{case_id}.json.gz"
            with gzip.open(path, "wt") as stream:
                json.dump(raw, stream, allow_nan=False)
            anchors.append(dict(case_id=case_id, exact=True, raw_file=str(path.relative_to(output)), sha256=sha(path)))
        for case in manifest["cases"]:
            raw = rollout(case, 20, budget)
            path = output/"raw"/f"matched_{case['case_id']}.json.gz"
            with gzip.open(path, "wt") as stream:
                json.dump(raw, stream, allow_nan=False)
            old = next(r for r in reference["rows"] if r["case_id"] == case["case_id"] and r["method"] == "mp_all_native")
            if raw["result"]["arrival_trace_hash"] != old["arrival_trace_hash"]:
                raise ValueError("Unpaired requested arrivals in matched control")
            controls.append(dict(case_id=case["case_id"], **raw["result"], raw_file=str(path.relative_to(output)), sha256=sha(path)))
            print(f"Completed matched cadence: {case['case_id']}", flush=True)
    except BudgetExceeded:
        reason = "budget_exceeded"
    csv_file(output/"matched_control_cases.csv", [{key: value for key, value in r.items() if key != "shield"} for r in controls])
    checks = dict(native_anchors_exact=len(anchors) == 2 and all(a["exact"] for a in anchors),
        all_matched_controls=len(controls) == 18,
        full_control_samples=all(r["samples"] == 1200 for r in controls),
        no_measured_control_violations=all(r["violations"] == 0 for r in controls))
    report = dict(complete=len(anchors) == 2 and len(controls) == 18, stop_reason=reason, trace_diagnosis=trace,
        controls=controls, anchors=anchors, control_comparison=control_summary(reference, controls),
        checks=checks, audit_integrity_passed=all(checks.values()),
        elapsed_seconds=budget.elapsed, new_control_rollouts=len(controls), deterministic_anchor_replays=len(anchors),
        original_screen_changed=False, policy_promoted=False, publication_ready=False,
        reused_development_cases=True, reference_checks="Sealed hashes, original sources/cases and raw summary reconstruction; full original216000-frame replay was already recorded by the original verifier.")
    report["output_sha256"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output/"report.json", report)
    return {key: value for key, value in report.items() if key not in ("controls", "anchors", "output_sha256")}


def verify_bundle(raw, cadence_ticks):
    if raw["method"] != ("mp_all_native" if cadence_ticks == 1 else "mp_all_2s"):
        raise ValueError("Wrong control-method label")
    timing = Timing(all_red=raw["case"]["scenario"]["red_duration"])
    sensor = TrackSensor(panel.CALIBRATION, TrackFaults(**raw["case"]["fault"]), raw["case"]["seed"]+90000)
    controller, protection, audit = AllVisiblePressure(timing, cadence_ticks), panel.shield(timing), panel.SignalAudit()
    signal = TrafficSignal(red_duration=timing.all_red)
    waits, arrivals, gates = dict.fromkeys(range(4), 0.), hashlib.sha256(), 0
    if len(raw["frames"]) != 1200:
        raise ValueError("Incomplete control trace")
    for step, frame in enumerate(raw["frames"]):
        if frame["step"] != step or panel.feedback(signal) != frame["before"]:
            raise ValueError("Control signal coverage mismatch")
        state = sensor.replay(tuple(Track(**t) for t in frame["capture"]), step)
        if state.packet != Packet.parse(frame["packet"]):
            raise ValueError("Control packet replay mismatch")
        context, waits = panel.build_context(state, frame["before"], step, waits, timing)
        proposed = controller.act(state, context)
        decision = protection.filter_context(proposed, context)
        if (proposed != frame["proposed"] or controller.diagnostics != frame["policy"] or
                decision.to_dict() != frame["shield"] or decision.executed_action != frame["executed"]):
            raise ValueError("Control proposal/shield replay mismatch")
        before = panel.feedback(signal)
        signal.tick(.1, lanes=None, requested_phase=decision.executed_action)
        if panel.feedback(signal) != frame["after"]:
            raise ValueError("Control lamp replay mismatch")
        audit.observe((before["phase"], before["color"], before["age"]), signal)
        arrivals.update(json.dumps([step, frame["generated"]]).encode())
        gates += int(controller.diagnostics["gate"])
    result, population = raw["result"], raw["wait_population"]
    if len(population["completed"]) != result["passed"]:
        raise ValueError("Control trip counter mismatch")
    metrics = panel.wait_metrics([v for values in population.values() for v in values], result["passed"], result["arrivals"])
    if (any(result[k] != value for k, value in metrics.items()) or result["samples"] != audit.samples
            or result["violations"] != audit.conflicts+audit.clearance_violations
            or result["signal_conflicts"] != audit.conflicts or result["clearance_violations"] != audit.clearance_violations
            or result["arrival_trace_hash"] != arrivals.hexdigest() or result["policy_gates"] != gates
            or result["shield"] != protection.get_audit_metrics() or result["extension_proposals"] != 0):
        raise ValueError("Control metrics/counters do not reconstruct")


def verify(output):
    manifest = json.loads((output/"manifest.json").read_text())
    report = json.loads((output/"report.json").read_text())
    if not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)):
        raise ValueError("Incomplete diagnostic or changed protocol")
    if manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__:
        raise ValueError("Verification requires the original runtime")
    files = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file() and p != output/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(output/p) != value for p, value in report["output_sha256"].items()):
        raise ValueError("Diagnostic output hashes/coverage mismatch")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(manifest["source_sha256"]):
            raise ValueError("Diagnostic source archive coverage mismatch")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Historical audit requires archived executable sources")
    source = Path(manifest["source_directory"])
    old_manifest, reference = load_reference(source)
    if sha(source/"report.json") != manifest["source_report_sha256"] or sha(source/"manifest.json") != manifest["source_manifest_sha256"] or manifest["cases"] != old_manifest["cases"]:
        raise ValueError("Reference provenance changed")
    analyses, cases, services, disagreements, trace = trace_analysis(source, reference)
    if analyses != json.loads((output/"trace_analysis.json").read_text()) or trace != report["trace_diagnosis"]:
        raise ValueError("Saved-trace diagnosis does not reproduce")
    for name, expected in (("same_state_cases.csv", cases), ("service_witnesses.csv", services),
                           ("disagreement_ticks.csv", disagreements),
                           ("matched_control_cases.csv", [{k:v for k,v in r.items() if k != "shield"} for r in report["controls"]])):
        if not csv_matches(output/name, expected):
            raise ValueError("Derived diagnostic CSV does not reconstruct")
    if len(report["anchors"]) != 2 or {r["case_id"] for r in report["anchors"]} != set(ANCHORS):
        raise ValueError("Missing native anchor")
    if len(report["controls"]) != 18 or {r["case_id"] for r in report["controls"]} != {c["case_id"] for c in manifest["cases"]}:
        raise ValueError("Missing matched control")
    for role, records, cadence in (("anchor", report["anchors"], 1), ("control", report["controls"], 20)):
        for record in records:
            if sha(output/record["raw_file"]) != record["sha256"]:
                raise ValueError("Diagnostic raw bundle changed")
            with gzip.open(output/record["raw_file"], "rt") as stream:
                raw = json.load(stream)
            expected_case = next(c for c in manifest["cases"] if c["case_id"] == record["case_id"])
            if raw["case"] != expected_case:
                raise ValueError("Diagnostic case mismatch")
            verify_bundle(raw, cadence)
            old = next(r for r in reference["rows"] if r["case_id"] == record["case_id"] and r["method"] == "mp_all_native")
            if role == "anchor":
                if raw != load_raw(source, old) or record["exact"] is not True:
                    raise ValueError("Native anchor differs")
            elif any(record[key] != value for key, value in raw["result"].items()) or record["arrival_trace_hash"] != old["arrival_trace_hash"]:
                raise ValueError("Matched result/arrival summary mismatch")
    if report["control_comparison"] != control_summary(reference, report["controls"]):
        raise ValueError("Controlled cadence comparison changed")
    checks = dict(native_anchors_exact=True, all_matched_controls=True,
        full_control_samples=all(r["samples"] == 1200 for r in report["controls"]),
        no_measured_control_violations=all(r["violations"] == 0 for r in report["controls"]))
    if report["checks"] != checks or report["audit_integrity_passed"] != all(checks.values()):
        raise ValueError("Diagnostic integrity flags do not reconstruct")
    if (report["new_control_rollouts"] != 18 or report["deterministic_anchor_replays"] != 2
            or report["original_screen_changed"] or report["policy_promoted"] or report["publication_ready"]):
        raise ValueError("Incorrect scope/completion flags")
    return dict(verified=True, primary_runs_analyzed=18, new_control_rollouts=18, deterministic_anchor_replays=2,
        new_control_frames_replayed=24000, verification_new_traffic_reruns=0, original_screen_changed=False,
        policy_promoted=False, publication_ready=False, trace_diagnosis=trace, control_comparison=report["control_comparison"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original panel, or this audit directory with --verify")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if args.output:
            parser.error("Verification cannot create output")
        result = verify(args.source)
    else:
        if not args.output:
            parser.error("Creation requires a new --output directory")
        result = run(args.source, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
