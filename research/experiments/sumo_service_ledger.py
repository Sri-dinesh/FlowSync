"""Isolated service-ledger adapter/replay over the unchanged SUMO signal model."""
from dataclasses import asdict
import json

from research.audits.sumo_branch_feasibility import Signal, advance, audit_signals
from research.experiments.sumo_observed_episode import validate_trace as validate_accounting
from research.experiments.sumo_switching import phase_state
from research.observation.sumo_sensing import CountSensor, PRESETS
from research.policies.sumo_classical import Clock, observe
from research.policies.sumo_service_ledger import DECISION_TICKS, RULES, VERSION, ServiceLedgerPolicy


def record(value):
    return json.loads(json.dumps(asdict(value), sort_keys=True, allow_nan=False))


def _same(actual, expected, message):
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError(message)


def _clock(state):
    return Clock(state["phase"], state["stage"], state["age"])


def _setup(mode, fault):
    if (not isinstance(mode,str) or not isinstance(fault,str)
            or mode not in RULES or fault not in {f.name for f in PRESETS}):
        raise ValueError("Unknown service-ledger mode or delivered sensing preset")
    return ServiceLedgerPolicy(RULES[mode]), next(f for f in PRESETS if f.name == fault)


def episode(conn, axes, plan, initial_phase, budget, *, mode="ledger", fault="clean"):
    if type(initial_phase) is not int or initial_phase not in (0, 1):
        raise ValueError("Canonical initial phase must be NS=0 or EW=1")
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("Ledger episodes require a fresh empty simulation")
    policy, preset = _setup(mode, fault)
    sensor = CountSensor(preset, plan["seed"])
    signal, previous, backlog, requests = Signal(), [], [], {}
    for request in plan["schedule"]:
        requests.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        delivered = sensor.step(previous, tick)
        before = phase_state(asdict(signal), initial_phase)
        proposal = policy.begin_interval(delivered.counts, _clock(before))
        # Explicit even at cold start/clearance gates: None would invoke raw queues.
        row, backlog = advance(conn, signal, [a ^ initial_phase for a in axes], tick,
                               requests.get(tick, []), backlog, first_action=proposal.phase ^ initial_phase)
        row["fsm"] = phase_state(row["fsm"], initial_phase)
        receipt = policy.finish_interval(proposal, _clock(row["fsm"]))
        row["sensing"] = delivered.to_dict()
        row["allocation"] = dict(version=VERSION, mode=mode, proposal=record(proposal), receipt=record(receipt))
        if tick % DECISION_TICKS == 0:
            row["decision"] = dict(packet=delivered.counts.to_dict(), before_fsm=before,
                                   proposal=proposal.phase, policy=record(proposal))
        previous = row["vehicles"]
        yield row


def validate_trace(trace, plan, axes, initial_phase, *, mode="ledger", fault="clean"):
    if type(initial_phase) is not int or initial_phase not in (0, 1) or len(trace) != plan["steps"]:
        raise ValueError("Invalid canonical phase or incomplete/extended ledger episode")
    policy, preset = _setup(mode, fault)
    sensor = CountSensor(preset, plan["seed"])
    signal = Signal(phase=initial_phase, pending=initial_phase)
    previous, views, gates = [], [], []
    completed = credited = changed = 0
    for tick, row in enumerate(trace):
        if type(row.get("tick")) is not int or row["tick"] != tick:
            raise ValueError("Invalid or reordered ledger interval")
        delivered = sensor.step(previous, tick)
        _same(row["sensing"], delivered.to_dict(), "Delivered packet does not reconstruct")
        before = asdict(signal)
        proposal = policy.begin_interval(delivered.counts, _clock(before))
        if tick % DECISION_TICKS == 0:
            expected = dict(packet=delivered.counts.to_dict(), before_fsm=before,
                            proposal=proposal.phase, policy=record(proposal))
            _same(row["decision"], expected, "Ledger decision differs from delivered state")
            gates.append((_clock(before), proposal.phase))
            changed += proposal.phase != proposal.reference
            signal.request(proposal.phase)
        elif "decision" in row:
            raise ValueError("Unexpected off-gate decision")
        _same(row["fsm"], asdict(signal), "Executed FSM does not reconstruct")
        _same(row["lamps"], signal.lamps(axes), "Executed lamps differ from the canonical clock")
        receipt = policy.finish_interval(proposal, _clock(row["fsm"]))
        _same(row["allocation"], dict(version=VERSION, mode=mode, proposal=record(proposal), receipt=record(receipt)),
              "Allocation debt, batch or service receipt does not reconstruct")
        completed += receipt.completed is not None
        credited += receipt.credited_batch is not None
        view = dict(row, fsm=phase_state(row["fsm"], initial_phase))
        if tick % DECISION_TICKS == 0:
            view["decision"] = dict(packet=observe(previous).to_dict(),
                before_fsm=phase_state(before, initial_phase), proposal=proposal.phase ^ initial_phase)
        views.append(view)
        previous = row["vehicles"]
        signal.advance()

    iterator = iter(gates)
    def accounted_policy(_offline_clean, clock):
        expected, choice = next(iterator)
        if expected != Clock(clock.phase ^ initial_phase, clock.stage, clock.age):
            raise ValueError("Accounting and delivered-policy clocks differ")
        return choice ^ initial_phase
    measured = validate_accounting(views, plan["schedule"], accounted_policy,
                                  [a ^ initial_phase for a in axes], plan["steps"])
    if next(iterator, None) is not None:
        raise ValueError("Unconsumed ledger decision")
    audit_signals(trace, axes)
    measured["allocation"] = dict(completed_batches=completed, credited_green_ticks=credited,
        changed_decision_gates=changed, final_state=policy.snapshot(),
        endpoint_censored=policy.snapshot()["batch"] is not None)
    return measured
