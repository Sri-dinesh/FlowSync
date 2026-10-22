import copy
from types import SimpleNamespace

import numpy as np
import pytest

from research.audits.audit_upstream_observation import empty_switch, upstream_packet
from research.experiments.runtime import ObservedState
from server.app.simulation.environment import TrafficEnv
from server.app.simulation.intersection import Intersection, STOP_LINE
from server.app.simulation.vehicle import Vehicle
from server.app.controllers.max_pressure import MaxPressureController


def vehicle(position, state="moving"):
    return Vehicle(id=str(position), lane="east", turn="straight", position=position,
                   state=state, speed=.12, wait_time=0.)


def test_upstream_boundary_backlog_and_legacy_unchanged():
    intersection = Intersection()
    intersection.lanes["east_straight"] = [vehicle(0.), vehicle(STOP_LINE),
        vehicle(STOP_LINE + 1e-8), vehicle(.95), vehicle(.2, "passed")]
    intersection.spawner._pending["east_straight"].extend([0., 0.])
    legacy = intersection.get_movement_queues()
    assert legacy["east_straight"] == 6
    assert intersection.get_upstream_movement_counts()["east_straight"] == 4
    assert intersection.get_upstream_movement_counts(include_backlog=False)["east_straight"] == 2
    assert intersection.get_movement_queues() == legacy


def test_shadow_packet_removes_phantom_demand_and_rebuilds_mask_timer():
    env = TrafficEnv()
    env.reset(seed=1)
    env.intersection.signal.time_in_phase = 10.
    env.intersection.lanes["east_straight"] = [vehicle(.7)]
    original = env._get_obs()
    saved = original.copy()
    packet = upstream_packet(env.intersection, original)
    assert np.array_equal(original, saved)
    np.testing.assert_array_equal(packet[12:], original[12:])
    legacy_sensor, shadow_sensor = ObservedState(), ObservedState()
    for step in range(3):
        _, ctx = legacy_sensor.build(env, original, step)
        _, shadow = shadow_sensor.build(env, packet, step)
    assert ctx.movement_queues["east_straight"] == 1
    assert shadow.movement_queues["east_straight"] == 0
    assert ctx.valid_action_mask[1] and not shadow.valid_action_mask[1]
    assert ctx.phase_starvation_times[1] == pytest.approx(.3)
    assert shadow.phase_starvation_times[1] == 0.


def test_shadow_builder_has_no_physical_side_effects():
    env = TrafficEnv()
    env.reset(seed=4)
    env.intersection.lanes["east_straight"] = [vehicle(.8)]
    control = copy.deepcopy(env)
    shadow = ObservedState()
    for step in range(20):
        shadow.build(env, upstream_packet(env.intersection, env._get_obs()), step)
        a, reward_a, *_ = env.step(0)
        b, reward_b, *_ = control.step(0)
        np.testing.assert_array_equal(a, b)
        assert reward_a == reward_b
        assert env.intersection.get_movement_queues() == control.intersection.get_movement_queues()


def test_empty_switch_excludes_holding_and_locked_states():
    intersection = Intersection()
    upstream = intersection.get_upstream_movement_counts()
    ctx = SimpleNamespace(is_decision_step=True, current_phase=0)
    assert empty_switch(1, ctx, upstream)
    assert not empty_switch(0, ctx, upstream)
    ctx.is_decision_step = False
    assert not empty_switch(1, ctx, upstream)
    ctx.is_decision_step = True
    upstream["east_straight"] = 1
    assert not empty_switch(1, ctx, upstream)


def test_bad_packet_rejected():
    with pytest.raises(ValueError):
        upstream_packet(Intersection(), np.zeros(36))
    with pytest.raises(ValueError):
        upstream_packet(Intersection(), np.full(28, np.nan))


def test_already_discharged_vehicles_can_change_teacher_hold_choice():
    env = TrafficEnv()
    env.reset(seed=1)
    env.intersection.signal.time_in_phase = 10.
    env.intersection.lanes["north_straight"] = [
        Vehicle(id=str(p), lane="north", turn="straight", position=p, speed=.12, wait_time=0., state="moving")
        for p in (.5, .6)]
    env.intersection.lanes["east_straight"] = [vehicle(.2)]
    original = env._get_obs()
    old_obs, old_ctx = ObservedState().build(env, original, 0)
    new_obs, new_ctx = ObservedState().build(env, upstream_packet(env.intersection, original), 0)
    assert MaxPressureController().act(old_obs, old_ctx) == 0
    assert MaxPressureController().act(new_obs, new_ctx) == 1
    # Holding the current phase stays legal even with no upstream demand.
    np.testing.assert_array_equal(old_ctx.valid_action_mask, new_ctx.valid_action_mask)
