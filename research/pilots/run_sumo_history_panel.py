"""Fixed interval-mean pressure experiment; mechanics first, no model training."""
import argparse
import json
from pathlib import Path
import sys

from research.analysis.sumo_history_metrics import summarize
from research.experiments import sumo_history as observed
from research.experiments import sumo_switching as legacy
from research.experiments.sumo_panel import Panel
from research.pilots.run_sumo_future_panel import arrivals
from research.pilots.run_sumo_switching_panel import ROOT, SOURCES as BASE_SOURCES
from research.policies.sumo_history import Method
from research.policies.sumo_switching import Method as AnchorMethod

SPEC = "research/manifests/sumo_history.json"
SOURCES = tuple(sorted((*BASE_SOURCES,SPEC,"research/policies/sumo_history.py","research/experiments/sumo_history.py",
                       "research/experiments/sumo_panel.py","research/analysis/sumo_history_metrics.py",
                       "research/pilots/run_sumo_history_panel.py")))


def protocol():
    spec = json.loads((ROOT/SPEC).read_text())
    if (spec["version"]!="sumo_history_v1" or spec["window_ticks"]!=20 or spec["decision_ticks"]!=20 or spec["dt_s"]!=.1
            or spec["physical_timings_ticks"]!=dict(min_green=80,yellow=30,all_red=10)
            or set(spec["base_source_sha256"])!=set(BASE_SOURCES)
            or spec["primary_candidate"]!="mean_clean" or spec["primary_references"]!=["instant_clean","lag_clean","instant_mixed"]):
        raise ValueError("History protocol differs from the fixed control/physical contract")
    methods = [Method(**m) for m in spec["methods"]]
    expected = [("instant_clean","clean","current"),("lag_clean","clean","lag"),("mean_clean","clean","mean"),
                ("instant_mixed","delay2s_miss30","current"),("mean_mixed","delay2s_miss30","mean")]
    if [(m.name,m.fault,m.estimator) for m in methods]!=expected:
        raise ValueError("The five history/sensing controls must match the declared factorial")
    rule = spec["candidate_screen"]
    if not all(rule[key] is True for key in ("no_aggregate_p95_or_throughput_loss","no_start_group_mean_delay_loss",
                                            "noise_arm_no_aggregate_mean_p95_or_throughput_loss")):
        raise ValueError("The fixed protocol requires the declared tail, throughput and start constraints")
    seeds = [seed for family in spec["families"] for seed in family["seeds"]]
    if (len(spec["families"])!=3 or any(len(f["seeds"])!=2 for f in spec["families"])
            or len(set(seeds))!=6 or set(seeds)&set(spec["smoke_family"]["seeds"])):
        raise ValueError("Requires six unique scientific seeds separated from smoke")
    return spec


def configuration(smoke=False):
    if type(smoke) is not bool: raise ValueError("Smoke mode must be boolean")
    spec = protocol()
    return dict(smoke=smoke,steps=spec["smoke_steps" if smoke else "full_steps"],
        endpoint_ticks=spec["smoke_endpoint_ticks" if smoke else "full_endpoint_ticks"],
        families=[spec["smoke_family"]] if smoke else spec["families"],methods=spec["methods"],
        initial_phases=spec["initial_phases"],window_ticks=spec["window_ticks"],
        session_cap_seconds=spec["smoke_session_cap_seconds" if smoke else "session_cap_seconds"],max_sessions=spec["max_sessions"])


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=seed,family=f["name"],ns_rate=f["ns_rate"],ew_rate=f["ew_rate"],steps=cfg["steps"],
                 schedule=arrivals(seed,0,cfg["steps"],f["ns_rate"],f["ew_rate"])) for f in cfg["families"] for seed in f["seeds"]]


def jobs(smoke=False):
    cfg = configuration(smoke)
    result = [dict(seed=p["seed"],initial_phase=phase,method=m["name"],repeat=repeat,kind="episode",steps=cfg["steps"])
              for p in plans(smoke) for phase in cfg["initial_phases"] for m in cfg["methods"] for repeat in range(2 if smoke else 1)]
    if smoke:
        seed = plans(True)[0]["seed"]
        result += [dict(seed=seed,initial_phase=phase,method=m["name"],repeat=0,kind="prefix",steps=cfg["endpoint_ticks"][0])
                   for phase in (0,1) for m in cfg["methods"]]
        result += [dict(seed=seed,initial_phase=phase,method=name,repeat=0,kind="anchor",steps=cfg["steps"])
                   for phase in (0,1) for name in ("instant_clean","instant_mixed","lag_clean")]
    return result


def method_for(name):
    return next(Method(**m) for m in protocol()["methods"] if m["name"]==name)


def anchor_for(name):
    method = method_for(name)
    return AnchorMethod(name,"max_pressure","delay2s" if method.estimator=="lag" else method.fault,0)


def episode(conn, axes, plan, job, budget):
    if job["kind"]=="anchor":
        return legacy.episode(conn,axes,plan,anchor_for(job["method"]),job["initial_phase"],budget)
    return observed.episode(conn,axes,plan,method_for(job["method"]),job["initial_phase"],protocol()["window_ticks"],budget)


def measurements(trace, plan, job, axes, smoke):
    cfg = configuration(smoke)
    if len(trace)!=job["steps"]: raise ValueError("Incomplete or extended history episode")
    result = {}
    for end in cfg["endpoint_ticks"]:
        if end>job["steps"]: continue
        prefix = legacy.trim(plan,end)
        if job["kind"]=="anchor":
            measured = legacy.validate_trace(trace[:end],prefix,anchor_for(job["method"]),axes,job["initial_phase"])
        else:
            measured = observed.validate_trace(trace[:end],prefix,method_for(job["method"]),axes,job["initial_phase"],cfg["window_ticks"])
        result[str(end//10)] = measured
    return result


def analyze(rows, smoke):
    return summarize(rows,plans(smoke),configuration(smoke),protocol(),jobs(smoke))


PANEL = Panel(sys.modules[__name__])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output",type=Path); mode.add_argument("--verify",type=Path); mode.add_argument("--preflight",type=Path)
    parser.add_argument("--smoke",action="store_true"); parser.add_argument("--resume",action="store_true")
    parser.add_argument("--mechanics",type=Path)
    args = parser.parse_args()
    if args.verify and (args.smoke or args.resume or args.mechanics): parser.error("--verify takes no collection options")
    if args.preflight and (args.smoke or args.resume): parser.error("--preflight is for a new full output")
    result = PANEL.verify(args.verify) if args.verify else PANEL.preflight(args.preflight,args.mechanics) if args.preflight else (
        PANEL.collect(args.output,args.smoke,args.mechanics,args.resume))
    print(json.dumps(result,indent=2))
    if args.output and not result["complete"]: raise SystemExit(1)


if __name__=="__main__": main()
