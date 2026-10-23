"""Fixed endpoint measurements and traffic-seed hierarchy for robustness runs."""
import statistics

from research.analysis.analyze_sumo_count_ablation import demand_role, profile
from research.experiments.sumo_robustness import CONTROLLERS, jobs, trim_plan, validate_trace
from research.policies.sumo_total_count import policy_for

GLOBAL_FIELDS = ("mean_stopped_wait_per_requested_vehicle_s", "p95_accumulated_wait_s", "max_accumulated_wait_s",
                 "completed_trips", "final_active", "final_entry_backlog", "endpoint_max_active_pending_wait_s", "switch_onsets")
SCORES = ("mean_wait_saved_s", "p95_wait_saved_s", "completed_trips_gained",
          "lower_mean_wait_saved_s", "lower_p95_wait_saved_s", "lower_trips_gained",
          "higher_mean_wait_saved_s", "higher_p95_wait_saved_s", "higher_trips_gained")


def measurements(trace, plan, task, axes, cfg):
    if len(trace) != task["steps"]:
        raise ValueError("Incomplete or extended raw episode")
    values = {}
    for end in cfg["endpoint_ticks"]:
        if end > task["steps"]:
            continue
        clipped = trim_plan(plan, end)
        prefix = trace[:end]
        metrics = validate_trace(prefix, clipped["schedule"], policy_for(task["controller"]), axes, end, task["initial_phase"])
        attributed = profile(prefix, clipped["schedule"])
        if abs(metrics["total_stopped_wait_vehicle_seconds"]-attributed["wait_vehicle_seconds"]) > 1e-6:
            raise ValueError("Axis attribution does not conserve the verified waiting integral")
        values[str(end//10)] = dict(overall=metrics, axes=attributed["axes"],
            signal=dict(seconds=attributed["signal"]["seconds"], switch_onsets=attributed["signal"]["switch_onsets"]))
    return values


def check_mechanics(rows, smoke):
    if not smoke:
        return dict(repeats="smoke_only", prefix_replays="smoke_only")
    lookup = {(r["initial_phase"], r["controller"], r["kind"], r["repeat"]): r for r in rows}
    for phase in (0, 1):
        for controller in CONTROLLERS:
            first = lookup[phase, controller, "episode", 0]
            second = lookup[phase, controller, "episode", 1]
            if first["semantic_trace_sha256"] != second["semantic_trace_sha256"]:
                raise ValueError("Repeated mechanics trajectory differs")
        long = lookup[phase, "max_pressure", "episode", 0]
        short = lookup[phase, "max_pressure", "prefix_replay", 0]
        if short["semantic_trace_sha256"] != long["prefix_semantic_trace_sha256"]:
            raise ValueError("Separate short trajectory differs from the longer-run prefix")
    return dict(repeats="verified", prefix_replays="verified")


def aggregate(cases):
    """Average starts within seed first; frames/starts are not new replicates."""
    if not cases:
        raise ValueError("No paired traffic contexts")
    seeds = []
    for seed in sorted({r["seed"] for r in cases}):
        selected = [r for r in cases if r["seed"] == seed]
        means = {k: statistics.mean(r[k] for r in selected if r[k] is not None)
                 if any(r[k] is not None for r in selected) else None for k in SCORES}
        seeds.append(dict(seed=seed, initial_phase_contexts=len(selected), mean=means))
    means = {k: statistics.mean(r["mean"][k] for r in seeds if r["mean"][k] is not None)
             if any(r["mean"][k] is not None for r in seeds) else None for k in SCORES}
    directions = {}
    for key in SCORES:
        values = [r["mean"][key] for r in seeds if r["mean"][key] is not None]
        directions[key] = dict(traffic_seeds=len(values), improved=sum(v > 0 for v in values),
                               equal=sum(v == 0 for v in values), worsened=sum(v < 0 for v in values))
    return dict(traffic_seeds=len(seeds), paired_start_contexts=len(cases), mean=means,
                seed_direction_counts=directions, seed_results=seeds)


def summarize(rows, frozen, cfg):
    keys = [(r["seed"], r["initial_phase"], r["controller"], r["kind"], r["repeat"]) for r in rows]
    expected = [(r["seed"], r["initial_phase"], r["controller"], r["kind"], r["repeat"]) for r in jobs(cfg["smoke"])]
    if len(set(keys)) != len(keys) or set(keys) != set(expected):
        raise ValueError("Incomplete/duplicate robustness cells")
    if cfg["smoke"]:
        return dict(endpoint_comparisons={}, sensitivity={})
    lookup = {(r["seed"], r["initial_phase"], r["controller"]): r for r in rows}
    endpoints = {}
    for end in cfg["endpoint_ticks"]:
        endpoint = str(end//10)
        cases = []
        for plan in frozen:
            for phase in cfg["initial_phases"]:
                total, pressure = (lookup[plan["seed"], phase, c]["measurements"][endpoint] for c in ("total_incoming", "max_pressure"))
                a, b = total["overall"], pressure["overall"]
                if a["requested_vehicles"] != b["requested_vehicles"]:
                    raise ValueError("Unpaired requested-vehicle denominator")
                case = dict(seed=plan["seed"], family=plan["family"], initial_phase=phase,
                    mean_wait_saved_s=round(b[GLOBAL_FIELDS[0]]-a[GLOBAL_FIELDS[0]], 6),
                    p95_wait_saved_s=round(b[GLOBAL_FIELDS[1]]-a[GLOBAL_FIELDS[1]], 6),
                    completed_trips_gained=a["completed_trips"]-b["completed_trips"])
                case.update({k: None for k in SCORES[3:]})
                axes = {}
                for axis in ("ns", "ew"):
                    x, y = total["axes"][axis], pressure["axes"][axis]
                    role = demand_role(plan, axis)
                    axes[axis] = dict(role=role, mean_wait_saved_s=y["mean_wait_s"]-x["mean_wait_s"],
                        p95_wait_saved_s=round(y["p95_wait_s"]-x["p95_wait_s"], 6),
                        completed_trips_gained=x["completed_trips"]-y["completed_trips"])
                    if role != "balanced":
                        prefix = "lower" if role == "lower_demand" else "higher"
                        for field, key in (("mean_wait_saved_s", "mean_wait_saved_s"),
                                           ("p95_wait_saved_s", "p95_wait_saved_s"), ("trips_gained", "completed_trips_gained")):
                            case[f"{prefix}_{field}"] = axes[axis][key]
                case["axis_results"] = axes
                cases.append(case)
        controller_means = {}
        for controller in CONTROLLERS:
            selected = [r["measurements"][endpoint] for r in rows if r["controller"] == controller]
            controller_means[controller] = dict(overall={k: statistics.mean(r["overall"][k] for r in selected) for k in GLOBAL_FIELDS},
                axes={axis: {k: statistics.mean(r["axes"][axis][k] for r in selected) for k in selected[0]["axes"][axis]}
                      for axis in ("ns", "ew")})
        phase_means = {str(p): aggregate([r for r in cases if r["initial_phase"] == p]) for p in cfg["initial_phases"]}
        endpoints[endpoint] = dict(endpoint_seconds=end//10, primary=end == cfg["steps"],
            controller_means=controller_means, aggregate=aggregate(cases), by_initial_phase=phase_means,
            by_family={f: aggregate([r for r in cases if r["family"] == f]) for f in sorted({r["family"] for r in cases})},
            case_results=cases,
            initial_phase_mean_wait_sign_changes=[p["seed"] for p in frozen if
                lookup_mean(cases, p["seed"], 0)*lookup_mean(cases, p["seed"], 1) < 0])
    first, last = (endpoints[str(end//10)]["aggregate"]["seed_results"] for end in (cfg["endpoint_ticks"][0], cfg["steps"]))
    sensitivity = dict(seed_mean_wait_sign_changes_between_endpoints=[a["seed"] for a, b in zip(first, last)
        if a["mean"]["mean_wait_saved_s"]*b["mean"]["mean_wait_saved_s"] < 0],
        prefix_is_overlapping=True, independent_traffic_seeds=len(frozen))
    return dict(endpoint_comparisons=endpoints, sensitivity=sensitivity)


def lookup_mean(cases, seed, phase):
    return next(r["mean_wait_saved_s"] for r in cases if r["seed"] == seed and r["initial_phase"] == phase)
