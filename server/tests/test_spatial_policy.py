import copy

import numpy as np
import pytest
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState
from research.noise.fault_injector import FAULT_PRESETS, FaultProfile, PerceptionFaultInjector
from research.noise.spatial_counts import bounded_upstream, thin_partition
from research.scenarios.scenario_schema import ScenarioConfig
from research.policies.spatial_baselines import UpstreamMaxPressureController
from research.training.temporal_initialization import initialize_parent
from research.training.train_policy import collect_episode
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import (
    OBSERVED_VERSION, SPATIAL_CONTROL_VERSION, SPATIAL_KEY, SPATIAL_VERSION,
    SPATIAL_VERSIONS, encode_policy_observation,
)


def packet(step=0, counts=None):
    counts = np.arange(12) + 6 if counts is None else np.asarray(counts)
    obs = np.zeros(28, np.float32)
    obs[:12] = np.tanh(counts / 15.)
    obs[12] = 1.
    ctx = ControllerContext(timestep=step, movement_queues={}, outgoing_counts={"north": 4, "east": 3},
                            extra_telemetry={"spawned_this_step": 3})
    return obs, ctx


@pytest.mark.parametrize("profile", list(FAULT_PRESETS.values()) + [
    FaultProfile(miss_rate=1.), FaultProfile(lane_misclass_prob=1., jitter_std=.5, false_positive_lambda=20.),
    FaultProfile(burst_miss_prob=1., burst_approaches=["north", "south", "east", "west"]),
])
def test_spatial_faults_preserve_legacy_draws_and_partition(profile):
    old, new = PerceptionFaultInjector(profile, 77), PerceptionFaultInjector(profile, 77)
    for step in range(30):
        obs, ctx = packet(step)
        ctx2 = copy.deepcopy(ctx)
        legacy = old.corrupt_observation(obs, step, ctx)
        actual = new.corrupt_observation(obs, step, ctx2, upstream_counts=np.arange(12))
        np.testing.assert_array_equal(actual, legacy)
        spatial = np.asarray(ctx2.extra_telemetry.pop(SPATIAL_KEY))
        assert (spatial >= 0).all() and (spatial <= actual[:12] + 1e-7).all()
        assert ctx2.extra_telemetry == ctx.extra_telemetry and ctx2.outgoing_counts == ctx.outgoing_counts
        assert old.get_realized_diagnostics() == new.get_realized_diagnostics()
        if profile.miss_rate == 1.:
            assert not spatial.any()
    new.reset(77)
    obs, ctx = packet()
    first = new.corrupt_observation(obs, 0, ctx, upstream_counts=np.arange(12))
    other = PerceptionFaultInjector(profile, 77)
    obs2, ctx2 = packet()
    np.testing.assert_array_equal(first, other.corrupt_observation(obs2, 0, ctx2, upstream_counts=np.arange(12)))
    assert ctx.extra_telemetry == ctx2.extra_telemetry


@pytest.mark.parametrize("profile", [FaultProfile(latency_ms=200), FaultProfile(frame_drop_prob=1.)])
def test_whole_spatial_packet_is_stale_not_refreshed(profile):
    injector = PerceptionFaultInjector(profile, 88)
    values = []
    for step in range(3):
        obs, ctx = packet(step, np.full(12, 10))
        injector.corrupt_observation(obs, step, ctx, upstream_counts=np.full(12, step + 1))
        values.append(ctx.extra_telemetry[SPATIAL_KEY])
    assert values[0] == values[1] == values[2]
    assert ctx.extra_telemetry["observation_age_ms"] == 200.


def test_partition_extremes_and_malformed_counts():
    total = np.full(12, 10)
    detected = np.full(12, 4)
    rng = np.random.default_rng(99)
    np.testing.assert_array_equal(thin_partition(np.zeros(12), total, detected, rng), np.zeros(12))
    np.testing.assert_array_equal(thin_partition(total, total, detected, rng), detected)
    np.testing.assert_array_equal(bounded_upstream(np.full(12, 120), np.full(12, 108)), np.full(12, 108))
    for invalid in (np.full(12, np.nan), np.full(12, -1), np.full(12, .5), np.zeros(3)):
        with pytest.raises(ValueError):
            bounded_upstream(invalid, total)


