"""Predeclared ledger contrasts with traffic seeds as the resampling units."""
from itertools import product
import math

from research.analysis.sumo_sensing_metrics import MEASURES, percentile
from research.pilots.run_sumo_switching_panel import digest

SUMMARY_MEASURES = MEASURES + ("max_accumulated_wait_s", "final_active", "final_entry_backlog",
    "endpoint_max_active_pending_wait_s", "switch_onsets")


def mean(values):
    values = list(values)
    return math.fsum(values)/len(values)


def seed_interval(values, frozen):
    groups = [[p["seed"] for p in frozen if p["family"] == family]
              for family in sorted({p["family"] for p in frozen})]
    if len(groups) != 3 or any(len(group) != 2 for group in groups):
        raise ValueError("The declared analysis requires two seeds in each of three families")
    draws = [mean(values[seed] for group in draw for seed in group)
             for draw in product(*(list(product(group, repeat=2)) for group in groups))]
    return dict(lower=percentile(draws, .025), upper=percentile(draws, .975), ordered_draws=len(draws))


def identity(row):
    return tuple(row[k] for k in ("seed", "initial_phase", "method", "repeat", "kind", "steps"))


def mechanics(rows, cfg, spec):
    lookup = {(r["initial_phase"], r["method"], r["kind"], r["repeat"]):r for r in rows}
    end, credits = str(cfg["steps"]//10), {}
    for phase in (0, 1):
        for method in spec["methods"]:
            name = method["name"]
            first = lookup[phase, name, "episode", 0]
            if first["prefix_trace_sha256"] != lookup[phase, name, "prefix", 0]["semantic_trace_sha256"]:
                raise ValueError("Independent native prefix differs from the long trajectory")
            if method["mode"] in ("ledger", "watchdog"):
                if first["semantic_trace_sha256"] != lookup[phase, name, "episode", 1]["semantic_trace_sha256"]:
                    raise ValueError("Primary/watchdog native repeat differs")
            if method["mode"] == "ledger":
                a = first["measurements"][end]["allocation"]
                if min(a["credited_green_ticks"], a["completed_batches"]) <= 0:
                    raise ValueError("Native smoke never credits and completes a primary batch")
                credits[str(phase)+"_"+name] = dict(credited_green_ticks=a["credited_green_ticks"], completed_batches=a["completed_batches"])
    return dict(mechanics=dict(primary_and_watchdog_repeats_verified=True, all_prefix_replays_verified=True,
        original_mp_uses_frozen_adapter=True, primary_receipts=credits,
        scope="Execution/provenance checks only; smoke outcomes cannot select parameters or performance endpoints"),
        candidate_screen=None, endpoint_comparisons={}, performance_evaluated=False)


def summarize(rows, frozen, cfg, spec, jobs):
    if [identity(r) for r in rows] != [identity(j) for j in jobs]:
        raise ValueError("Incomplete, duplicate or reordered ledger panel grid")
    plans = {p["seed"]:p for p in frozen}
    for row in rows:
        plan = plans[row["seed"]]
        expected_arrivals = digest([a for a in plan["schedule"] if a[0] < row["steps"]])
        if row["requested_arrival_sha256"] != expected_arrivals:
            raise ValueError("Requested arrivals differ from the frozen paired schedule")
        for end, measured in row["measurements"].items():
            if measured["measured_signal_violations"] != 0 or measured["signal_samples"] != int(end)*10:
                raise ValueError("Signal audit/sample coverage differs")
    if cfg["smoke"]:
        return mechanics(rows, cfg, spec)
    lookup = {(r["seed"], r["initial_phase"], r["method"]):r for r in rows}
    methods = [m["name"] for m in spec["methods"]]
    endpoints = {}
    for end in cfg["endpoint_ticks"]:
        endpoint = str(end//10)
        cells = {key:r["measurements"][endpoint] for key, r in lookup.items()}
        for p in frozen:
            for phase in (0, 1):
                expected = len([a for a in p["schedule"] if a[0] < end])
                if any(cells[p["seed"], phase, m]["requested_vehicles"] != expected for m in methods):
                    raise ValueError("Requested-vehicle denominator differs between controls or schedule")
        for cell in cells.values():
            if any(type(cell[k]) not in (int, float) or not math.isfinite(cell[k]) or cell[k] < 0 for k in SUMMARY_MEASURES):
                raise ValueError("Invalid nonfinite or negative traffic measurement")
        means = {m:{k:mean(cells[p["seed"], phase, m][k] for p in frozen for phase in (0, 1))
                    for k in SUMMARY_MEASURES} for m in methods}
        diagnostic_means = {m:{k:mean(cells[p["seed"], phase, m]["diagnostics"][k] for p in frozen for phase in (0, 1))
                              for k in cells[frozen[0]["seed"], 0, m]["diagnostics"]} for m in methods}
        seed_means = {str(p["seed"]):{m:{k:mean(cells[p["seed"], phase, m][k] for phase in (0, 1)) for k in MEASURES}
                      for m in methods} for p in frozen}
        definitions = {}
        for label in ("clean", "mixed"):
            definitions.update({"ledger_vs_"+ref+"_"+label:{"ledger_"+label:1, ref+"_"+label:-1}
                                for ref in spec["gain_references"]+spec["nonloss_references"]})
            definitions["debt_priority_by_variable_budget_"+label] = {
                "ledger_"+label:1, "pressure_budget_"+label:-1, "debt_batch_"+label:-1, "pressure_batch_"+label:1}
        contrasts = {}
        for name, terms in definitions.items():
            contexts = [dict(seed=p["seed"], family=p["family"], initial_phase=phase,
                **{k:math.fsum(weight*cells[p["seed"], phase, m][k] for m, weight in terms.items()) for k in MEASURES})
                for p in frozen for phase in (0, 1)]
            values = {k:{p["seed"]:math.fsum(weight*seed_means[str(p["seed"])][m][k] for m, weight in terms.items())
                         for p in frozen} for k in MEASURES}
            contrasts[name] = dict(terms=terms, sign="Candidate minus comparator; negative waiting and positive trips favor candidate. Interaction is an additive difference of differences, not a benefit score.",
                metrics={k:dict(mean=mean(v.values()), interval=seed_interval(v, frozen),
                    positive=sum(x > 0 for x in v.values()), negative=sum(x < 0 for x in v.values()), zero=sum(x == 0 for x in v.values()))
                    for k, v in values.items()}, context_rows=contexts,
                seed_rows=[dict(seed=p["seed"], family=p["family"], **{k:v[p["seed"]] for k, v in values.items()}) for p in frozen],
                by_initial_phase={str(phase):{k:mean(r[k] for r in contexts if r["initial_phase"] == phase) for k in MEASURES}
                                  for phase in (0, 1)},
                by_family={family:{k:mean(r[k] for r in contexts if r["family"] == family) for k in MEASURES}
                           for family in sorted({p["family"] for p in frozen})})
        endpoints[endpoint] = dict(primary=end == cfg["steps"], means=means, diagnostic_means=diagnostic_means,
                                   seed_means=seed_means, contrasts=contrasts)
    primary = endpoints[str(cfg["steps"]//10)]
    delay, p95, trips = MEASURES
    failures, comparisons = [], {}
    for label in ("clean", "mixed"):
        candidate = "ledger_"+label
        for ref in spec["gain_references"]+spec["nonloss_references"]:
            reference, name = ref+"_"+label, "ledger_vs_"+ref+"_"+label
            a, b = primary["means"][candidate], primary["means"][reference]
            minimum = spec["candidate_screen"]["minimum_delay_gain_fraction"] if ref in spec["gain_references"] else 0
            gain = (b[delay]-a[delay])/b[delay] if b[delay] > 0 else None
            if gain is None or gain < minimum: failures.append("mean_wait_"+name)
            if a[p95] > b[p95]: failures.append("p95_"+name)
            if a[trips] < b[trips]: failures.append("throughput_"+name)
            losses = [int(seed) for seed, v in primary["seed_means"].items()
                      if v[candidate][delay] > v[reference][delay]*(1+spec["candidate_screen"]["maximum_seed_mean_delay_loss_fraction"])]
            if losses: failures.append("seed_loss_"+name)
            starts = [phase for phase in (0, 1) if mean(
                lookup[p["seed"], phase, candidate]["measurements"][str(cfg["steps"]//10)][delay]
                -lookup[p["seed"], phase, reference]["measurements"][str(cfg["steps"]//10)][delay] for p in frozen) > 0]
            if starts: failures.append("start_group_loss_"+name)
            comparisons[name] = dict(delay_gain_fraction=gain, minimum_delay_gain_fraction=minimum,
                seed_loss_ids=losses, start_group_loss_ids=starts)
    return dict(mechanics=dict(scope="Full study requires matching source/runtime/topology native smoke"),
        endpoint_comparisons=endpoints, performance_evaluated=True,
        candidate_screen=dict(continue_to_bounded_development=not failures, failures=failures, comparisons=comparisons,
            primary_endpoint_seconds=cfg["steps"]//10, automatic_promotion=False, publication_ready=False, scope=spec["continuation"]),
        replication=dict(traffic_seeds=len(frozen), paired_start_contexts=2*len(frozen), independent_training_replicates=0,
            prefix_endpoints_overlap=True, requested_arrivals_paired=True), uncertainty=spec["analysis"])
