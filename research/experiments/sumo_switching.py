"""Observed-count switching diagnostic with canonical phase labels and frozen physics."""
from dataclasses import asdict
import json
from pathlib import Path

from research.audits.sumo_branch_feasibility import Signal, advance, audit_signals
from research.experiments.sumo_observed_episode import validate_trace as validate_accounting
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.pilots.run_sumo_future_panel import arrivals
from research.policies.sumo_classical import Clock, observe
from research.policies.sumo_switching import Method, propose

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "research/manifests/sumo_switching.json"


def protocol():
    spec = json.loads(PROTOCOL.read_text())
    if (spec["version"] != "sumo_switching_v1" or spec["dt_s"] != .1 or spec["decision_ticks"] != 20
            or spec["physical_timings_ticks"] != dict(min_green=80, yellow=30, all_red=10)):
        raise ValueError("Protocol must match the frozen physical clock and transition rules")
    names = [m["name"] for m in spec["methods"] + spec["smoke_extra_methods"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate study method")
    for raw in spec["methods"] + spec["smoke_extra_methods"]:
        method = Method(**raw)
        if method.fault not in {f.name for f in PRESETS}:
            raise ValueError("Unknown sensing condition")
    if not all(spec["candidate_screen"][key] is True for key in (
            "no_primary_aggregate_p95_or_throughput_loss", "no_start_group_mean_delay_loss")):
        raise ValueError("This protocol requires the declared tail/throughput/start constraints")
    return spec


def configuration(smoke=False):
    if type(smoke) is not bool:
        raise ValueError("Smoke mode must be boolean")
    spec = protocol()
    return dict(smoke=smoke, steps=spec["smoke_steps" if smoke else "full_steps"],
                endpoint_ticks=spec["smoke_endpoint_ticks" if smoke else "full_endpoint_ticks"],
                families=[spec["smoke_family"]] if smoke else spec["families"],
                initial_phases=spec["initial_phases"],
                methods=spec["methods"] + (spec["smoke_extra_methods"] if smoke else []),
                session_cap_seconds=spec["smoke_session_cap_seconds" if smoke else "session_cap_seconds"],
                max_sessions=spec["max_sessions"])


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=s, family=f["name"], ns_rate=f["ns_rate"], ew_rate=f["ew_rate"], steps=cfg["steps"],
                 schedule=arrivals(s, 0, cfg["steps"], f["ns_rate"], f["ew_rate"]))
            for f in cfg["families"] for s in f["seeds"]]


def method_for(name):
    spec = protocol()
    matches = [m for m in spec["methods"] + spec["smoke_extra_methods"] if m["name"] == name]
    if len(matches) != 1:
        raise ValueError("Unknown study method")
    return Method(**matches[0])


def jobs(smoke=False):
    cfg = configuration(smoke)
    result = [dict(seed=p["seed"], initial_phase=phase, method=m["name"], repeat=repeat,
                   kind="episode", steps=cfg["steps"])
              for p in plans(smoke) for phase in cfg["initial_phases"] for m in cfg["methods"]
              for repeat in range(2 if smoke else 1)]
    if smoke:
        seed = plans(True)[0]["seed"]
        result += [dict(seed=seed, initial_phase=phase, method=m["name"], repeat=0,
                        kind="prefix", steps=cfg["endpoint_ticks"][0])
                   for phase in cfg["initial_phases"] for m in protocol()["methods"]]
        result += [dict(seed=seed, initial_phase=0, method=m, repeat=0, kind="anchor", steps=cfg["steps"])
                   for m in ("pressure_clean", "pressure_mixed")]
    return result


def job_name(job):
    return f"s{job['seed']}_p{job['initial_phase']}_{job['method']}_{job['kind']}_r{job['repeat']}"


def trim(plan, steps):
    return dict(plan, steps=steps, schedule=[r for r in plan["schedule"] if r[0] < steps])


def phase_state(state, phase):
    return dict(state, phase=state["phase"] ^ phase, pending=state["pending"] ^ phase)


