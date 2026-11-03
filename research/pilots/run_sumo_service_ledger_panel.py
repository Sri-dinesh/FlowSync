"""Frozen paired traffic screen for the research-only executed-service ledger."""
import argparse
import json
from pathlib import Path
import sys

from research.analysis.sumo_service_ledger_metrics import summarize
from research.experiments import sumo_service_ledger as ledger
from research.experiments import sumo_service_watchdog as watchdog
from research.experiments import sumo_switching as pressure
from research.experiments.sumo_panel import Panel
from research.pilots.run_sumo_future_panel import arrivals
from research.pilots.run_sumo_history_panel import ROOT, SOURCES as BASE_SOURCES
from research.policies.sumo_service_ledger import DECISION_TICKS, MAX_BATCH_TICKS, QUANTUM_TICKS, SHARE_SCALE
from research.policies.sumo_service_watchdog import WATCHDOG_TICKS, after_execution
from research.policies.sumo_classical import Counts
from research.policies.sumo_switching import Method

SPEC = "research/manifests/sumo_service_ledger_panel.json"
MODES = ("ledger", "pressure_budget", "pressure_batch", "debt_batch", "max_pressure", "watchdog")
SOURCES = tuple(sorted((*BASE_SOURCES, SPEC, "research/manifests/service_ledger_design.json",
    "research/policies/sumo_service_ledger.py", "research/experiments/sumo_service_ledger.py",
    "research/policies/sumo_service_watchdog.py", "research/experiments/sumo_service_watchdog.py",
    "research/analysis/sumo_service_ledger_metrics.py", "research/pilots/run_sumo_service_ledger_panel.py")))


def protocol():
    spec = json.loads((ROOT/SPEC).read_text())
    expected = dict(version="sumo_service_ledger_panel_v1", dt_s=.1, decision_ticks=DECISION_TICKS,
        quantum_ticks=QUANTUM_TICKS, share_scale=SHARE_SCALE, max_batch_ticks=MAX_BATCH_TICKS,
        watchdog_ticks=WATCHDOG_TICKS, physical_timings_ticks=dict(min_green=80, yellow=30, all_red=10),
        initial_phases=[0, 1], full_steps=3600, full_endpoint_ticks=[1800, 3600],
        smoke_steps=800, smoke_endpoint_ticks=[400, 800], session_cap_seconds=900,
        smoke_session_cap_seconds=600, max_sessions=4, smoke_pause_after_jobs=2,
        primary_candidate="ledger", gain_references=["max_pressure", "pressure_budget"],
        nonloss_references=["pressure_batch", "debt_batch", "watchdog"],
        candidate_screen=dict(minimum_delay_gain_fraction=.02, maximum_seed_mean_delay_loss_fraction=.01,
            no_aggregate_p95_or_throughput_loss=True, no_start_group_mean_delay_loss=True, separate_sensing_screens=True))
    methods = [dict(name=mode+"_"+label, mode=mode, fault=fault) for mode in MODES
               for label, fault in (("clean", "clean"), ("mixed", "delay2s_miss30"))]
    families = [dict(name=name, ns_rate=ns, ew_rate=ew, seeds=seeds) for name, ns, ew, seeds in (
        ("balanced", .2, .2, [1380001, 1380002]), ("ns_dominant", .3, .1, [1380101, 1380102]),
        ("ew_dominant", .1, .3, [1380201, 1380202]))]
    expected.update(methods=methods, families=families,
        smoke_family=dict(name="balanced", ns_rate=.2, ew_rate=.2, seeds=[1380901]))
    ledger._same({k:spec[k] for k in expected}, expected, "Frozen ledger panel grid/controls/screen changed")
    if set(spec["base_source_sha256"]) != set(BASE_SOURCES):
        raise ValueError("Frozen baseline source coverage changed")
    return spec


def configuration(smoke=False):
    if type(smoke) is not bool:
        raise ValueError("Smoke must be boolean")
    spec = protocol()
    return dict(smoke=smoke, steps=spec["smoke_steps" if smoke else "full_steps"],
        endpoint_ticks=spec["smoke_endpoint_ticks" if smoke else "full_endpoint_ticks"],
        families=[spec["smoke_family"]] if smoke else spec["families"], methods=spec["methods"],
        initial_phases=spec["initial_phases"],
        session_cap_seconds=spec["smoke_session_cap_seconds" if smoke else "session_cap_seconds"],
        max_sessions=spec["max_sessions"])


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=seed, family=f["name"], ns_rate=f["ns_rate"], ew_rate=f["ew_rate"], steps=cfg["steps"],
        schedule=arrivals(seed, 0, cfg["steps"], f["ns_rate"], f["ew_rate"])) for f in cfg["families"] for seed in f["seeds"]]


