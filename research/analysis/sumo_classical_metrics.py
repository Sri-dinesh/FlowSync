"""Independent saved-trace validation and endpoints for executed SUMO baselines."""
from dataclasses import asdict
import math
import statistics

from research.audits.sumo_branch_feasibility import Signal, audit_signals
from research.policies.sumo_classical import Clock, choose_action, observe


def percentile95(values):
    values = sorted(values)
    if not values:
        return 0.
    rank = .95*(len(values)-1)
    lo, hi = math.floor(rank), math.ceil(rank)
    return round(values[lo]+(values[hi]-values[lo])*(rank-lo), 6)


def validate_trace(trace, schedule, controller, axes, steps):
    if len(trace) != steps or [r["tick"] for r in trace] != list(range(steps)):
        raise ValueError("Incomplete or unordered whole-episode trace")
    if len({a[2] for a in schedule}) != len(schedule) or not schedule:
        raise ValueError("Duplicate or empty requested schedule")
    expected = {}
    for arrival in schedule:
        if (len(arrival) != 3 or type(arrival[0]) is not int or not 0 <= arrival[0] < steps
                or arrival[1] not in "nsew" or len(arrival[1]) != 1
                or not isinstance(arrival[2], str) or not arrival[2]):
            raise ValueError("Malformed requested arrival")
        expected.setdefault(arrival[0], []).append(arrival)
    requested, completed, waiting_ticks = set(), set(), {}
    previous_vehicles, previous_pending, signal = [], [], Signal()
    for row in trace:
        tick = row["tick"]
        observe(row["vehicles"])  # Also validate non-decision/last-step snapshots.
        if row["requested"] != expected.get(tick, []):
            raise ValueError("Unpaired requested arrivals")
        if tick % 20 == 0:
            packet = observe(previous_vehicles)
            decision = dict(packet=packet.to_dict(), before_fsm=asdict(signal),
                            proposal=choose_action(controller, packet, Clock(signal.phase, signal.stage, signal.age)))
            if row.get("decision") != decision:
                raise ValueError("Delivered packet or controller proposal does not reconstruct")
            signal.request(decision["proposal"])
        elif "decision" in row:
            raise ValueError("Off-cadence controller decision")
        if row["fsm"] != asdict(signal) or row["lamps"] != signal.lamps(axes):
            raise ValueError("Executed physical FSM does not reconstruct")
        signal.advance()
        new_ids = {a[2] for a in row["requested"]}
        if new_ids & requested:
            raise ValueError("Repeated request")
        requested |= new_ids
        old_backlog = previous_pending+row["requested"]
        inserted = row["inserted"]
        if len(set(inserted)) != len(inserted) or not set(inserted) <= {a[2] for a in old_backlog}:
            raise ValueError("Invalid entry insertion")
        remaining = [a for a in old_backlog if a[2] not in set(inserted)]
        if row["pending"] != remaining:
            raise ValueError("External FIFO not preserved")
        for direction in "nsew":
            queue = [a[2] for a in old_backlog if a[1] == direction]
            admitted = [vid for vid in inserted if vid in set(queue)]
            if len(admitted) > 1 or admitted != queue[:len(admitted)]:
                raise ValueError("Entry FIFO bypass or multiple same-lane insertions")
        active = [v[0] for v in row["vehicles"]]
        done = row["arrived"]
        old_active = {v[0] for v in previous_vehicles}
        if len(active) != len(set(active)) or len(done) != len(set(done)) or set(done) & completed:
            raise ValueError("Duplicate vehicle inventory")
        if set(active) != (old_active | set(inserted))-set(done) or not set(done) <= old_active | set(inserted):
            raise ValueError("Vehicle conservation failed")
        completed.update(done)
        pending = {a[2] for a in row["pending"]}
        if (set(active) & pending or (set(active) | pending) & completed
                or requested != set(active) | pending | completed):
            raise ValueError("Requested/active/pending/completed inventory mismatch")
        stopped = [v[0] for v in row["vehicles"] if v[3] < .1]+list(pending)
        if row["wait_vehicle_seconds"] != round(len(stopped)/10, 6):
            raise ValueError("Stopped waiting does not reconstruct")
        for vid in stopped:
            waiting_ticks[vid] = waiting_ticks.get(vid, 0)+1
        previous_vehicles, previous_pending = row["vehicles"], row["pending"]
    audit_signals(trace, axes)
    waits = [waiting_ticks.get(vid, 0)/10 for vid in sorted(requested)]
    total = sum(waiting_ticks.values())/10
    present = {v[0] for v in previous_vehicles} | {a[2] for a in previous_pending}
    return dict(requested_vehicles=len(requested), completed_trips=len(completed),
                final_active=len(previous_vehicles), final_entry_backlog=len(previous_pending),
                total_stopped_wait_vehicle_seconds=round(total, 6),
                mean_stopped_wait_per_requested_vehicle_s=round(total/len(requested), 6),
                p95_accumulated_wait_s=percentile95(waits), max_accumulated_wait_s=max(waits),
                endpoint_max_active_pending_wait_s=max((waiting_ticks.get(v, 0)/10 for v in present), default=0.),
                signal_samples=steps, decision_samples=(steps+19)//20,
                switch_onsets=sum(r["fsm"]["stage"] == "yellow" and r["fsm"]["age"] == 0 for r in trace),
                measured_signal_violations=0)


def summarize(rows, plans):
    primary = [r for r in rows if r["repeat"] == 0]
    expected = {(p["seed"], c) for p in plans for c in ("halted", "fixed", "max_pressure")}
    keys = [(r["seed"], r["controller"]) for r in primary]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate controller-case cells")
    fields = ("mean_stopped_wait_per_requested_vehicle_s", "p95_accumulated_wait_s", "max_accumulated_wait_s",
              "completed_trips", "final_entry_backlog", "switch_onsets")
    controllers = {c: {k: statistics.mean(r["metrics"][k] for r in primary if r["controller"] == c) for k in fields}
                   for c in ("halted", "fixed", "max_pressure")}
    lookup = {(r["seed"], r["controller"]): r["metrics"] for r in primary}
    contrasts = []
    for first, second in (("max_pressure", "halted"), ("max_pressure", "fixed"), ("halted", "fixed")):
        cases = [dict(seed=p["seed"], family=p["family"],
            mean_wait_saved_s=round(lookup[p["seed"], second][fields[0]]-lookup[p["seed"], first][fields[0]], 6),
            p95_wait_saved_s=round(lookup[p["seed"], second][fields[1]]-lookup[p["seed"], first][fields[1]], 6),
            completed_trips_gained=lookup[p["seed"], first]["completed_trips"]-lookup[p["seed"], second]["completed_trips"])
                 for p in plans]
        contrasts.append(dict(first=first, reference=second, cases=cases,
            mean_wait_saved_s=statistics.mean(r["mean_wait_saved_s"] for r in cases),
            mean_p95_wait_saved_s=statistics.mean(r["p95_wait_saved_s"] for r in cases),
            mean_completed_trips_gained=statistics.mean(r["completed_trips_gained"] for r in cases),
            by_family={family: {key: statistics.mean(r[key] for r in cases if r["family"] == family)
                               for key in ("mean_wait_saved_s", "p95_wait_saved_s", "completed_trips_gained")}
                       for family in sorted({p["family"] for p in plans})}))
    families = {family: {c: {k: statistics.mean(r["metrics"][k] for r in primary
                                               if r["controller"] == c and r["family"] == family) for k in fields}
                         for c in controllers} for family in sorted({p["family"] for p in plans})}
    return dict(controllers=controllers, paired_comparisons=contrasts, families=families)
