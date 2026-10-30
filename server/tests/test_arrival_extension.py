from dataclasses import replace

import numpy as np
import pytest

from research.observation.arrival_tracks import Calibration, Track, Packet, Motion, DeliveredState
from research.policies.arrival_extension import (
    ArrivalExtension, Timing, METHODS, choose_extension, advanced_phase, earliest_return_seconds,
)
from server.app.controllers.base import ControllerContext
from server.app.simulation.traffic_signal import TrafficSignal


def state(distance=.1, opposing=3, age_ticks=0, speed=(.11, .12, .12), leader=None):
    calibration = Calibration(dedicated_movement_lanes=True)
    motions = [Motion(Track(0, "north_straight", .42-distance), "moving", speed)]
    if leader:
        motions.append(Motion(Track(100, "north_straight", .4), leader))
    motions += [Motion(Track(i+1, "east_straight", .42-.08*i), "stopped") for i in range(opposing)]
    packet = Packet(100-age_ticks, 100, calibration.sha256, tuple(m.track for m in motions))
    return DeliveredState(packet, tuple(motions), calibration)


def context(**changes):
    return replace(ControllerContext(timestep=100, current_phase=0, time_in_phase=10.,
        valid_action_mask=np.ones(4, bool), phase_starvation_times=dict.fromkeys(range(4), 0.)), **changes)


def test_fresh_serviceable_approaching_cohort_can_extend_against_reference():
    observation = state()
    assert advanced_phase(observation, 0, 2) == 1
    action, diagnostic = choose_extension(observation, context(), Timing(), "window_extension")
    assert action == 0 and diagnostic["reference"] == 1
    assert diagnostic["used_ids"] == [0] and diagnostic["reason"] == "supported_extension"
    assert diagnostic["service_proxy"] > diagnostic["opposing_proxy"]+1


def test_advanced_mp_preserves_strict_paper_comparison_and_frozen_weight_ablation():
    observation = state(opposing=2)
    assert advanced_phase(observation, 0, 1.) == 1
    assert advanced_phase(observation, 0, 2.) == 1  # Equal demand/pressure does not activate strict > hold.
    assert advanced_phase(observation, 0, 4.) == 0


@pytest.mark.parametrize("leader", ["unknown", "stopped"])
def test_unresolved_or_stopped_leader_blocks_follower_support(leader):
    action, diagnostic = choose_extension(state(leader=leader), context(), Timing(), "window_extension")
    assert action == 1 and not diagnostic["used_ids"]


def test_competing_demand_and_phase_guards_prevent_unqualified_holds():
    action, _ = choose_extension(state(opposing=6), context(), Timing(), "window_extension")
    assert action == 0  # Explicit service proxy exceeds twelve competing vehicle-seconds.
    # Six is the largest valid single-lane population inside this normalized approach;
    # add demand in its opposing paired movement without changing the evidence.
    observation = state(opposing=5)
    more = tuple(Motion(Track(20+i, "west_straight", .4-.08*i), "stopped") for i in range(5))
    observation = replace(observation, packet=replace(observation.packet, tracks=observation.packet.tracks+tuple(m.track for m in more)),
                          motions=observation.motions+more)
    assert choose_extension(observation, context(), Timing(), "window_extension")[0] == 1
    assert choose_extension(state(), context(time_in_phase=39.), Timing(), "window_extension")[1]["reason"] == "maximum_green_guard"
    assert choose_extension(state(), context(phase_starvation_times={1:44.}), Timing(), "window_extension")[1]["reason"] == "phase_service_guard"


def test_source_age_correction_and_point_ablation_are_separate():
    observation = state(distance=.25, age_ticks=3, opposing=1, speed=(.12, .12, .12))
    assert choose_extension(observation, context(), Timing(), "window_extension")[0] == 0
    assert choose_extension(observation, context(), Timing(), "no_age_extension")[0] == 1
    uncertain = state(distance=.23, age_ticks=1, speed=(.105, .12, .12))
    assert choose_extension(uncertain, context(), Timing(), "point_extension")[0] == 0
    assert choose_extension(uncertain, context(), Timing(), "window_extension")[0] == 1


def test_zero_uncertainty_matches_point_rule_and_headway_limits_service_prefix():
    observation = state(distance=.15, speed=(.12, .12, .12))
    calibration = replace(observation.calibration, position_error=0.)
    observation = replace(observation, calibration=calibration,
                          packet=replace(observation.packet, calibration_sha256=calibration.sha256))
    assert choose_extension(observation, context(), Timing(), "point_extension") == choose_extension(observation, context(), Timing(), "window_extension")
    observation = state(opposing=5)
    moving = tuple(Motion(Track(30+i, "north_straight", .42-distance), "moving", (.12, .12, .12))
                   for i, distance in enumerate((.05, .1, .15, .2)))
    competing = tuple(Motion(Track(40+i, "west_straight", .4-.08*i), "stopped") for i in range(5))
    motions = tuple(m for m in observation.motions if m.track.track_id != 0)+moving+competing
    observation = replace(observation, motions=motions, packet=replace(observation.packet, tracks=tuple(m.track for m in motions)))
    action, diagnostic = choose_extension(observation, context(), Timing(), "window_extension")
    assert action == 0 and diagnostic["used_ids"] == [30, 31, 32]


def test_stale_or_possibly_departed_tracks_cannot_create_positive_support():
    assert choose_extension(state(age_ticks=6), context(), Timing(), "window_extension")[1]["reason"] == "missing_or_stale_support"
    action, diagnostic = choose_extension(state(distance=.02, age_ticks=3), context(), Timing(), "window_extension")
    assert action == 1 and not diagnostic["used_ids"]


def test_exact_return_timing_matches_the_actual_fsm_including_floating_guards():
    timing = Timing()
    signal = TrafficSignal(timing.all_red)
    signal.time_in_phase = timing.min_green
    signal.tick(.1, requested_phase=1)
    assert signal.color.name == "YELLOW"
    for _ in range(20):
        signal.tick(.1, requested_phase=1)
    assert signal.color.name == "RED"
    for _ in range(30):
        signal.tick(.1, requested_phase=1)
    assert signal.current_phase == 1 and signal.color.name == "GREEN"
    assert earliest_return_seconds(timing) == pytest.approx(18.2)
    assert earliest_return_seconds(Timing(all_red=1.)) < earliest_return_seconds(timing)


def test_all_methods_preserve_physical_locks_and_declared_cadence():
    for method in METHODS:
        controller = ArrivalExtension(method, Timing())
        observation = state()
        action = controller.act(observation, context())
        assert action in range(4)
        locked = context(timestep=101, is_decision_step=False, current_phase=2)
        assert controller.act(observation, locked) == 2
        controller.act(observation, context(timestep=102))
        assert controller.diagnostics["gate"] == method.endswith("native")
