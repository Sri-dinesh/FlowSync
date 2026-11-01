"""Frozen history-by-sensing contrasts with traffic-seed resampling units."""
import statistics

from research.analysis.sumo_sensing_metrics import MEASURES, seed_interval


def identity(row):
    return tuple(row[k] for k in ("seed","initial_phase","method","repeat","kind","steps"))


def summarize(rows, frozen, cfg, spec, jobs):
    if [identity(r) for r in rows]!=[identity(j) for j in jobs]:
        raise ValueError("Incomplete, duplicate or reordered history grid")
    if cfg["smoke"]:
        lookup = {(r["initial_phase"],r["method"],r["kind"],r["repeat"]):r for r in rows}
        for phase in (0,1):
            for method in spec["methods"]:
                name = method["name"]
                a,b = (lookup[phase,name,"episode",repeat] for repeat in (0,1))
                if a["semantic_trace_sha256"]!=b["semantic_trace_sha256"]:
                    raise ValueError("Native repeat differs")
                if a["prefix_trace_sha256"]!=lookup[phase,name,"prefix",0]["semantic_trace_sha256"]:
                    raise ValueError("Independent prefix differs from long trajectory")
            for name in ("instant_clean","instant_mixed","lag_clean"):
                new,old = lookup[phase,name,"episode",0],lookup[phase,name,"anchor",0]
                if any(new[k]!=old[k] for k in ("physical_trace_sha256","proposal_trace_sha256")):
                    raise ValueError("Current/lag physics or proposal clock differs from frozen anchor")
                if name!="lag_clean" and new["historical_trace_sha256"]!=old["historical_trace_sha256"]:
                    raise ValueError("Instantaneous delivered stream differs from frozen anchor")
        endpoint = str(cfg["steps"]//10)
        exercised = {name:sum(lookup[phase,name,"episode",0]["measurements"][endpoint]["service"]["history_changed_gates"]
                        for phase in (0,1)) for name in ("mean_clean","mean_mixed")}
        if any(value<1 for value in exercised.values()):
            raise ValueError("Native smoke never exercises a mean/current proposal difference")
        return dict(mechanics=dict(repeats_verified=True,prefix_replays_verified=True,current_anchors_verified=True,
                    lag_physics_and_proposals_verified=True,mean_changed_gates=exercised),candidate_screen=None,endpoint_comparisons={})
    lookup = {(r["seed"],r["initial_phase"],r["method"]):r for r in rows}
    methods = [m["name"] for m in spec["methods"]]
    endpoints = {}
    for end in cfg["endpoint_ticks"]:
        endpoint = str(end//10)
        cells = {key:{**{k:v for k,v in row["measurements"][endpoint].items() if k!="service"},
                      **row["measurements"][endpoint]["service"]} for key,row in lookup.items()}
        for p in frozen:
            for phase in (0,1):
                if len({cells[p["seed"],phase,m]["requested_vehicles"] for m in methods})!=1:
                    raise ValueError("Requested traffic denominator differs between methods")
        means = {m:{key:statistics.mean(cells[p["seed"],phase,m][key] for p in frozen for phase in (0,1))
                    for key in next(iter(cells.values()))} for m in methods}
        seed_means = {str(p["seed"]):{m:{key:statistics.mean(cells[p["seed"],phase,m][key] for phase in (0,1))
                            for key in MEASURES} for m in methods} for p in frozen}
        contrasts = {}
        for definition in spec["contrasts"]:
            terms = definition["terms"]
            contexts = [dict(seed=p["seed"],family=p["family"],initial_phase=phase,
                **{key:sum(weight*cells[p["seed"],phase,m][key] for m,weight in terms.items()) for key in MEASURES})
                for p in frozen for phase in (0,1)]
            by_seed = {key:{p["seed"]:sum(weight*seed_means[str(p["seed"])][m][key] for m,weight in terms.items())
                           for p in frozen} for key in MEASURES}
            def average(selected): return {key:statistics.mean(r[key] for r in selected) for key in MEASURES}
            contrasts[definition["name"]] = dict(terms=terms,
                metrics={key:dict(mean=statistics.mean(values.values()),interval=seed_interval(values,frozen),
                    positive=sum(v>0 for v in values.values()),negative=sum(v<0 for v in values.values()),zero=sum(v==0 for v in values.values()))
                    for key,values in by_seed.items()},
                by_initial_phase={str(phase):average([r for r in contexts if r["initial_phase"]==phase]) for phase in (0,1)},
                by_family={family:average([r for r in contexts if r["family"]==family]) for family in sorted({p["family"] for p in frozen})},
                context_rows=contexts,seed_rows=[dict(seed=p["seed"],family=p["family"],
                    **{key:values[p["seed"]] for key,values in by_seed.items()}) for p in frozen])
        endpoints[endpoint] = dict(primary=end==cfg["steps"],means=means,seed_means=seed_means,contrasts=contrasts)
    primary = endpoints[str(cfg["steps"]//10)]; delay,p95,trips = MEASURES
    failures,comparisons,rule = [],{},spec["candidate_screen"]
    pairs = [(spec["primary_candidate"],ref,rule["minimum_delay_gain_fraction"]) for ref in spec["primary_references"]]
    pairs.append(("mean_mixed","instant_mixed",0.))
    for candidate,reference,minimum in pairs:
        a,b = primary["means"][candidate],primary["means"][reference]
        label = candidate+"_vs_"+reference
        gain = (b[delay]-a[delay])/b[delay] if b[delay]>0 else None
        if gain is None or gain<minimum: failures.append("mean_wait_"+label)
        if a[p95]>b[p95]: failures.append("p95_"+label)
        if a[trips]<b[trips]: failures.append("throughput_"+label)
        limit = rule["maximum_seed_mean_delay_loss_fraction"] if candidate==spec["primary_candidate"] else rule["noise_arm_maximum_seed_loss_fraction"]
        losses = [int(seed) for seed,values in primary["seed_means"].items() if values[candidate][delay]>values[reference][delay]*(1+limit)]
        if losses: failures.append("seed_loss_"+label)
        start_losses = [phase for phase in (0,1) if statistics.mean(lookup[p["seed"],phase,candidate]["measurements"][str(cfg["steps"]//10)][delay]
                      -lookup[p["seed"],phase,reference]["measurements"][str(cfg["steps"]//10)][delay] for p in frozen)>0]
        if start_losses: failures.append("start_group_loss_"+label)
        comparisons[label] = dict(delay_gain_fraction=gain,minimum_delay_gain_fraction=minimum,seed_loss_ids=losses,start_group_loss_ids=start_losses)
    return dict(mechanics=dict(scope="Full study relies on matched verified native smoke"),endpoint_comparisons=endpoints,
        candidate_screen=dict(continue_to_bounded_development=not failures,failures=failures,comparisons=comparisons,
            primary_endpoint_seconds=cfg["steps"]//10,automatic_promotion=False,publication_ready=False,scope=spec["continuation"]),
        replication=dict(traffic_seeds=len(frozen),paired_start_contexts=2*len(frozen),independent_training_replicates=0,prefix_endpoints_overlap=True),
        uncertainty=spec["analysis"])