def episode(conn, axes, plan, method, initial_phase, budget):
    if type(initial_phase) is not int or initial_phase not in (0, 1):
        raise ValueError("Canonical initial phase must be integer NS=0 or EW=1")
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("Whole episodes require an empty fresh simulation")
    fault = next(f for f in PRESETS if f.name == method.fault)
    sensor, signal, previous, backlog, requested = CountSensor(fault, plan["seed"]), Signal(), [], [], {}
    for request in plan["schedule"]:
        requested.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        delivered = sensor.step(previous, tick)
        internal_proposal, decision = None, None
        if tick % 20 == 0:
            before = phase_state(asdict(signal), initial_phase)
            packet = None if method.controller == "fixed" else delivered.counts
            selected = propose(method, packet, Clock(before["phase"], before["stage"], before["age"]))
            internal_proposal = selected["proposal"] ^ initial_phase
            decision = dict(packet=delivered.counts.to_dict(), before_fsm=before,
                            proposal=selected["proposal"], policy=selected)
        row, backlog = advance(conn, signal, [a ^ initial_phase for a in axes], tick,
                               requested.get(tick, []), backlog, first_action=internal_proposal)
        row["fsm"] = phase_state(row["fsm"], initial_phase)
        row["sensing"] = delivered.to_dict()
        if decision is not None:
            row["decision"] = decision
        previous = row["vehicles"]
        yield row


def historical_view(trace):
    return [dict(row, decision={k: v for k, v in row["decision"].items() if k != "policy"})
            if "decision" in row else dict(row) for row in trace]


def physical_view(trace):
    return [{k: v for k, v in r.items() if k not in ("decision", "sensing")} for r in trace]


def validate_trace(trace, plan, method, axes, initial_phase):
    if type(initial_phase) is not int or initial_phase not in (0, 1):
        raise ValueError("Invalid canonical initial phase")
    fault = next(f for f in PRESETS if f.name == method.fault)
    sensor, previous, packets, views, missing, ages = CountSensor(fault, plan["seed"]), [], [], [], 0, []
    for tick, row in enumerate(trace):
        delivery = sensor.step(previous, tick)
        if row["tick"] != tick or row.get("sensing") != delivery.to_dict():
            raise ValueError("Delivered sensing frame does not reconstruct")
        view = dict(row, fsm=phase_state(row["fsm"], initial_phase))
        permission = {axes[i] for i, lamp in enumerate(row["lamps"]) if lamp in "GgYy"}
        if row["fsm"]["stage"] in ("green", "yellow") and permission != {row["fsm"]["phase"]}:
            raise ValueError("Canonical phase label differs from executed lamps")
        if tick % 20 == 0:
            packet = None if method.controller == "fixed" else delivery.counts
            decision = row["decision"]
            before = decision["before_fsm"]
            chosen = propose(method, packet, Clock(before["phase"], before["stage"], before["age"]))
            if decision["packet"] != delivery.counts.to_dict() or decision["policy"] != chosen or decision["proposal"] != chosen["proposal"]:
                raise ValueError("Policy proposal/margin telemetry differs from delivered counts")
            view["decision"] = dict(packet=observe(previous).to_dict(),
                before_fsm=phase_state(before, initial_phase), proposal=decision["proposal"] ^ initial_phase)
            packets.append(delivery.counts)
            if delivery.source_tick is None: missing += 1
            else: ages.append((tick-delivery.source_tick)/10)
        views.append(view)
        previous = row["vehicles"]
    iterator = iter(packets)
    def policy(_offline_clean, clock):
        counts = next(iterator)
        canonical = Clock(clock.phase ^ initial_phase, clock.stage, clock.age)
        return propose(method, None if method.controller == "fixed" else counts, canonical)["proposal"] ^ initial_phase
    measured = validate_accounting(views, plan["schedule"], policy, [a ^ initial_phase for a in axes], plan["steps"])
    if next(iterator, None) is not None:
        raise ValueError("Unconsumed policy packets")
    audit_signals(trace, axes)
    measured["sensing"] = dict(missing_decisions=missing, mean_age_s=sum(ages)/len(ages) if ages else None)
    measured["service"] = dict(
        green_ns_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 0 for r in trace)/10,
        green_ew_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 1 for r in trace)/10,
        clearance_s=sum(r["fsm"]["stage"] != "green" for r in trace)/10,
        margin_held_gates=sum(r.get("decision", {}).get("policy", {}).get("margin_held", False) for r in trace))
    return measured


def measurements(trace, plan, job, axes, smoke=False):
    cfg = configuration(smoke)
    if len(trace) != job["steps"]:
        raise ValueError("Incomplete or extended episode")
    method = method_for(job["method"])
    return {str(end//10): validate_trace(trace[:end], trim(plan, end), method, axes, job["initial_phase"])
            for end in cfg["endpoint_ticks"] if end <= job["steps"]}