def test_encoding_control_and_missing_data_fail_closed():
    obs, ctx = packet()
    for version in SPATIAL_VERSIONS:
        with pytest.raises(ValueError, match="delivered spatial"):
            encode_policy_observation(obs, ctx, version)
    ctx.extra_telemetry[SPATIAL_KEY] = (obs[:12] * .5).tolist()
    treatment = encode_policy_observation(obs, ctx, SPATIAL_VERSION)
    control = encode_policy_observation(obs, ctx, SPATIAL_CONTROL_VERSION)
    legacy = encode_policy_observation(obs, ctx, OBSERVED_VERSION)
    np.testing.assert_array_equal(treatment[:36], legacy)
    np.testing.assert_array_equal(control[:36], legacy)
    assert treatment.shape == control.shape == (48,) and treatment[36:].any() and not control[36:].any()
    ctx.extra_telemetry[SPATIAL_KEY] = [1.] * 12
    with pytest.raises(ValueError):
        encode_policy_observation(obs, ctx, SPATIAL_VERSION)


@pytest.mark.parametrize("version", SPATIAL_VERSIONS)
def test_zero_expansion_checkpoint_and_new_column_gradients(tmp_path, version):
    torch.manual_seed(12)
    parent = DQNAgent(36, OBSERVED_VERSION)
    state = parent.get_checkpoint_state()
    child = DQNAgent(48, version)
    initialize_parent(child, state, expand_v7=True)
    x = torch.rand(32, 36)
    extra = torch.rand(32, 12) if version == SPATIAL_VERSION else torch.zeros(32, 12)
    masks = torch.ones(32, 4, dtype=torch.bool)
    q_parent = parent.online_net(x, masks)
    q_child = child.online_net(torch.cat((x, extra), 1), masks)
    torch.testing.assert_close(q_parent, q_child, atol=1e-5, rtol=1e-5)
    assert torch.equal(q_parent.argmax(1), q_child.argmax(1))
    q_child.square().mean().backward()
    assert bool(child.online_net.feature_layer[0].weight.grad[:, 36:].any()) == (version == SPATIAL_VERSION)
    path = tmp_path / "v9.pt"
    torch.save(child.get_checkpoint_state(), path)
    loaded = D3QNController(checkpoint_path=str(path))
    assert loaded.agent.obs_version == version and loaded.agent.state_dim == 48
    assert not loaded.agent.online_net.training


@pytest.mark.parametrize("version", SPATIAL_VERSIONS)
@pytest.mark.parametrize("shield", [False, True])
def test_train_inference_input_parity_with_spatial_faults(version, shield):
    torch.manual_seed(22)
    agent = DQNAgent(48, version)
    inputs = []
    hook = agent.online_net.register_forward_pre_hook(lambda net, args: inputs.append(args[0].clone()))
    scenario = ScenarioConfig("train_v9_parity", "train", "Parity", duration_steps=600)
    fault = FaultProfile(miss_rate=.3, latency_ms=200, frame_drop_prob=.1, false_positive_lambda=.2)
    result = collect_episode(agent, scenario, 32001, fault, epsilon=0, learn=False, train_with_shield=shield)
    training_inputs = list(inputs)
    inputs.clear()
    controller = D3QNController(agent=agent)
    if shield:
        controller = FlowSyncUQController(d3qn_controller=controller, enable_shield=True, enable_fallback=False)
    inference = ExperimentRunner().run(controller, scenario, 32001, record_trajectory=False, allow_untrained=True,
        fault_injector=PerceptionFaultInjector(fault, seed=122001))
    hook.remove()
    assert len(inputs) == len(training_inputs) > 1
    for train, predicted in zip(training_inputs, inputs):
        torch.testing.assert_close(train, predicted, atol=0, rtol=0)
    assert result["avg_delay"] == pytest.approx(inference.avg_delay, abs=.001)
    assert inference.scenario_diagnostics["sensor_model"] == "synthetic_partitioned_count_sensor_v3"
    assert inference.executed_conflict_violations == inference.executed_clearance_violations == 0
    with pytest.raises(ValueError, match="spatial sensor"):
        ExperimentRunner().run(controller, scenario, 32001, allow_untrained=True, spatial_observation=False)


def test_spatial_baseline_reads_only_delivered_counts_not_original():
    obs, ctx = packet()
    obs[:12] = 0.
    obs[0], obs[6] = np.tanh(10/15), np.tanh(2/15)
    ctx.outgoing_counts = {}
    ctx.current_phase = 0
    ctx.movement_queues = {"north_straight": 10, "east_straight": 2}
    delivered = np.zeros(12)
    delivered[6] = obs[6]
    ctx.extra_telemetry[SPATIAL_KEY] = delivered.tolist()
    saved = copy.deepcopy(ctx)
    assert UpstreamMaxPressureController().act(obs, ctx) == 1
    assert ctx.movement_queues == saved.movement_queues
    ctx.extra_telemetry[SPATIAL_KEY] = [0.] * 12
    assert UpstreamMaxPressureController().act(obs, ctx) == 0
