"""Shared execution/replay for new studies using the frozen v1 track contract.

Historical runners remain archived. Their v1 context, observation and metric
helpers are reused explicitly so new controls can be anchored to old bundles.
"""
from dataclasses import asdict
import hashlib
import json
from typing import Protocol

from research.observation.arrival_tracks import Packet, Track, TrackSensor, TrackFaults
from research.pilots import run_arrival_window_panel as v1
from research.policies.arrival_extension import Timing
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.simulation.traffic_signal import TrafficSignal


class TrackController(Protocol):
    label: str
    timing: Timing
    diagnostics: dict

    def act(self, state, context) -> int: ...


def rollout_tracks(case, controller: TrackController, budget):
    scenario = ScenarioConfig.from_dict(case["scenario"])
    env, profile = v1.build_environment(scenario)
    env.reset(seed=case["seed"])
    timing = Timing(all_red=scenario.red_duration)
    if controller.timing != timing:
        raise ValueError("Controller and executed signal timing differ")
    sensor = TrackSensor(v1.CALIBRATION, TrackFaults(**case["fault"]), case["seed"]+90000)
    protection, audit = v1.shield(timing), v1.SignalAudit()
    waits, frames, arrivals, gates, extensions = dict.fromkeys(range(4), 0.), [], hashlib.sha256(), 0, 0
    for step in range(scenario.duration_steps):
        budget.check("receding track controller rollout")
        v1.apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        state = sensor.observe(env.intersection, step)
        before = v1.feedback(env.intersection.signal)
        context, waits = v1.build_context(state, before, step, waits, timing)
        proposal = controller.act(state, context)
        decision = protection.filter_context(proposal, context)
        env.step(decision.executed_action)
        audit.observe((before["phase"], before["color"], before["age"]), env.intersection.signal)
        generated = env.intersection.spawner.generated_movements_last_tick
        arrivals.update(json.dumps([step, generated]).encode())
        gates += int(controller.diagnostics["gate"])
        extensions += int(controller.diagnostics.get("reason") == "supported_extension")
        frames.append(dict(step=step, capture=[asdict(t) for t in sensor.last_snapshot], packet=state.packet.to_dict(),
            before=before, after=v1.feedback(env.intersection.signal), proposed=proposal, executed=decision.executed_action,
            policy=controller.diagnostics.copy(), shield=decision.to_dict(), generated=generated))
    population = dict(completed=list(env.intersection.completed_wait_times),
        active=[v.wait_time for queue in env.intersection.lanes.values() for v in queue if v.state != "passed"],
        backlog=env.intersection.spawner.get_backlog_waits())
    metrics = v1.wait_metrics([v for values in population.values() for v in values], env.intersection.total_passed, env.intersection.total_spawned)
    if not v1.math_close(metrics["delay"], env.intersection.get_avg_wait_time()):
        raise ValueError("Track runtime metric differs from shared simulator")
    result = dict(**metrics, samples=audit.samples, violations=audit.conflicts+audit.clearance_violations,
        signal_conflicts=audit.conflicts, clearance_violations=audit.clearance_violations,
        arrival_trace_hash=arrivals.hexdigest(), policy_gates=gates, extension_proposals=extensions,
        shield=protection.get_audit_metrics())
    return dict(case=case, method=controller.label, result=result, wait_population=population, frames=frames)


def replay_tracks(raw, controller: TrackController):
    case = raw["case"]
    timing = Timing(all_red=case["scenario"]["red_duration"])
    if controller.label != raw["method"] or controller.timing != timing:
        raise ValueError("Replay controller identity/timing mismatch")
    sensor = TrackSensor(v1.CALIBRATION, TrackFaults(**case["fault"]), case["seed"]+90000)
    protection, signal, audit = v1.shield(timing), TrafficSignal(timing.all_red), v1.SignalAudit()
    waits, arrivals, gates, extensions = dict.fromkeys(range(4), 0.), hashlib.sha256(), 0, 0
    if len(raw["frames"]) != case["scenario"]["duration_steps"]:
        raise ValueError("Incomplete track trace")
    for step, frame in enumerate(raw["frames"]):
        if frame["step"] != step or v1.feedback(signal) != frame["before"]:
            raise ValueError("Track replay signal continuity mismatch")
        state = sensor.replay(tuple(Track(**t) for t in frame["capture"]), step)
        if state.packet != Packet.parse(frame["packet"]):
            raise ValueError("Track replay packet mismatch")
        context, waits = v1.build_context(state, frame["before"], step, waits, timing)
        proposal = controller.act(state, context)
        decision = protection.filter_context(proposal, context)
        if (proposal != frame["proposed"] or controller.diagnostics != frame["policy"]
                or decision.to_dict() != frame["shield"] or decision.executed_action != frame["executed"]):
            raise ValueError("Track replay controller/shield mismatch")
        before = v1.feedback(signal)
        signal.tick(.1, lanes=None, requested_phase=decision.executed_action)
        if v1.feedback(signal) != frame["after"]:
            raise ValueError("Track replay lamps mismatch")
        audit.observe((before["phase"], before["color"], before["age"]), signal)
        arrivals.update(json.dumps([step, frame["generated"]]).encode())
        gates += int(controller.diagnostics["gate"])
        extensions += int(controller.diagnostics.get("reason") == "supported_extension")
    result, population = raw["result"], raw["wait_population"]
    if set(population) != {"completed", "active", "backlog"} or len(population["completed"]) != result["passed"]:
        raise ValueError("Track replay population mismatch")
    expected = dict(**v1.wait_metrics([v for values in population.values() for v in values], result["passed"], result["arrivals"]),
        samples=audit.samples, violations=audit.conflicts+audit.clearance_violations, signal_conflicts=audit.conflicts,
        clearance_violations=audit.clearance_violations, arrival_trace_hash=arrivals.hexdigest(), policy_gates=gates,
        extension_proposals=extensions, shield=protection.get_audit_metrics())
    if result != expected:
        raise ValueError("Track replay metrics/counters mismatch")
