"""Delivered-frame pressure memory with the existing physical SUMO stepping."""
from dataclasses import asdict

from research.audits.sumo_branch_feasibility import Signal, advance, audit_signals
from research.experiments.sumo_observed_episode import validate_trace as validate_accounting
from research.experiments.sumo_switching import phase_state
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import Clock, observe
from research.policies.sumo_history import PressureHistory, propose


def episode(conn, axes, plan, method, initial_phase, window_ticks, budget):
    if type(initial_phase) is not int or initial_phase not in (0, 1):
        raise ValueError("Canonical initial phase must be NS=0 or EW=1")
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("History episodes require a fresh empty simulation")
    sensor = CountSensor(next(f for f in PRESETS if f.name == method.fault), plan["seed"])
    memory, signal, previous, backlog, requests = PressureHistory(window_ticks), Signal(), [], [], {}
    for request in plan["schedule"]: requests.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        delivered = sensor.step(previous, tick)
        memory.push(delivered)
        action, decision = None, None
        if tick % 20 == 0:
            before = phase_state(asdict(signal), initial_phase)
            selected = propose(method, memory, Clock(before["phase"], before["stage"], before["age"]))
            action = selected["proposal"] ^ initial_phase
            decision = dict(packet=delivered.counts.to_dict(), before_fsm=before,
                            proposal=selected["proposal"], policy=selected)
        row, backlog = advance(conn, signal, [a ^ initial_phase for a in axes], tick,
                               requests.get(tick, []), backlog, first_action=action)
        row["fsm"], row["sensing"] = phase_state(row["fsm"], initial_phase), delivered.to_dict()
        if decision is not None: row["decision"] = decision
        previous = row["vehicles"]
        yield row


def validate_trace(trace, plan, method, axes, initial_phase, window_ticks):
    if type(initial_phase) is not int or initial_phase not in (0, 1) or len(trace) != plan["steps"]:
        raise ValueError("Invalid canonical phase or incomplete/extended history episode")
    sensor = CountSensor(next(f for f in PRESETS if f.name == method.fault), plan["seed"])
    memory, previous, views, selected_gates = PressureHistory(window_ticks), [], [], []
    for tick, row in enumerate(trace):
        delivered = sensor.step(previous, tick)
        memory.push(delivered)
        if row["tick"] != tick or row["sensing"] != delivered.to_dict():
            raise ValueError("Delivered frame does not reconstruct from recorded history")
        permissions = {axes[i] for i, lamp in enumerate(row["lamps"]) if lamp in "GgYy"}
        if row["fsm"]["stage"] in ("green", "yellow") and permissions != {row["fsm"]["phase"]}:
            raise ValueError("Canonical phase differs from executed lamps")
        view = dict(row, fsm=phase_state(row["fsm"], initial_phase))
        if tick % 20 == 0:
            decision = row["decision"]
            before = decision["before_fsm"]
            clock = Clock(before["phase"], before["stage"], before["age"])
            selected = propose(method, memory, clock)
            if (decision["packet"] != delivered.counts.to_dict() or decision["policy"] != selected
                    or decision["proposal"] != selected["proposal"]):
                raise ValueError("Memory scores/proposal differ from delivered frame history")
            selected_gates.append((clock, selected["proposal"]))
            view["decision"] = dict(packet=observe(previous).to_dict(), before_fsm=phase_state(before, initial_phase),
                                    proposal=selected["proposal"] ^ initial_phase)
        views.append(view)
        previous = row["vehicles"]
    iterator = iter(selected_gates)
    def policy(_offline_clean, clock):
        expected, choice = next(iterator)
        if expected != Clock(clock.phase ^ initial_phase, clock.stage, clock.age):
            raise ValueError("Recorded and reconstructed decision clocks differ")
        return choice ^ initial_phase
    measured = validate_accounting(views, plan["schedule"], policy, [a ^ initial_phase for a in axes], plan["steps"])
    if next(iterator, None) is not None: raise ValueError("Unconsumed memory decisions")
    audit_signals(trace, axes)
    measured["service"] = dict(
        green_ns_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 0 for r in trace)/10,
        green_ew_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 1 for r in trace)/10,
        clearance_s=sum(r["fsm"]["stage"] != "green" for r in trace)/10,
        history_changed_gates=sum(r["decision"]["proposal"] != r["decision"]["policy"]["current_proposal"]
                                  for r in trace if "decision" in r))
    return measured
