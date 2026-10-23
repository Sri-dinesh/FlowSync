"""Frozen plans and executed episode stream for the SUMO classical comparison."""
from dataclasses import asdict

from research.audits.sumo_branch_feasibility import Signal, advance
from research.pilots.run_sumo_future_panel import arrivals
from research.policies.sumo_classical import Clock, choose_action, observe

SOURCE_FILES = (
    "research/pilots/run_sumo_classical_panel.py", "research/policies/sumo_classical.py",
    "research/analysis/sumo_classical_metrics.py", "research/experiments/sumo_classical_runtime.py",
    "research/audits/verify_sumo_classical_panel.py", "research/audits/sumo_branch_feasibility.py",
    "research/audits/verify_sumo_future_panel.py", "research/pilots/run_sumo_future_panel.py",
    "research/requirements-sumo.txt", "research/docs/protocols/SUMO_CLASSICAL_BASELINES_20261023.md",
)


def configuration(smoke=False):
    return dict(smoke=smoke, steps=800 if smoke else 1800,
                repeats=2 if smoke else 1, cap_seconds=180 if smoke else 900,
                families=[("balanced", .2, .2, [110901])] if smoke else [
                    ("balanced", .2, .2, list(range(110001, 110006))),
                    ("ns_dominant", .3, .1, list(range(110101, 110106))),
                    ("ew_dominant", .1, .3, list(range(110201, 110206)))])


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=seed, family=family, ns_rate=ns, ew_rate=ew,
                 steps=cfg["steps"], schedule=arrivals(seed, 0, cfg["steps"], ns, ew))
            for family, ns, ew, seeds in cfg["families"] for seed in seeds]


def episode(conn, axes, plan, controller, budget):
    """Stream ticks; callers persist partial gzip traces if a budget/error stops."""
    signal, backlog, previous = Signal(), [], []
    requested = {}
    for request in plan["schedule"]:
        requested.setdefault(request[0], []).append(request)
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("Whole episodes require a fresh empty simulation")
    for tick in range(plan["steps"]):
        budget()
        proposal, decision = None, None
        if tick % 20 == 0:
            packet = observe(previous)
            proposal = choose_action(controller, packet, Clock(signal.phase, signal.stage, signal.age))
            decision = dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
        # Every decision is supplied explicitly; the frozen helper does not
        # silently resume halted-only control after the first intervention.
        row, backlog = advance(conn, signal, axes, tick, requested.get(tick, []), backlog, first_action=proposal)
        if decision is not None:
            row["decision"] = decision
        previous = row["vehicles"]
        yield row
