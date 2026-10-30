"""Paired sensing contrasts; traffic seeds, not frames, are resampling units."""
from itertools import product
import statistics

from research.observation.sumo_sensing import PRESETS
from research.policies.sumo_classical import CONTROLLERS

MEASURES = ("mean_stopped_wait_per_requested_vehicle_s", "p95_accumulated_wait_s", "completed_trips")
SUMMARY_MEASURES = MEASURES+("max_accumulated_wait_s", "final_entry_backlog", "switch_onsets")


def percentile(values, probability):
    values = sorted(values)
    rank = probability*(len(values)-1)
    lo = int(rank)
    return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(rank-lo)


def seed_interval(values, frozen):
    """Enumerate the 64 ordered bootstrap draws for two seeds in each family."""
    groups = [[p["seed"] for p in frozen if p["family"] == family]
              for family in sorted({p["family"] for p in frozen})]
    if any(len(group) != 2 for group in groups):
        return None  # Mechanics smoke is not a scientific sample.
    draws = [list(product(group, repeat=2)) for group in groups]
    averages = [statistics.mean(values[seed] for group in draw for seed in group) for draw in product(*draws)]
    return dict(lower=percentile(averages,.025), upper=percentile(averages,.975), ordered_draws=len(averages))


def summarize(rows, frozen, repeats):
    expected = {(p["seed"], c, f.name, r) for p in frozen for c in CONTROLLERS for f in PRESETS for r in range(repeats)}
    keys = [(r["seed"],r["controller"],r["fault"],r["repeat"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate sensing cells")
    selected = [r for r in rows if r["repeat"] == 0]
    lookup = {(r["seed"],r["controller"],r["fault"]):r["metrics"] for r in selected}
    aggregate = [dict(controller=c, fault=f.name,
        **{m:statistics.mean(r["metrics"][m] for r in selected if r["controller"] == c and r["fault"] == f.name)
           for m in SUMMARY_MEASURES}) for c in CONTROLLERS for f in PRESETS]
    pairs, contrasts = [], []
    definitions = [("fault_minus_clean", c, f.name) for c in CONTROLLERS for f in PRESETS if f.name != "clean"]
    definitions += [("pressure_saving", c, f.name) for c in CONTROLLERS if c != "max_pressure" for f in PRESETS]
    definitions += [("factorial_interaction", c, "delay2s_miss30") for c in CONTROLLERS]
    for kind, controller, fault in definitions:
        by_metric = {m:{} for m in MEASURES}
        for plan in frozen:
            seed = plan["seed"]
            def value(c, f, m):
                return lookup[seed,c,f][m]
            delta = {}
            for m in MEASURES:
                if kind == "fault_minus_clean":
                    amount = value(controller,fault,m)-value(controller,"clean",m)
                elif kind == "pressure_saving":
                    amount = value(controller,fault,m)-value("max_pressure",fault,m)
                    if m == "completed_trips":
                        amount = -amount
                else:
                    amount = value(controller,"delay2s_miss30",m)-value(controller,"delay2s",m)-value(controller,"miss30",m)+value(controller,"clean",m)
                delta[m] = by_metric[m][seed] = amount
            pairs.append(dict(kind=kind, controller=controller, fault=fault, seed=seed, family=plan["family"], **delta))
        contrasts.append(dict(kind=kind, controller=controller, fault=fault,
            metrics={m:dict(mean=statistics.mean(values.values()), interval=seed_interval(values,frozen),
                positive=sum(v>0 for v in values.values()), zero=sum(v==0 for v in values.values()),
                negative=sum(v<0 for v in values.values())) for m,values in by_metric.items()}))
    return dict(aggregate=aggregate, contrasts=contrasts, paired_contrasts=pairs,
        contrast_signs=dict(fault_minus_clean="Fault minus own clean: positive waiting is a cost; positive trips is a gain.",
            pressure_saving="Comparator minus pressure for waiting, pressure minus comparator for trips: positive favours pressure.",
            factorial_interaction="Both minus delay-only minus misses-only plus clean, separately for each metric."),
        uncertainty="Exact stratified traffic-seed bootstrap percentile intervals; only two seeds per family. Descriptive sensitivity, not guaranteed coverage or multiplicity-adjusted superiority. Smoke intervals omitted.")