def jobs(smoke=False):
    cfg = configuration(smoke)
    result = [dict(seed=p["seed"], initial_phase=phase, method=m["name"], repeat=repeat, kind="episode", steps=cfg["steps"])
        for p in plans(smoke) for phase in (0, 1) for m in cfg["methods"]
        for repeat in range(2 if smoke and m["mode"] in ("ledger", "watchdog") else 1)]
    if smoke:
        result += [dict(seed=plans(True)[0]["seed"], initial_phase=phase, method=m["name"], repeat=0,
            kind="prefix", steps=cfg["endpoint_ticks"][0]) for phase in (0, 1) for m in cfg["methods"]]
    return result


def method_for(name):
    matches = [m for m in protocol()["methods"] if m["name"] == name]
    if len(matches) != 1:
        raise ValueError("Unknown ledger panel method")
    return matches[0]


def episode(conn, axes, plan, job, budget):
    m = method_for(job["method"])
    if m["mode"] == "max_pressure":
        return pressure.episode(conn, axes, plan, Method(m["name"], "max_pressure", m["fault"], 0), job["initial_phase"], budget)
    runtime = watchdog if m["mode"] == "watchdog" else ledger
    options = dict(fault=m["fault"])
    if runtime is ledger:
        options["mode"] = m["mode"]
    return runtime.episode(conn, axes, plan, job["initial_phase"], budget, **options)


def traffic_diagnostics(trace):
    """Evaluation-only service, empty-green and allocation counters from validated rows."""
    ages, peak, batches = (0, 0), 0, {}
    empty_observed = empty_truth = 0
    max_debt = credited = 0
    for row in trace:
        packet = Counts.from_dict(row["sensing"]["counts"])
        clock = ledger._clock(row["fsm"])
        ages = after_execution(packet, clock, ages)
        peak = max(peak, *ages)
        if clock.stage == "green":
            empty_observed += not any(packet.incoming[2*clock.phase:2*clock.phase+2])
            directions = ("n", "s") if clock.phase == 0 else ("e", "w")
            empty_truth += not any(v[1] in {d+"_in" for d in directions} for v in row["vehicles"])
        if "allocation" in row:
            p, r = row["allocation"]["proposal"], row["allocation"]["receipt"]
            max_debt = max(max_debt, abs(r["debt_ns_units"]))
            credited += r["credited_batch"] is not None
            if p["batch"] is not None:
                batches[p["batch"]["identifier"]] = p["batch"]["budget"]
    return dict(green_ns_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 0 for r in trace)/10,
        green_ew_s=sum(r["fsm"]["stage"] == "green" and r["fsm"]["phase"] == 1 for r in trace)/10,
        clearance_s=sum(r["fsm"]["stage"] != "green" for r in trace)/10,
        green_with_no_delivered_incoming_s=empty_observed/10, green_with_no_poststep_truth_incoming_s=empty_truth/10,
        peak_delivered_demand_without_phase_green_s=peak/10, started_batches=len(batches),
        extended_batches=sum(b > QUANTUM_TICKS for b in batches.values()),
        budgeted_green_ticks=sum(batches.values()), credited_green_ticks=credited,
        max_absolute_allocation_debt_s=max_debt/(10*SHARE_SCALE))


def measurements(trace, plan, job, axes, smoke):
    if len(trace) != job["steps"]:
        raise ValueError("Incomplete or extended service-ledger panel episode")
    cfg, m, result = configuration(smoke), method_for(job["method"]), {}
    for end in cfg["endpoint_ticks"]:
        if end > job["steps"]:
            continue
        rows, prefix = trace[:end], pressure.trim(plan, end)
        if m["mode"] == "max_pressure":
            measured = pressure.validate_trace(rows, prefix, Method(m["name"], "max_pressure", m["fault"], 0), axes, job["initial_phase"])
        elif m["mode"] == "watchdog":
            measured = watchdog.validate_trace(rows, prefix, axes, job["initial_phase"], fault=m["fault"])
        else:
            measured = ledger.validate_trace(rows, prefix, axes, job["initial_phase"], mode=m["mode"], fault=m["fault"])
        measured["diagnostics"] = traffic_diagnostics(rows)
        if m["mode"] in ("ledger", "debt_batch") and measured["diagnostics"]["max_absolute_allocation_debt_s"] > 16:
            raise ValueError("Executed debt-priority trace violates the conditional allocation bound")
        result[str(end//10)] = measured
    return result


def analyze(rows, smoke):
    return summarize(rows, plans(smoke), configuration(smoke), protocol(), jobs(smoke))


PANEL = Panel(sys.modules[__name__])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path); mode.add_argument("--verify", type=Path); mode.add_argument("--preflight", type=Path)
    parser.add_argument("--smoke", action="store_true"); parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mechanics", type=Path)
    args = parser.parse_args()
    if args.verify and (args.smoke or args.resume or args.mechanics):
        parser.error("--verify takes no collection options")
    if args.preflight and (args.smoke or args.resume):
        parser.error("--preflight is for a new full output")
    result = PANEL.verify(args.verify) if args.verify else PANEL.preflight(args.preflight, args.mechanics) if args.preflight else (
        PANEL.collect(args.output, args.smoke, args.mechanics, args.resume))
    print(json.dumps(result, indent=2))
    if args.output and not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
