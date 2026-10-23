"""All-case comparisons for the declared total-count ablation; no selection gate."""
import statistics

from research.analysis.analyze_sumo_classical_panel import contrast_summary

FIELDS = ("mean_stopped_wait_per_requested_vehicle_s", "p95_accumulated_wait_s", "max_accumulated_wait_s",
          "completed_trips", "final_active", "final_entry_backlog", "endpoint_max_active_pending_wait_s", "switch_onsets")


def summarize(rows, reference_rows, plans, smoke):
    if smoke:
        return dict(controller_means={}, comparisons=[])
    expected = {(p["seed"], "total_incoming", 0) for p in plans}
    keys = [(r["seed"], r["controller"], r["repeat"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate total-count cases")
    old = [r for r in reference_rows if r["repeat"] == 0]
    old_keys = [(r["seed"], r["controller"]) for r in old]
    if len(set(old_keys)) != len(old_keys) or set(old_keys) != {
            (p["seed"], c) for p in plans for c in ("halted", "fixed", "max_pressure")}:
        raise ValueError("Incomplete/duplicate reference cases")
    combined = old+rows
    lookup = {(r["seed"], r["controller"]): r["metrics"] for r in combined}
    means = {c: {k: statistics.mean(r["metrics"][k] for r in combined if r["controller"] == c) for k in FIELDS}
             for c in ("halted", "fixed", "max_pressure", "total_incoming")}
    comparisons = []
    for reference in ("max_pressure", "halted", "fixed"):
        cases = []
        for plan in plans:
            total, old = lookup[plan["seed"], "total_incoming"], lookup[plan["seed"], reference]
            if total["requested_vehicles"] != old["requested_vehicles"]:
                raise ValueError("Requested vehicle denominator differs")
            cases.append(dict(seed=plan["seed"], family=plan["family"],
                mean_wait_saved_s=round(old[FIELDS[0]]-total[FIELDS[0]], 6),
                p95_wait_saved_s=round(old[FIELDS[1]]-total[FIELDS[1]], 6),
                completed_trips_gained=total["completed_trips"]-old["completed_trips"],
                final_active_reduced=old["final_active"]-total["final_active"],
                final_entry_backlog_reduced=old["final_entry_backlog"]-total["final_entry_backlog"],
                endpoint_wait_saved_s=round(old["endpoint_max_active_pending_wait_s"]-total["endpoint_max_active_pending_wait_s"], 6)))
        summary = contrast_summary(cases)
        mean_reference = means[reference][FIELDS[0]]
        comparisons.append(dict(first="total_incoming", reference=reference, primary=reference == "max_pressure",
            **summary, case_results=cases,
            mean_wait_reduction_percent=100*(1-means["total_incoming"][FIELDS[0]]/mean_reference) if mean_reference else None,
            by_family={family: contrast_summary([r for r in cases if r["family"] == family])
                       for family in sorted({p["family"] for p in plans})}))
    return dict(controller_means=means, comparisons=comparisons)
