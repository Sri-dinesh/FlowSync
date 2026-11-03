"""Native adapter and strict replay for the fixed service-watchdog comparator."""
from dataclasses import asdict

from research.audits.sumo_branch_feasibility import Signal, advance, audit_signals
from research.experiments.sumo_observed_episode import validate_trace as validate_accounting
from research.experiments.sumo_service_ledger import _clock, _same
from research.experiments.sumo_switching import phase_state
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import observe
from research.policies.sumo_service_watchdog import VERSION, after_execution, propose


def _sensor(fault, seed):
    if fault not in {p.name for p in PRESETS}:
        raise ValueError("Unknown delivered sensing condition")
    return CountSensor(next(p for p in PRESETS if p.name == fault), seed)


def episode(conn, axes, plan, initial_phase, budget, *, fault="clean"):
    if type(initial_phase) is not int or initial_phase not in (0, 1):
        raise ValueError("Canonical initial phase must be NS=0 or EW=1")
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("Requires an empty fresh native simulation")
    sensor = _sensor(fault, plan["seed"])
    signal, ages, previous, backlog, requested = Signal(), (0, 0), [], [], {}
    for request in plan["schedule"]:
        requested.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        delivery = sensor.step(previous, tick)
        before = phase_state(asdict(signal), initial_phase)
        choice = propose(delivery.counts, _clock(before), ages)
        row, backlog = advance(conn, signal, [a ^ initial_phase for a in axes], tick,
            requested.get(tick, []), backlog, first_action=choice["proposal"] ^ initial_phase)
        row["fsm"] = phase_state(row["fsm"], initial_phase)
        after = after_execution(delivery.counts, _clock(row["fsm"]), ages)
        row["sensing"] = delivery.to_dict()
        row["watchdog"] = dict(version=VERSION, before=list(ages), after=list(after))
        if tick % 20 == 0:
            row["decision"] = dict(packet=delivery.counts.to_dict(), before_fsm=before,
                                   proposal=choice["proposal"], policy=choice)
        previous, ages = row["vehicles"], after
        yield row


def validate_trace(trace, plan, axes, initial_phase, *, fault="clean"):
    if type(initial_phase) is not int or initial_phase not in (0, 1) or len(trace) != plan["steps"]:
        raise ValueError("Invalid phase or incomplete/extended watchdog episode")
    sensor = _sensor(fault, plan["seed"])
    signal = Signal(phase=initial_phase, pending=initial_phase)
    ages, previous, views, gates = (0, 0), [], [], []
    overrides = changed = 0
    for tick, row in enumerate(trace):
        if type(row.get("tick")) is not int or row["tick"] != tick:
            raise ValueError("Invalid or reordered watchdog interval")
        delivery = sensor.step(previous, tick)
        _same(row["sensing"], delivery.to_dict(), "Delivered packet does not reconstruct")
        before = asdict(signal)
        choice = propose(delivery.counts, _clock(before), ages)
        if tick % 20 == 0:
            _same(row["decision"], dict(packet=delivery.counts.to_dict(), before_fsm=before,
                proposal=choice["proposal"], policy=choice), "Watchdog decision does not reconstruct")
            gates.append((_clock(before), choice["proposal"]))
            overrides += choice["watchdog_due"]
            changed += choice["proposal"] != choice["reference"]
            signal.request(choice["proposal"])
        elif "decision" in row:
            raise ValueError("Unexpected off-gate decision")
        _same(row["fsm"], asdict(signal), "Executed watchdog FSM does not reconstruct")
        _same(row["lamps"], signal.lamps(axes), "Executed lamps differ from canonical phase")
        after = after_execution(delivery.counts, _clock(row["fsm"]), ages)
        _same(row["watchdog"], dict(version=VERSION, before=list(ages), after=list(after)),
              "Watchdog service ages do not reconstruct")
        view = dict(row, fsm=phase_state(row["fsm"], initial_phase))
        if tick % 20 == 0:
            view["decision"] = dict(packet=observe(previous).to_dict(),
                before_fsm=phase_state(before, initial_phase), proposal=choice["proposal"] ^ initial_phase)
        views.append(view)
        previous, ages = row["vehicles"], after
        signal.advance()
    iterator = iter(gates)
    def accounted_policy(_offline_clean, clock):
        expected, choice = next(iterator)
        if expected != _clock(dict(phase=clock.phase ^ initial_phase, stage=clock.stage, age=clock.age)):
            raise ValueError("Accounting and watchdog clocks differ")
        return choice ^ initial_phase
    measured = validate_accounting(views, plan["schedule"], accounted_policy,
        [a ^ initial_phase for a in axes], plan["steps"])
    if next(iterator, None) is not None:
        raise ValueError("Unconsumed watchdog decision")
    audit_signals(trace, axes)
    measured["watchdog"] = dict(due_gates=overrides, changed_gates=changed, final_ages=list(ages))
    return measured
