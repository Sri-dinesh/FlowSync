"""Frozen robustness cases and a reversible initial-phase label adapter."""
from research.audits.sumo_branch_feasibility import audit_signals, file_hash
from research.experiments.sumo_count_ablation import ROOT, SOURCE_FILES as COUNT_SOURCES
from research.experiments.sumo_observed_episode import episode as base_episode, validate_trace as base_validate
from research.pilots.run_sumo_future_panel import arrivals
from research.policies.sumo_classical import Clock

CONTROLLERS = ("max_pressure", "total_incoming")
PINNED_SOURCES = {
    "research/policies/sumo_classical.py": "15c66f3f47507496204595823d026df6d4bc25bacd8d5456918ce8a1d2c30be1",
    "research/policies/sumo_total_count.py": "2c39bea997473584606bdc73a3621e733b88b8a7148d4ef2ac2afe4206ea3342",
    "research/audits/sumo_branch_feasibility.py": "f150579af1bb14befaf2f9af2a930929b532dcc77639dc7d78bb4672bbed329b",
    "research/experiments/sumo_observed_episode.py": "2aa8f40f5ddf37679e61cdaf76e1774b61696723e100d7c88717584e985df73e",
}
SOURCE_FILES = (*COUNT_SOURCES, "research/analysis/analyze_sumo_count_ablation.py",
    "research/experiments/sumo_robustness.py", "research/analysis/sumo_robustness_metrics.py",
    "research/pilots/run_sumo_robustness_panel.py", "research/audits/verify_sumo_robustness.py",
    "research/docs/protocols/SUMO_ROBUSTNESS_20261023.md")


def configuration(smoke=False):
    if type(smoke) is not bool:
        raise ValueError("Smoke mode must be boolean")
    families = [dict(name="balanced", ns_rate=.2, ew_rate=.2, seeds=[112901])] if smoke else [
        dict(name="balanced", ns_rate=.2, ew_rate=.2, seeds=[112001, 112002]),
        dict(name="ns_dominant", ns_rate=.3, ew_rate=.1, seeds=[112101, 112102]),
        dict(name="ew_dominant", ns_rate=.1, ew_rate=.3, seeds=[112201, 112202])]
    return dict(smoke=smoke, steps=800 if smoke else 3600, endpoint_ticks=[400, 800] if smoke else [1800, 3600],
        cap_seconds=180 if smoke else 900, families=families, initial_phases=[0, 1],
        controllers=list(CONTROLLERS), repeats=2 if smoke else 1, planned_runs=10 if smoke else 24,
        planned_signal_samples=7200 if smoke else 86400, pinned_sources=PINNED_SOURCES.copy())


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=seed, family=f["name"], ns_rate=f["ns_rate"], ew_rate=f["ew_rate"], steps=cfg["steps"],
                 schedule=arrivals(seed, 0, cfg["steps"], f["ns_rate"], f["ew_rate"]))
            for f in cfg["families"] for seed in f["seeds"]]


def jobs(smoke=False):
    cfg = configuration(smoke)
    tasks = [dict(seed=p["seed"], initial_phase=phase, controller=c, repeat=repeat, kind="episode", steps=cfg["steps"])
             for p in plans(smoke) for phase in cfg["initial_phases"] for c in CONTROLLERS for repeat in range(cfg["repeats"])]
    if smoke:
        tasks += [dict(seed=112901, initial_phase=phase, controller="max_pressure", repeat=0,
                       kind="prefix_replay", steps=cfg["endpoint_ticks"][0]) for phase in cfg["initial_phases"]]
    return tasks


def trace_name(job):
    return f"trace_{job['seed']}_p{job['initial_phase']}_{job['controller']}_{job['kind']}_r{job['repeat']}.jsonl.gz"


def trim_plan(plan, steps):
    return dict(**{k: v for k, v in plan.items() if k not in ("steps", "schedule")}, steps=steps,
                schedule=[a for a in plan["schedule"] if a[0] < steps])


def check_pins():
    for name, expected in PINNED_SOURCES.items():
        if file_hash(ROOT/name) != expected:
            raise ValueError(f"Frozen controller/physical dependency changed: {name}")


def phase_value(value):
    if type(value) is not int or value not in (0, 1):
        raise ValueError("Phase/action must be integer NS=0 or EW=1")
    return value


def relabel_frame(frame, initial_phase):
    """An involution: relabel only phase/pending/action; preserve sensor data/lamps."""
    offset = phase_value(initial_phase)
    def state(fsm):
        return dict(fsm, phase=phase_value(fsm["phase"]) ^ offset, pending=phase_value(fsm["pending"]) ^ offset)
    result = dict(frame, fsm=state(frame["fsm"]))
    if "decision" in frame:
        decision = frame["decision"]
        result["decision"] = dict(decision, before_fsm=state(decision["before_fsm"]),
                                  proposal=phase_value(decision["proposal"]) ^ offset)
    return result


def relabel_policy(policy, initial_phase):
    offset = phase_value(initial_phase)
    def select(packet, clock):
        canonical = Clock(clock.phase ^ offset, clock.stage, clock.age)
        return phase_value(policy(packet, canonical)) ^ offset
    return select


def episode(conn, axes, plan, policy, initial_phase, budget):
    offset = phase_value(initial_phase)
    for frame in base_episode(conn, [a ^ offset for a in axes], plan, relabel_policy(policy, offset), budget):
        yield relabel_frame(frame, offset)


def validate_trace(trace, schedule, policy, axes, steps, initial_phase):
    offset = phase_value(initial_phase)
    normalized = [relabel_frame(r, offset) for r in trace]
    result = base_validate(normalized, schedule, relabel_policy(policy, offset), [a ^ offset for a in axes], steps)
    # Also audit the ORIGINAL executed lamps against canonical NS/EW axes.
    audit_signals(trace, axes)
    return result
