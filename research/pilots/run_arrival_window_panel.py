"""Bounded full-episode headroom test for a causal arrival-extension prototype."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import statistics
import subprocess
import sys
import time
import zipfile

import numpy as np

from research.experiments.runtime import SignalAudit, apply_scenario_step, build_environment
from research.observation.arrival_tracks import Calibration, Track, Packet, TrackSensor, TrackFaults
from research.pilots.run_switch_margin_pilot import ROOT, sha, write
from research.policies.arrival_extension import ArrivalExtension, Timing, METHODS
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import RunBudget, BudgetExceeded, load_split
from server.app.controllers.base import ControllerContext
from server.app.controllers.max_pressure import PHASE_MOVEMENTS
from server.app.controllers.safety_shield import SafetyShield
from server.app.simulation.traffic_signal import TrafficSignal

CALIBRATION = Calibration(dedicated_movement_lanes=True)
FAULTS = (TrackFaults(), TrackFaults(name="delayed_tracks", latency_ticks=2),
          TrackFaults(name="intermittent_tracks", miss_rate=.1, latency_ticks=3,
                      frame_drop_probability=.2, position_error=.002))
PRIMARY = "window_extension"
PLAN = dict(schema_version="arrival_window_headroom_v1", invocation_budget_seconds=300, max_invocations=2, processes=3,
    hypothesis="A source-time-aware kinematic service prefix can improve full-run control beyond a pressure/Advanced-MP reference and its identical freshness gate.",
    architecture="Unified synthetic delivered tracks -> causal position-history motion -> age-gated Advanced-MP reference -> optional two-second extension -> unchanged shield -> unchanged physical FSM.",
    calibration=asdict(CALIBRATION), distance_units="normalized_path_not_metres", methods=METHODS,
    faults=[asdict(f) for f in FAULTS], seeds=[1341001+i for i in range(6)],
    panel="Six existing train templates, one new traffic seed each, three sensing conditions, 1200ticks:18 cases x10 methods=180 full episodes. No validation/test access or fitting.",
    observation="Dedicated observable movement lanes are a declared synthetic calibration assumption. Capture only normalized positions, lane labels and session-remapped IDs. Never simulator velocity/state/wait/turn/future/backlog. Derive every count and motion feature from the same delayed/corrupted packet.",
    motion="Position-error engineering bound0.002, history0.4..1s. Distinct advancing source frames only; stopped/unknown/gap/implausible motion stays explicit. No calibrated actual-crossing interval claim.",
    policy="Age-gated Advanced-MP weight2 reference. Current green may extend2s if its known-moving serviceable leading prefix has positive kinematic release windows within2s and earliest-return proxy exceeds2s*all competing visible upstream demand plus1 vehicle-second. Stopped/unknown/possibly departed leaders block follower support. Stale>0.5s, maximum-green and phase-service guards abstain.",
    timing="Shared min-green8s,yellow2s,scenario all-red,max-green40s,phase-service45s. Earliest return computed with a fresh local TrafficSignal and no lanes/RNG. All real methods shielded at10Hz; native references act10Hz, others hold2s.",
    baselines="Clipped MP on all-visible counts/native cadence; upstream-only MP/native and2s; paper-labelled Advanced-MP adaptation weights1/2/4; identical age-gated Advanced-MP; point-time and age-ignored extension ablations.",
    primary_endpoint="All18 complete cases for the predefined window_extension. No selecting a method, traffic seed, condition or checkpoint.",
    screen="Primary >=2% aggregate delay gain vs each of7 classical references; >=1% vs point and no-age ablations. No aggregate p95/throughput loss vs all9 references; no case >5% delay loss vs any reference. Clean mean/p95<=1% loss and no throughput loss vs age-gated reference. Paired requested arrivals, complete immutable outputs, zero measured signal violations.",
    recovery="Atomic per-method full-episode bundles; identical-source --resume can reuse completed episodes in a new invocation, at most2 invocations. Unsealed partial executions are not samples. Budget timing reported per invocation; no automatic rerun or threshold change.",
    novelty="Unestablished. Arrival-aware pressure, green extension, information age, switching costs and robust/reference MPC already exist; this is a narrowly tested integration/empirical hypothesis.",
    references=["https://arxiv.org/abs/2112.10107", "https://xingminw.github.io/publication/2022-max-pressure/",
        "https://biblio.ugent.be/publication/01J8QHQCP55ECXP43A61ABGAAX", "https://arxiv.org/abs/2610.32290",
        "https://rosap.ntl.bts.gov/view/dot/54566/dot_54566_DS1.pdf",
        "https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/final-reports/ca13-2157a-finalreport-a11y.pdf"],
    no_training=True, automatic_promotion=False, publication_ready=False)


def panel_cases(smoke=False):
    templates = load_split("train")
    if len(templates) != 6 or any(s.duration_steps != 1200 for s in templates):
        raise ValueError("Unexpected training panel")
    return [dict(case_id=f"{scenario.scenario_id}_{fault.name}", scenario=scenario.to_dict(),
                 seed=(1340901 if smoke else 1341001+i), fault=asdict(fault))
            for i, scenario in enumerate(templates[:1] if smoke else templates)
            for fault in (FAULTS[-1:] if smoke else FAULTS)]


def feedback(signal):
    return dict(phase=signal.current_phase, color=signal.color.name, age=signal.time_in_phase)


def build_context(state, signal, step, waits, timing):
    counts = state.counts("upstream")
    can_switch = signal["color"] == "GREEN" and signal["age"] >= timing.min_green
    mask = np.zeros(4, dtype=bool)
    mask[signal["phase"]] = True
    updated = {}
    for phase, movements in PHASE_MOVEMENTS.items():
        demand = sum(counts[m] for m in movements) > 0
        served = signal["color"] == "GREEN" and signal["phase"] == phase
        updated[phase] = waits[phase]+.1 if demand and not served else 0.
        if can_switch and demand:
            mask[phase] = True
    return ControllerContext(timestep=step, current_phase=signal["phase"], time_in_phase=signal["age"],
        color=signal["color"], can_switch_phase=can_switch, is_decision_step=can_switch,
        valid_action_mask=mask, movement_queues=counts, outgoing_counts=state.outgoing(),
        phase_starvation_times=updated.copy(), extra_telemetry={"track_source_tick":state.packet.source_tick}), updated


def shield(timing):
    return SafetyShield(min_green_time=timing.min_green, max_green_time=timing.max_green,
        yellow_duration=timing.yellow, red_duration=timing.all_red, starvation_threshold=timing.starvation)


def wait_metrics(waits, passed, generated):
    if type(passed) is not int or type(generated) is not int or not 0 <= passed <= generated or len(waits) != generated:
        raise ValueError("Completed/active/backlog wait population does not conserve generated vehicles")
    return dict(delay=float(np.mean(waits)) if waits else 0., p95=float(np.percentile(waits, 95)) if waits else 0.,
                passed=passed, arrivals=generated)


def rollout(case, method, budget):
    scenario = ScenarioConfig.from_dict(case["scenario"])
    env, profile = build_environment(scenario)
    env.reset(seed=case["seed"])
    timing = Timing(all_red=scenario.red_duration)
    sensor = TrackSensor(CALIBRATION, TrackFaults(**case["fault"]), case["seed"]+90000)
    controller, protection, audit = ArrivalExtension(method, timing), shield(timing), SignalAudit()
    waits, frames, arrivals = dict.fromkeys(range(4), 0.), [], hashlib.sha256()
    extensions = gates = 0
    for step in range(scenario.duration_steps):
        budget.check("arrival-window full episode")
        apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        state = sensor.observe(env.intersection, step)
        before = feedback(env.intersection.signal)
        context, waits = build_context(state, before, step, waits, timing)
        proposal = controller.act(state, context)
        decision = protection.filter_context(proposal, context)
        _, _, _, _, _ = env.step(decision.executed_action)
        signal = env.intersection.signal
        audit.observe((before["phase"], before["color"], before["age"]), signal)
        generated = env.intersection.spawner.generated_movements_last_tick
        arrivals.update(json.dumps([step, generated]).encode())
        gates += int(controller.diagnostics["gate"])
        extensions += int(controller.diagnostics.get("reason") == "supported_extension")
        frames.append(dict(step=step, capture=[asdict(t) for t in sensor.last_snapshot], packet=state.packet.to_dict(),
            before=before, after=feedback(signal), proposed=proposal, executed=decision.executed_action,
            policy=controller.diagnostics.copy(), shield=decision.to_dict(), generated=generated))
    population = dict(completed=list(env.intersection.completed_wait_times),
        active=[v.wait_time for queue in env.intersection.lanes.values() for v in queue if v.state != "passed"],
        backlog=env.intersection.spawner.get_backlog_waits())
    all_waits = [value for category in population.values() for value in category]
    metrics = wait_metrics(all_waits, env.intersection.total_passed, env.intersection.total_spawned)
    if not math_close(metrics["delay"], env.intersection.get_avg_wait_time()):
        raise ValueError("Delay metric disagrees with the shared simulator")
    result = dict(**metrics, samples=audit.samples, violations=audit.conflicts+audit.clearance_violations,
        signal_conflicts=audit.conflicts, clearance_violations=audit.clearance_violations,
        arrival_trace_hash=arrivals.hexdigest(), policy_gates=gates, extension_proposals=extensions,
        shield=protection.get_audit_metrics())
    return dict(case=case, method=method, result=result, wait_population=population, frames=frames)


def math_close(first, second):
    return abs(first-second) <= 1e-8*max(1., abs(first), abs(second))


def case_worker(output, case, methods, deadline, invocation):
    directory = output/case["case_id"]
    directory.mkdir(exist_ok=True)
    budget = RunBudget(max(.000001, deadline-time.monotonic()))
    for method in methods:
        target = directory/f"{method}.json.gz"
        if target.exists():
            continue
        try:
            raw = rollout(case, method, budget)
        except BudgetExceeded:
            return
        partial = directory/f"{method}.invocation_{invocation}.partial.gz"
        with gzip.open(partial, "wt") as stream:
            json.dump(raw, stream, allow_nan=False)
        partial.replace(target)
    print(f"Completed arrival case: {case['case_id']}", flush=True)


def means(rows):
    return {key: statistics.mean(row[key] for row in rows) for key in ("delay", "p95", "passed")}


def compare(rows, cases, methods=METHODS, *, mechanics_only=False):
    expected = {(case["case_id"], method) for case in cases for method in methods}
    if len(rows) != len(expected) or {(r["case_id"], r["method"]) for r in rows} != expected:
        return dict(primary_endpoint_complete=False, continue_to_fresh_development=False)
    group = {method: [r for r in rows if r["method"] == method] for method in methods}
    summary = {method: means(selected) for method, selected in group.items()}
    audit_checks = dict(paired_arrivals=all(len({r["arrival_trace_hash"] for r in rows if r["case_id"] == c["case_id"]}) == 1 for c in cases),
                       signal_audit=all(r["samples"] == 1200 and r["violations"] == 0 for r in rows))
    if mechanics_only:
        return dict(primary_endpoint_complete=True, mechanics_only=True, means=summary, checks=audit_checks,
                    mechanics_pass=all(audit_checks.values()), continue_to_fresh_development=False)
    checks = {}
    primary = summary[PRIMARY]
    for method in methods:
        if method == PRIMARY:
            continue
        reference = summary[method]
        gain = .01 if method in ("point_extension", "no_age_extension") else .02
        checks[f"delay_gain_vs_{method}"] = primary["delay"] <= (1-gain)*reference["delay"]
        checks[f"p95_vs_{method}"] = primary["p95"] <= reference["p95"]
        checks[f"throughput_vs_{method}"] = primary["passed"] >= reference["passed"]
        checks[f"no_case_over_five_percent_loss_vs_{method}"] = all(
            candidate["delay"] <= 1.05*next(r["delay"] for r in group[method] if r["case_id"] == candidate["case_id"])
            for candidate in group[PRIMARY])
    clean_ids = {c["case_id"] for c in cases if c["fault"]["name"] == "clean_tracks"}
    if clean_ids:
        candidate = means([r for r in group[PRIMARY] if r["case_id"] in clean_ids])
        reference = means([r for r in group["age_gated_advanced_mp"] if r["case_id"] in clean_ids])
        checks.update(clean_delay=candidate["delay"] <= 1.01*reference["delay"],
                      clean_p95=candidate["p95"] <= 1.01*reference["p95"], clean_throughput=candidate["passed"] >= reference["passed"])
    checks.update(audit_checks)
    return dict(primary_endpoint_complete=True, means=summary, checks=checks, continue_to_fresh_development=all(checks.values()))


def collect_rows(output, cases, methods):
    rows = []
    for case in cases:
        for method in methods:
            path = output/case["case_id"]/f"{method}.json.gz"
            if not path.exists():
                continue
            with gzip.open(path, "rt") as stream:
                raw = json.load(stream)
            if raw["case"] != case or raw["method"] != method:
                raise ValueError("Existing bundle does not match the frozen case/method")
            rows.append(dict(case_id=case["case_id"], method=method, **raw["result"],
                             raw_file=str(path.relative_to(output)), raw_sha256=sha(path)))
    return rows


def run(output, *, smoke=False, resume=False):
    output = output.resolve()
    cases = panel_cases(smoke)
    methods = ("mp_upstream_2s", "age_gated_advanced_mp", "point_extension", "window_extension") if smoke else METHODS
    if resume:
        manifest = json.loads((output/"manifest.json").read_text())
        if manifest["smoke"] != smoke or manifest["plan"] != json.loads(json.dumps(PLAN)):
            raise ValueError("Resume requires identical frozen protocol and mode")
        if (output/"report.json").exists():
            raise ValueError("A sealed panel cannot be resumed or rerun")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected:
                raise ValueError("Resume requires the archived executable source")
    else:
        if not smoke and subprocess.check_output(["git", "status", "--porcelain", "--", "research", "server/app"], cwd=ROOT, text=True).strip():
            raise ValueError("Commit research executable source before collecting performance outcomes")
        output.mkdir(parents=True, exist_ok=False)
        paths = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
        manifest = dict(plan=PLAN, smoke=smoke, cases=cases, methods=methods, python_version=sys.version,
            numpy_version=np.__version__, git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths})
        write(output/"manifest.json", manifest)
        with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, str(path.relative_to(ROOT)))
    if manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__:
        raise ValueError("Resume requires original runtime")
    invocations_path = output/"invocations.json"
    invocations = json.loads(invocations_path.read_text()) if invocations_path.exists() else []
    if len(invocations) >= PLAN["max_invocations"]:
        raise ValueError("Frozen invocation limit exhausted")
    invocation = len(invocations)+1
    invocations.append(dict(invocation=invocation, status="unsealed", unix_started=time.time(),
                            budget_seconds=60 if smoke else 300))
    write(invocations_path, invocations)
    started = time.monotonic()
    deadline = started+(60 if smoke else 300)
    if smoke:
        for case in cases:
            case_worker(output, case, methods, deadline, invocation)
    else:
        with ProcessPoolExecutor(max_workers=3, mp_context=multiprocessing.get_context("spawn")) as pool:
            jobs = [pool.submit(case_worker, output, case, methods, deadline, invocation) for case in cases]
            for job in as_completed(jobs):
                job.result()
    rows = collect_rows(output, cases, methods)
    comparison = compare(rows, cases, methods, mechanics_only=smoke)
    invocations[-1].update(status="finished", elapsed_seconds=time.monotonic()-started)
    write(invocations_path, invocations)
    report = dict(smoke=smoke, complete=comparison["primary_endpoint_complete"], rows=rows, comparison=comparison,
        publication_ready=False, automatic_promotion=False,
        continue_to_fresh_development=not smoke and comparison["continue_to_fresh_development"])
    report["output_sha256"] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    write(output/"report.json", report)
    return {k: v for k, v in report.items() if k not in ("rows", "output_sha256")}


def verify(output):
    manifest = json.loads((output/"manifest.json").read_text())
    report = json.loads((output/"report.json").read_text())
    if not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)):
        raise ValueError("Incomplete panel or changed frozen protocol")
    expected_methods = ["mp_upstream_2s", "age_gated_advanced_mp", "point_extension", "window_extension"] if manifest["smoke"] else list(METHODS)
    if (manifest["methods"] != expected_methods or report["smoke"] != manifest["smoke"]
            or report["publication_ready"] or report["automatic_promotion"]
            or report["continue_to_fresh_development"] != (not report["smoke"] and report["comparison"]["continue_to_fresh_development"])):
        raise ValueError("Incorrect study mode, methods or promotion flags")
    if manifest["python_version"] != sys.version or manifest["numpy_version"] != np.__version__:
        raise ValueError("Verification requires original runtime")
    files = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file() and p != output/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(output/p) != value for p, value in report["output_sha256"].items()):
        raise ValueError("Output hash/coverage mismatch")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(manifest["source_sha256"]):
            raise ValueError("Archived source coverage mismatch")
        for name, expected in manifest["source_sha256"].items():
            if sha(ROOT/name) != expected or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Historical verification requires archived sources")
    if manifest["cases"] != panel_cases(manifest["smoke"]):
        raise ValueError("Changed case plan")
    rows = collect_rows(output, manifest["cases"], manifest["methods"])
    if rows != report["rows"] or compare(rows, manifest["cases"], manifest["methods"], mechanics_only=manifest["smoke"]) != report["comparison"]:
        raise ValueError("Raw summary/screen reconstruction differs")
    frame_count = 0
    for row in rows:
        with gzip.open(output/row["raw_file"], "rt") as stream:
            raw = json.load(stream)
        case = raw["case"]
        sensor = TrackSensor(CALIBRATION, TrackFaults(**case["fault"]), case["seed"]+90000)
        timing = Timing(all_red=case["scenario"]["red_duration"])
        controller, protection, audit = ArrivalExtension(raw["method"], timing), shield(timing), SignalAudit()
        physical = TrafficSignal(red_duration=timing.all_red)
        waits, arrivals = dict.fromkeys(range(4), 0.), hashlib.sha256()
        extensions = gates = 0
        if len(raw["frames"]) != 1200:
            raise ValueError("Incomplete 10Hz packet/signal trace")
        for step, frame in enumerate(raw["frames"]):
            if frame["step"] != step or feedback(physical) != frame["before"]:
                raise ValueError("Physical trace continuity mismatch")
            state = sensor.replay(tuple(Track(**t) for t in frame["capture"]), step)
            if state.packet != Packet.parse(frame["packet"]):
                raise ValueError("Delivered packet does not reproduce from captured measurements")
            context, waits = build_context(state, frame["before"], step, waits, timing)
            proposal = controller.act(state, context)
            decision = protection.filter_context(proposal, context)
            if proposal != frame["proposed"] or controller.diagnostics != frame["policy"] or decision.to_dict() != frame["shield"]:
                raise ValueError("Controller/shield proposal reconstruction mismatch")
            if decision.executed_action != frame["executed"]:
                raise ValueError("Executed action differs")
            before = feedback(physical)
            physical.tick(.1, lanes=None, requested_phase=decision.executed_action)
            if feedback(physical) != frame["after"]:
                raise ValueError("Executed physical lamps do not reproduce")
            audit.observe((before["phase"], before["color"], before["age"]), physical)
            arrivals.update(json.dumps([step, frame["generated"]]).encode())
            gates += int(controller.diagnostics["gate"])
            extensions += int(controller.diagnostics.get("reason") == "supported_extension")
            frame_count += 1
        result = raw["result"]
        population = raw["wait_population"]
        if set(population) != {"completed", "active", "backlog"} or len(population["completed"]) != result["passed"]:
            raise ValueError("Completed-trip population/counter mismatch")
        metrics = wait_metrics([v for category in population.values() for v in category], result["passed"], result["arrivals"])
        if (any(metrics[k] != result[k] for k in metrics) or result["arrival_trace_hash"] != arrivals.hexdigest()
                or result["samples"] != audit.samples or result["signal_conflicts"] != audit.conflicts
                or result["clearance_violations"] != audit.clearance_violations
                or result["policy_gates"] != gates or result["extension_proposals"] != extensions
                or result["shield"] != protection.get_audit_metrics()):
            raise ValueError("Outcome population/audit/counter reconstruction mismatch")
    return dict(verified=True, smoke=report["smoke"], full_runs=len(rows), replayed_packet_and_signal_frames=frame_count,
        independently_rerun_traffic_trajectories=0, continue_to_fresh_development=report["continue_to_fresh_development"],
        publication_ready=False, scope="Sources/output hashes, synthetic packet corruption/delivery, causal motion, all actions/shield/lamp states, saved wait-population metrics and frozen screen. Traffic kinematics not independently rerun.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--smoke-output", type=Path)
    mode.add_argument("--resume", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
    elif args.resume:
        manifest = json.loads((args.resume/"manifest.json").read_text())
        result = run(args.resume, smoke=manifest["smoke"], resume=True)
    else:
        result = run(args.smoke_output or args.output, smoke=bool(args.smoke_output))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
