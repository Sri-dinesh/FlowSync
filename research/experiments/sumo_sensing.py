"""Frozen sensing study, live delivery boundary and offline accounting bridge."""
from dataclasses import asdict

from research.audits.sumo_branch_feasibility import Signal, advance
from research.experiments.sumo_observed_episode import validate_trace as validate_accounting
from research.observation.sumo_sensing import CountSensor, PRESETS, VERSION
from research.pilots.run_sumo_future_panel import arrivals
from research.policies.sumo_classical import Clock, CONTROLLERS, choose_action, observe

SOURCE_FILES = (
    "research/observation/sumo_sensing.py", "research/experiments/sumo_sensing.py",
    "research/analysis/sumo_sensing_metrics.py", "research/pilots/run_sumo_sensing_panel.py",
    "research/policies/sumo_classical.py", "research/audits/sumo_branch_feasibility.py",
    "research/experiments/sumo_observed_episode.py", "research/analysis/sumo_classical_metrics.py",
    "research/pilots/run_sumo_future_panel.py", "research/requirements-sumo.txt",
)
PLAN = dict(version=VERSION, decision_ticks=20, capture_ticks=1, dt_s=.1,
    initial_phase="NS", physical_timings_s=dict(min_green=8, yellow=3, all_red=1),
    controllers=list(CONTROLLERS), presets=[asdict(f) for f in PRESETS],
    scope="Known synthetic families and straight-only topology. New traffic seeds, not a final learned-policy test or camera calibration.",
    analysis="Equal-case means; paired own-clean penalties, pressure contrasts and factorial interactions. Exact 64-draw stratified seed bootstrap for 2 seeds/family; descriptive percentile intervals, not calibrated population coverage. Keep repeats out of scientific sample counts.",
    model_selection=False, policy_promoted=False, publication_ready=False)


def configuration(smoke=False):
    return dict(smoke=smoke, steps=800 if smoke else 1800, repeats=2 if smoke else 1,
        cap_seconds=240 if smoke else 900,
        families=[("balanced", .2, .2, [1350901])] if smoke else [
            ("balanced", .2, .2, [1350001, 1350002]),
            ("ns_dominant", .3, .1, [1350101, 1350102]),
            ("ew_dominant", .1, .3, [1350201, 1350202])])


def plans(smoke=False):
    cfg = configuration(smoke)
    return [dict(seed=seed, family=family, ns_rate=ns, ew_rate=ew, steps=cfg["steps"],
        schedule=arrivals(seed, 0, cfg["steps"], ns, ew)) for family, ns, ew, seeds in cfg["families"] for seed in seeds]


def episode(conn, axes, plan, controller, fault, budget):
    if conn.simulation.getTime() != 0 or conn.vehicle.getIDList():
        raise ValueError("Sensing episodes require a fresh empty simulation")
    sensor, signal, backlog, previous, requests = CountSensor(fault, plan["seed"]), Signal(), [], [], {}
    for request in plan["schedule"]:
        requests.setdefault(request[0], []).append(request)
    for tick in range(plan["steps"]):
        budget()
        delivery = sensor.step(previous, tick)
        proposal, decision = None, None
        if tick % 20 == 0:
            packet = None if controller == "fixed" else delivery.counts
            proposal = choose_action(controller, packet, Clock(signal.phase, signal.stage, signal.age))
            decision = dict(packet=delivery.counts.to_dict(), before_fsm=asdict(signal), proposal=proposal)
        row, backlog = advance(conn, signal, axes, tick, requests.get(tick, []), backlog, first_action=proposal)
        row["sensing"] = delivery.to_dict()
        if decision is not None:
            row["decision"] = decision
        previous = row["vehicles"]
        yield row


def physical_view(trace):
    """Sensor-independent executed traffic/signal evidence for Fixed controls."""
    return [{k:v for k,v in row.items() if k not in ("sensing", "decision")} for row in trace]


def validate_trace(trace, plan, controller, fault, axes):
    sensor, previous, packets, validation_rows = CountSensor(fault, plan["seed"]), [], [], []
    missing, ages, delivery_errors, corruption_errors, visible, missed = 0, [], [], [], 0, 0
    captures = []
    for tick, row in enumerate(trace):
        if row["tick"] != tick:
            raise ValueError("Unordered sensing trace")
        delivery = sensor.step(previous, tick)
        clean = observe(previous)
        captures.append(clean)
        if row.get("sensing") != delivery.to_dict():
            raise ValueError("Delivered sensing record does not reconstruct")
        view = dict(row)
        if tick % 20 == 0:
            if row["decision"]["packet"] != delivery.counts.to_dict():
                raise ValueError("Original controller packet differs from delivered counts")
            packets.append(delivery.counts)
            # Evaluation-only representation for the frozen clean-packet checker.
            # Preserve original proposals and clocks. Never use this view live.
            view["decision"] = {**row["decision"], "packet":clean.to_dict()}
            if delivery.source_tick is None:
                missing += 1
            else:
                ages.append(tick-delivery.source_tick)
                source = captures[delivery.source_tick]
                raw_visible = sum(source.incoming)+sum(source.outgoing)
                visible += raw_visible
                missed += raw_visible-sum(delivery.counts.incoming)-sum(delivery.counts.outgoing)
                corruption_errors.extend(abs(a-b) for name in ("incoming", "outgoing", "halted")
                    for a,b in zip(getattr(source,name), getattr(delivery.counts,name)))
            delivery_errors.extend(abs(a-b) for name in ("incoming", "outgoing", "halted")
                for a,b in zip(getattr(clean,name), getattr(delivery.counts,name)))
        validation_rows.append(view)
        previous = row["vehicles"]
    iterator = iter(packets)
    def delivered_policy(_legacy_clean_packet, clock):
        counts = next(iterator)
        return choose_action(controller, None if controller == "fixed" else counts, clock)
    metrics = validate_accounting(validation_rows, plan["schedule"], delivered_policy, axes, plan["steps"])
    if next(iterator, None) is not None:
        raise ValueError("Unconsumed delivered decisions")
    metrics["sensing"] = dict(missing_decisions=missing, present_decisions=len(ages),
        mean_age_s=sum(ages)/len(ages)/10 if ages else None,
        max_age_s=max(ages)/10 if ages else None,
        contemporary_count_feature_mae=sum(delivery_errors)/len(delivery_errors),
        source_corruption_count_feature_mae=sum(corruption_errors)/len(corruption_errors) if corruption_errors else None,
        source_visible_vehicle_samples=visible, source_missed_vehicle_samples=missed,
        realised_source_miss_fraction=missed/visible if visible else None)
    return metrics
