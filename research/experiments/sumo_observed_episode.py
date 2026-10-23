"""Callback-based delivered-count episodes; frozen physical stepping is reused.

The completed classical runner/checker remain unchanged for provenance. This
adapter permits a new policy while retaining their packet and metric contract.
"""
from dataclasses import asdict

from research.analysis.sumo_classical_metrics import percentile95
from research.audits.sumo_branch_feasibility import Signal, advance, audit_signals
from research.policies.sumo_classical import Clock, observe


def proposal_for(policy, packet, signal):
    proposal = policy(packet, Clock(signal.phase, signal.stage, signal.age))
    if type(proposal) is not int or proposal not in (0, 1):
        raise ValueError("Policy must propose a valid integer phase")
    return proposal


def episode(conn, axes, plan, policy, budget):
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("A fresh empty simulation is required")
    signal, backlog, previous, requests = Signal(), [], [], {}
    for request in plan["schedule"]:
        requests.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        proposal, decision = None, None
        if tick % 20 == 0:
            packet = observe(previous)
            proposal = proposal_for(policy, packet, signal)
            decision = dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
        row, backlog = advance(conn, signal, axes, tick, requests.get(tick, []), backlog, first_action=proposal)
        if decision is not None:
            row["decision"] = decision
        previous = row["vehicles"]
        yield row


def validate_trace(trace, schedule, policy, axes, steps):
    """Reconstruct raw packet/proposal, physical state, inventory and waiting."""
    if len(trace) != steps or [r["tick"] for r in trace] != list(range(steps)):
        raise ValueError("Incomplete or unordered episode")
    expected = {}
    for request in schedule:
        if (len(request) != 3 or type(request[0]) is not int or not 0 <= request[0] < steps
                or request[1] not in ("n", "s", "e", "w") or not isinstance(request[2], str) or not request[2]):
            raise ValueError("Malformed requested arrival")
        expected.setdefault(request[0], []).append(request)
    if not schedule or len({a[2] for a in schedule}) != len(schedule):
        raise ValueError("Empty or duplicate requested vehicles")
    signal, previous, pending, requested, completed, waits = Signal(), [], [], set(), set(), {}
    for row in trace:
        tick = row["tick"]
        observe(row["vehicles"])
        if row["requested"] != expected.get(tick, []):
            raise ValueError("Changed paired requested schedule")
        if tick % 20 == 0:
            packet = observe(previous)
            proposal = proposal_for(policy, packet, signal)
            decision = dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
            if row.get("decision") != decision:
                raise ValueError("Delivered packet or policy proposal does not reconstruct")
            signal.request(proposal)
        elif "decision" in row:
            raise ValueError("Off-cadence policy decision")
        if row["fsm"] != asdict(signal) or row["lamps"] != signal.lamps(axes):
            raise ValueError("Executed physical signal does not reconstruct")
        signal.advance()
        new_ids = {a[2] for a in row["requested"]}
        if new_ids & requested:
            raise ValueError("Repeated request")
        requested |= new_ids
        queue = pending+row["requested"]
        inserted, done = row["inserted"], row["arrived"]
        admitted = set(inserted)
        if len(admitted) != len(inserted) or not admitted <= {a[2] for a in queue}:
            raise ValueError("Invalid entry insertion")
        if row["pending"] != [a for a in queue if a[2] not in admitted]:
            raise ValueError("External entry FIFO changed")
        for direction in "nsew":
            lane_queue = [a[2] for a in queue if a[1] == direction]
            entered = [vid for vid in inserted if vid in set(lane_queue)]
            if len(entered) > 1 or entered != lane_queue[:len(entered)]:
                raise ValueError("Entry FIFO bypass or multiple same-lane insertions")
        active = [v[0] for v in row["vehicles"]]
        before = {v[0] for v in previous} | admitted
        if (len(set(active)) != len(active) or len(set(done)) != len(done) or set(done) & completed
                or not set(done) <= before or set(active) != before-set(done)):
            raise ValueError("Vehicle conservation failed")
        completed.update(done)
        pending = row["pending"]
        queued = {a[2] for a in pending}
        if (set(active) & queued or (set(active) | queued) & completed
                or requested != set(active) | queued | completed):
            raise ValueError("Requested/active/pending/completed inventory mismatch")
        stopped = [v[0] for v in row["vehicles"] if v[3] < .1]+list(queued)
        if row["wait_vehicle_seconds"] != round(len(stopped)/10, 6):
            raise ValueError("Stopped waiting does not reconstruct")
        for vid in stopped:
            waits[vid] = waits.get(vid, 0)+1
        previous = row["vehicles"]
    audit_signals(trace, axes)
    total = sum(waits.values())/10
    values = [waits.get(vid, 0)/10 for vid in sorted(requested)]
    present = {v[0] for v in previous} | {a[2] for a in pending}
    return dict(requested_vehicles=len(requested), completed_trips=len(completed),
        final_active=len(previous), final_entry_backlog=len(pending),
        total_stopped_wait_vehicle_seconds=round(total, 6),
        mean_stopped_wait_per_requested_vehicle_s=round(total/len(requested), 6),
        p95_accumulated_wait_s=percentile95(values), max_accumulated_wait_s=max(values),
        endpoint_max_active_pending_wait_s=max((waits.get(v, 0)/10 for v in present), default=0.),
        signal_samples=steps, decision_samples=(steps+19)//20,
        switch_onsets=sum(r["fsm"]["stage"] == "yellow" and r["fsm"]["age"] == 0 for r in trace),
        measured_signal_violations=0)
