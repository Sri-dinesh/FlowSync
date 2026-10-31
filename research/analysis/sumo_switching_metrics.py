"""Seed-level contrasts retain starts, overlapping endpoints and unfavorable cases."""
import statistics

from research.analysis.sumo_sensing_metrics import MEASURES, seed_interval
from research.experiments.sumo_switching import configuration, jobs, protocol


def identity(row):
    return tuple(row[k] for k in ("seed", "initial_phase", "method", "repeat", "kind", "steps"))


def mechanics(rows, smoke):
    if [identity(r) for r in rows] != [identity(j) for j in jobs(smoke)]:
        raise ValueError("Incomplete, reordered or duplicate frozen jobs")
    if not smoke:
        return dict(scope="Full study relies on its verified smoke; no extra independent replicates")
    lookup = {(r["initial_phase"], r["method"], r["kind"], r["repeat"]): r for r in rows}
    for phase in (0, 1):
        for m in configuration(True)["methods"]:
            a, b = (lookup[phase, m["name"], "episode", repeat] for repeat in (0, 1))
            if a["semantic_trace_sha256"] != b["semantic_trace_sha256"]:
                raise ValueError("Repeated native trajectory differs")
        fixed = {lookup[phase, m, "episode", repeat]["physical_trace_sha256"]
                 for m in ("fixed_clean", "fixed_mixed") for repeat in (0, 1)}
        if len(fixed) != 1:
            raise ValueError("Fixed traffic depends on sensing faults")
        for m in protocol()["methods"]:
            long = lookup[phase, m["name"], "episode", 0]
            short = lookup[phase, m["name"], "prefix", 0]
            if long["prefix_trace_sha256"] != short["semantic_trace_sha256"]:
                raise ValueError("Independent short replay differs from long-run prefix")
    for name in ("pressure_clean", "pressure_mixed"):
        if lookup[0, name, "anchor", 0]["historical_trace_sha256"] != lookup[0, name, "episode", 0]["historical_trace_sha256"]:
            raise ValueError("Zero-margin NS runtime differs from frozen sensing engine")
    end = str(configuration(True)["steps"]//10)
    held = sum(lookup[phase, "pressure_margin1", "episode", 0]["measurements"][end]["service"]["margin_held_gates"]
               for phase in (0, 1))
    if held < 1:
        raise ValueError("Native smoke never exercises the margin-held branch")
    return dict(repeats_verified=True, fixed_fault_invariance=True, prefix_replays_verified=True,
                historical_ns_anchors_verified=True, margin_held_gates=held, science_scope=False)


def flat(measured):
    return {**{key: value for key, value in measured.items() if key not in ("service", "sensing")},
            **measured["service"]}


def summarize(rows, frozen, smoke=False):
    checked = mechanics(rows, smoke)
    if smoke:
        return dict(mechanics=checked, endpoint_comparisons={}, candidate_screen=None)
    cfg, spec = configuration(), protocol()
    lookup = {(r["seed"], r["initial_phase"], r["method"]): r for r in rows}
    endpoints = {}
    for end in cfg["endpoint_ticks"]:
        endpoint = str(end//10)
        cells = {key: flat(row["measurements"][endpoint]) for key, row in lookup.items()}
        for plan in frozen:
            for phase in cfg["initial_phases"]:
                if len({cells[plan["seed"], phase, m["name"]]["requested_vehicles"] for m in cfg["methods"]}) != 1:
                    raise ValueError("Unpaired requested-vehicle denominator")
        means = {m["name"]: {key: statistics.mean(cells[p["seed"], phase, m["name"]][key]
                    for p in frozen for phase in cfg["initial_phases"])
                    for key in next(iter(cells.values()))} for m in cfg["methods"]}
        seed_means = {str(p["seed"]): {m["name"]: {key: statistics.mean(cells[p["seed"], phase, m["name"]][key]
                    for phase in cfg["initial_phases"]) for key in MEASURES}
                    for m in cfg["methods"]} for p in frozen}
        contrasts = {}
        for definition in spec["contrasts"]:
            candidate, reference = definition["candidate"], definition["reference"]
            contexts = [dict(seed=p["seed"], family=p["family"], initial_phase=phase,
                **{key: cells[p["seed"], phase, candidate][key]-cells[p["seed"], phase, reference][key] for key in MEASURES})
                for p in frozen for phase in cfg["initial_phases"]]
            by_seed = {key: {p["seed"]: seed_means[str(p["seed"])][candidate][key]-seed_means[str(p["seed"])][reference][key]
                            for p in frozen} for key in MEASURES}
            def average(selected):
                return {key: statistics.mean(r[key] for r in selected) for key in MEASURES}
            contrasts[definition["name"]] = dict(candidate=candidate, reference=reference,
                metrics={key: dict(mean=statistics.mean(values.values()), interval=seed_interval(values, frozen),
                    positive=sum(v > 0 for v in values.values()), zero=sum(v == 0 for v in values.values()),
                    negative=sum(v < 0 for v in values.values())) for key, values in by_seed.items()},
                by_initial_phase={str(phase): average([r for r in contexts if r["initial_phase"] == phase]) for phase in (0, 1)},
                by_family={family: average([r for r in contexts if r["family"] == family]) for family in sorted({p["family"] for p in frozen})},
                context_rows=contexts, seed_rows=[dict(seed=p["seed"], family=p["family"],
                    **{key: values[p["seed"]] for key, values in by_seed.items()}) for p in frozen])
        endpoints[endpoint] = dict(primary=end == cfg["steps"], means=means, seed_means=seed_means, contrasts=contrasts)
    primary = endpoints[str(cfg["steps"]//10)]
    candidate, failures, comparisons = primary["means"]["pressure_margin1"], [], {}
    rule = spec["candidate_screen"]
    delay, p95, trips = MEASURES
    for reference in ("pressure_clean", "pressure_mixed"):
        base = primary["means"][reference]
        gain = (base[delay]-candidate[delay])/base[delay] if base[delay] > 0 else None
        if gain is None or gain < rule["minimum_delay_gain_fraction_against_both"]: failures.append(f"delay_gain_vs_{reference}")
        if candidate[p95] > base[p95]: failures.append(f"p95_vs_{reference}")
        if candidate[trips] < base[trips]: failures.append(f"throughput_vs_{reference}")
        seed_losses = []
        for seed, values in primary["seed_means"].items():
            a, b = values["pressure_margin1"][delay], values[reference][delay]
            if a > b * (1 + rule["maximum_seed_mean_delay_loss_fraction"]): seed_losses.append(int(seed))
        if seed_losses: failures.append(f"seed_mean_loss_vs_{reference}")
        contrast = primary["contrasts"]["margin_minus_clean" if reference == "pressure_clean" else "margin_minus_mixed"]
        if any(values[delay] > 0 for values in contrast["by_initial_phase"].values()): failures.append(f"start_group_loss_vs_{reference}")
        comparisons[reference] = dict(delay_gain_fraction=gain, seed_loss_ids=seed_losses)
    screen = dict(continue_to_bounded_mechanism_development=not failures, failures=failures,
                  comparisons=comparisons, primary_endpoint_seconds=cfg["steps"]//10,
                  scope=spec["screen_scope"], automatic_promotion=False, publication_ready=False)
    return dict(mechanics=checked, endpoint_comparisons=endpoints, candidate_screen=screen,
        replication=dict(traffic_seeds=len(frozen), paired_start_contexts=len(frozen)*2, independent_training_replicates=0,
                         prefix_endpoints_overlap=True),
        contrast_direction="Candidate minus reference. Negative waiting favours candidate; positive completed trips favours candidate.",
        uncertainty="Average starts within traffic seed. Exact 64-draw family-stratified percentile bootstrap; two seeds per known family, descriptive and not multiplicity-adjusted.")
