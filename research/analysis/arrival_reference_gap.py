"""Post-hoc same-state decisions and chosen-action service witnesses.

Future pre-corruption captures are evaluation-only. They are never passed to
the reconstructed policy and do not estimate alternative-action traffic gains.
"""
from collections import Counter

from research.observation.arrival_tracks import DT, Packet, TrackHistory
from research.pilots.run_arrival_window_panel import CALIBRATION, build_context, shield
from research.policies.arrival_extension import (
    ArrivalExtension, Timing, choose_extension, pressure_phase, advanced_phase, age_gated_reference, MAX_PACKET_AGE,
)


def _track(frame, identifier):
    return next((track for track in frame["capture"] if track["track_id"] == identifier), None)


def service_witness(frames, gate, identifier, stop_line=.42, option_ticks=20):
    """Observe service under the chosen hold; a crossing is a discharge, not demand."""
    current = _track(frames[gate], identifier)
    endpoint = gate+option_ticks
    observed_end = min(endpoint, len(frames)-1)
    phase = frames[gate]["before"]["phase"]
    result = dict(gate=gate, track_id=identifier, option_s=option_ticks*DT,
        endpoint_complete=endpoint < len(frames), position_at_gate=None if current is None else current["position"],
        crossing_after_s_lower=None, crossing_after_s_upper=None,
        green_ticks=sum(frame["after"]["phase"] == phase and frame["after"]["color"] == "GREEN"
                        for frame in frames[gate:min(endpoint, len(frames))]))
    if current is None:
        return {**result, "status": "missing_at_gate"}
    if current["position"] > stop_line:
        return {**result, "status": "already_postline_at_gate"}
    lost = False
    for index in range(gate+1, observed_end+1):
        observed = _track(frames[index], identifier)
        if observed is None:
            lost = True
            continue
        if observed["position"] > stop_line:
            return {**result, "status": "crossed_within_option",
                    "crossing_after_s_lower": (index-gate-1)*DT,
                    "crossing_after_s_upper": (index-gate)*DT}
    if endpoint >= len(frames):
        return {**result, "status": "censored_horizon"}
    return {**result, "status": "lost_before_observed_crossing" if lost else "not_crossed_by_endpoint"}


def analyze_run(raw):
    if raw["method"] != "window_extension":
        raise ValueError("Reference-gap audit requires the frozen primary trajectory")
    timing = Timing(all_red=raw["case"]["scenario"]["red_duration"])
    history = TrackHistory(CALIBRATION)
    policy, protection = ArrivalExtension("window_extension", timing), shield(timing)
    alternative_shield = shield(timing)
    waits, counts, reasons, disagreements, services = dict.fromkeys(range(4), 0.), Counter(), Counter(), [], []
    for index, frame in enumerate(raw["frames"]):
        if frame["step"] != index:
            raise ValueError("Primary saved-frame coverage is not contiguous")
        state = history.observe(Packet.parse(frame["packet"]))
        context, waits = build_context(state, frame["before"], index, waits, timing)
        proposed = policy.act(state, context)
        actual = protection.filter_context(proposed, context)
        if proposed != frame["proposed"] or actual.to_dict() != frame["shield"] or policy.diagnostics != frame["policy"]:
            raise ValueError("Frozen primary decisions do not reconstruct")
        if not context.is_decision_step:
            counts["physical_lock_ticks"] += 1
            continue
        counts["switchable_ticks"] += 1
        gate = policy.diagnostics["gate"]
        counts["policy_gates" if gate else "cached_switchable_ticks"] += 1
        native = alternative_shield.filter_context(pressure_phase(state, context.current_phase, subset="all"), context).executed_action
        upstream = alternative_shield.filter_context(pressure_phase(state, context.current_phase), context).executed_action
        fresh_proposal, _ = choose_extension(state, context, timing, "window_extension")
        fresh = alternative_shield.filter_context(fresh_proposal, context).executed_action
        reference = alternative_shield.filter_context(age_gated_reference(state, context.current_phase), context).executed_action
        ungated = alternative_shield.filter_context(advanced_phase(state, context.current_phase, 2.), context).executed_action
        counts["count_semantics_disagreement_ticks"] += int(native != upstream)
        counts["freshness_gate_effect_ticks"] += int(reference != ungated)
        counts["overage_switchable_ticks"] += int(state.packet.age_s is None or state.packet.age_s > MAX_PACKET_AGE+1e-9)
        if actual.executed_action != native:
            counts["disagreement_ticks"] += 1
            counts["gate_disagreement_ticks" if gate else "cached_disagreement_ticks"] += 1
            cache_only = not gate and fresh == native
            counts["cached_disagreements_removed_by_fresh_primary"] += int(cache_only)
            disagreements.append(dict(step=index, gate=gate, primary=actual.executed_action, native=native,
                upstream=upstream, fresh_primary=fresh, reference=reference,
                cached_disagreement_removed_by_fresh_primary=cache_only, source_age_s=state.packet.age_s))
        if not gate:
            continue
        reasons[policy.diagnostics["reason"]] += 1
        counts["reference_disagreement_gates"] += int(reference != native)
        counts["overage_policy_gates"] += int(state.packet.age_s is None or state.packet.age_s > MAX_PACKET_AGE+1e-9)
        if policy.diagnostics["reason"] != "supported_extension":
            continue
        counts["extension_gates"] += 1
        counts["extension_agrees_with_native"] += int(actual.executed_action == native)
        observed_ids = {track.track_id for track in state.packet.tracks}
        motions = {motion.track.track_id: motion for motion in state.motions}
        for identifier in policy.diagnostics["used_ids"]:
            witness = service_witness(raw["frames"], index, identifier, CALIBRATION.stop_line)
            motion = motions[identifier]
            current = _track(frame, identifier)
            previous = _track(raw["frames"][index-1], identifier) if index else None
            speed = ((current["position"]-previous["position"])/DT if current is not None and previous is not None else None)
            unobserved_leaders = sum(track["movement"] == current["movement"] and
                current["position"] < track["position"] <= CALIBRATION.stop_line and track["track_id"] not in observed_ids
                for track in frame["capture"]) if current is not None else None
            services.append(dict(case_id=raw["case"]["case_id"], **witness, source_age_s=state.packet.age_s,
                estimated_speed_upper=motion.speed[2], evaluation_last_tick_speed=speed,
                evaluation_speed_exceeds_estimated_upper=speed is not None and speed > motion.speed[2]+1e-9,
                evaluation_unobserved_leaders=unobserved_leaders))
    keys = ("physical_lock_ticks", "switchable_ticks", "policy_gates", "cached_switchable_ticks",
            "disagreement_ticks", "gate_disagreement_ticks", "cached_disagreement_ticks",
            "cached_disagreements_removed_by_fresh_primary", "count_semantics_disagreement_ticks",
            "reference_disagreement_gates", "freshness_gate_effect_ticks", "overage_switchable_ticks",
            "overage_policy_gates", "extension_gates", "extension_agrees_with_native")
    return dict(case_id=raw["case"]["case_id"], counts={key: counts[key] for key in keys},
                reasons=dict(reasons), disagreements=disagreements, service_witnesses=services)
