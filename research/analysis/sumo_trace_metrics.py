"""Saved SUMO trace measurements; no simulator, fitting or policy execution."""
from collections import Counter
import math

DIRECTIONS = ("n", "s", "e", "w")
AXIS = {"n": 0, "s": 0, "e": 1, "w": 1}
OPPOSITE = {"n": "s", "s": "n", "e": "w", "w": "e"}
WINDOWS = (0, 20, 40, 60, 120, 200, 300, 400)


def best_phase(values, current):
    return current if values[current] == max(values) else int(values[1] > values[0])


def gate_features(prefix, lane_lengths):
    """Use only the final PRE-action sample; future keys/rates/IDs are not features."""
    if not prefix:
        raise ValueError("Missing pre-action history")
    last = prefix[-1]
    fsm = last["fsm"]
    if fsm["stage"] != "green" or fsm["age"]+1 < 80 or (last["tick"]+1) % 20:
        raise ValueError("Not an eligible green decision")
    incoming, outgoing, halted, moving, near, eta = (Counter() for _ in range(6))
    for _vid, edge, position, speed in last["vehicles"]:
        if not all(math.isfinite(v) for v in (position, speed)) or speed < 0:
            raise ValueError("Invalid saved vehicle kinematics")
        if edge in {f"{d}_in" for d in DIRECTIONS}:
            direction = edge[0]
            distance = lane_lengths[edge]-position
            if distance < -1e-6:
                raise ValueError("Vehicle beyond its recorded incoming lane")
            incoming[direction] += 1
            halted[direction] += speed < .1
            moving[direction] += speed >= .1
            near[direction] += distance <= 30
            # Exploratory geometric proxy; not a calibrated arrival prediction.
            eta[direction] += speed >= .1 and distance/max(speed, .1) <= 4
        elif edge in {f"{d}_out" for d in DIRECTIONS}:
            outgoing[edge[0]] += 1
    aggregate = lambda values: [sum(values[d] for d in pair) for pair in ("ns", "ew")]
    pressure = [sum(max(0, incoming[d]-outgoing[OPPOSITE[d]]) for d in pair) for pair in ("ns", "ew")]
    current = fsm["phase"]
    queues = aggregate(halted)
    counts = aggregate(incoming)
    return dict(current_phase=current, green_age_s=(fsm["age"]+1)/10,
                halted=queues, incoming=counts, moving=aggregate(moving), near_30m=aggregate(near),
                geometric_eta_le_4s=aggregate(eta), outgoing_by_direction={d: outgoing[d] for d in DIRECTIONS},
                raw_pressure=pressure, halted_proposal=best_phase(queues, current),
                total_count_shadow_proposal=best_phase(counts, current),
                pressure_shadow_proposal=best_phase(pressure, current),
                evaluation_only_entry_backlog=len(last["pending"]))


def origin_map(prefix, future_arrivals):
    """Evaluation-only route attribution, independent of ID spelling or future rates."""
    result = {}
    for _, direction, vid in [a for r in prefix for a in r["requested"]]+future_arrivals:
        if direction not in DIRECTIONS or vid in result:
            raise ValueError("Invalid or duplicate requested vehicle")
        result[vid] = direction
    return result


def wait_partition(trace, origins, present_at_gate):
    if not trace or len(trace) > WINDOWS[-1]:
        raise ValueError("Requires a nonempty branch of at most forty seconds")
    origin_ticks, location_ticks, cohort_ticks, window_ticks = (Counter() for _ in range(4))
    cumulative, stopped_ticks = [], 0
    first = trace[0]["tick"]
    for index, row in enumerate(trace):
        if row["tick"] != first+index:
            raise ValueError("Missing or unordered trace tick")
        ids = [v[0] for v in row["vehicles"]]+[v[2] for v in row["pending"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate active/pending vehicle")
        stopped = [(v[0], "incoming" if v[1].endswith("_in") else "outgoing" if v[1].endswith("_out") else "internal")
                   for v in row["vehicles"] if v[3] < .1]
        stopped += [(v[2], "entry_backlog") for v in row["pending"]]
        if round(len(stopped)/10, 6) != row["wait_vehicle_seconds"]:
            raise ValueError("Recorded stopped-wait increment differs from vehicles/backlog")
        window = next(i for i, end in enumerate(WINDOWS[1:]) if index < end)
        for vid, location in stopped:
            if vid not in origins:
                raise ValueError("Stopped vehicle has no preserved demand origin")
            origin_ticks[origins[vid]] += 1
            location_ticks[location] += 1
            cohort_ticks["present_at_gate" if vid in present_at_gate else "arrived_after_gate"] += 1
        window_ticks[window] += len(stopped)
        stopped_ticks += len(stopped)
        cumulative.append(stopped_ticks/10)
    if any(sum(values.values()) != stopped_ticks for values in (origin_ticks, location_ticks, cohort_ticks, window_ticks)):
        raise ValueError("Waiting partition does not conserve total delay")
    return dict(total=stopped_ticks/10,
                by_origin={d: origin_ticks[d]/10 for d in DIRECTIONS},
                by_location={k: location_ticks[k]/10 for k in ("incoming", "outgoing", "internal", "entry_backlog")},
                by_cohort={k: cohort_ticks[k]/10 for k in ("present_at_gate", "arrived_after_gate")},
                by_window=[window_ticks[i]/10 for i in range(len(WINDOWS)-1)], cumulative=cumulative)


def signal_partition(trace):
    counts, runs = Counter(), []
    for row in trace:
        stage, phase = row["fsm"]["stage"], row["fsm"]["phase"]
        counts[stage] += 1
        if stage == "green":
            counts[f"green_{phase}"] += 1
        if not runs or (stage, phase) != (runs[-1]["stage"], runs[-1]["phase"]):
            runs.append(dict(stage=stage, phase=phase, start_tick=row["tick"], ticks=1))
        else:
            runs[-1]["ticks"] += 1
    if sum(counts[k] for k in ("green", "yellow", "red")) != len(trace):
        raise ValueError("Unexpected recorded signal stage")
    return dict(seconds={k: counts[k]/10 for k in ("green", "yellow", "red", "green_0", "green_1")},
                switch_onsets=sum(r["stage"] == "yellow" for r in runs), runs=runs)
