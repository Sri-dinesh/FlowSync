"""Causal v8 inputs, matched initialization and train/inference parity."""
import json

import numpy as np
import pytest
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState, build_environment
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.temporal_initialization import initialize_parent
from research.train_policy import collect_episode
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import (DeliveredHistory, OBSERVED_VERSION, TEMPORAL_KEY,
    TEMPORAL_VERSION, TEMPORAL_CONTROL_VERSION, TEMPORAL_VERSIONS, encode_policy_observation)


def test_history_is_causal_copied_bounded_and_resettable():
    history = DeliveredHistory()
    obs = np.zeros(28, dtype=np.float32)
    for tick in range(50):
        obs[:12] = tick / 100.
        ctx = ControllerContext(timestep=tick, extra_telemetry={"observation_age_ms": tick * 100})
        value = history.update(obs, ctx)
        if tick < 10:
            assert not value[:24].any() and not value[25:27].any()
        if tick == 30:
            np.testing.assert_allclose(value[:12], .2)
            np.testing.assert_array_equal(value[12:24], np.zeros(12))
            np.testing.assert_allclose(value[24:], [.6, 1, 1, 1])
        obs[:] = 999  # Packet buffers are reusable; history must own its copy.
    assert len(history._counts) == 31
    history.reset()
    value = history.update(np.zeros(28), ControllerContext(timestep=0))
    assert not value.any()


def test_missing_history_is_not_interpolated_and_unknown_age_is_not_fresh():
    history = DeliveredHistory()
    history.update(np.ones(28), ControllerContext(timestep=0))
    value = history.update(np.ones(28), ControllerContext(timestep=11))
    assert not value.any()  # Exact tick 1 was never observed; age unavailable.
    for age in (-1, float("nan"), None, "unknown"):
        history.reset()
        value = history.update(np.ones(28), ControllerContext(timestep=0,
            extra_telemetry={"observation_age_ms": age}))
        assert value[-1] == 0
    history.reset()
    value = history.update(np.ones(28), ControllerContext(timestep=0,
        extra_telemetry={"observation_age_ms": 9000}))
    assert value[24] == value[-1] == 1


def test_history_rejects_reused_episode_and_wrong_tick_rate():
    history = DeliveredHistory()
    history.update(np.zeros(28), ControllerContext(timestep=0))
    with pytest.raises(ValueError, match="reset history"):
        history.update(np.zeros(28), ControllerContext(timestep=0))
    with pytest.raises(ValueError, match="10 Hz"):
        history.update(np.zeros(28), ControllerContext(timestep=1, dt=.2))


def test_versions_are_explicit_and_control_zeros_only_extension():
    ctx = ControllerContext(timestep=40, extra_telemetry={TEMPORAL_KEY: list(range(28))})
    obs = np.linspace(0, 1, 28)
    parent = encode_policy_observation(obs, ctx, OBSERVED_VERSION)
    for version in TEMPORAL_VERSIONS:
        value = encode_policy_observation(obs, ctx, version)
        assert value.shape == (64,) and value.dtype == np.float32
        np.testing.assert_array_equal(value[:36], parent)
        np.testing.assert_array_equal(value[36:], np.arange(28) if version == TEMPORAL_VERSION else np.zeros(28))
    with pytest.raises(ValueError, match="Unsupported"):
        encode_policy_observation(obs, ctx, "v8_guess")
    for version in TEMPORAL_VERSIONS:
        with pytest.raises(ValueError, match="every tick"):
            encode_policy_observation(obs, ControllerContext(timestep=0), version)


def test_runtime_history_uses_post_fault_packets_including_locked_ticks():
    sc = ScenarioConfig("train_history", "train", "History", duration_steps=50)
    env, _ = build_environment(sc)
    obs, _ = env.reset(seed=1)
    obs[:12] = .9
    sensor = ObservedState()
    faults = PerceptionFaultInjector(FaultProfile(miss_rate=1, latency_ms=200, frame_drop_prob=1), seed=1)
    for tick in range(35):
        _, ctx = sensor.build(env, obs, tick, faults)
        assert not ctx.is_decision_step
    value = np.asarray(ctx.extra_telemetry[TEMPORAL_KEY])
    assert not value[:24].any()  # Never hidden .9 counts.
    np.testing.assert_allclose(value[24:], [.68, 1, 1, 1])
    json.dumps(ctx.extra_telemetry)  # Trajectory serialization must remain valid.
    _, clean = ObservedState().build(env, obs, 0)
    assert clean.extra_telemetry[TEMPORAL_KEY][-1] == 1
    assert clean.extra_telemetry[TEMPORAL_KEY][24] == 0


@pytest.mark.parametrize("version", TEMPORAL_VERSIONS)
def test_zero_expansion_preserves_parent_q_values_and_checkpoint_loading(tmp_path, version):
    torch.manual_seed(11)
    parent = DQNAgent(36, OBSERVED_VERSION)
    checkpoint = parent.get_checkpoint_state()
    original = checkpoint["online_net"]["feature_layer.0.weight"].clone()
    child = DQNAgent(64, version)
    initialize_parent(child, checkpoint, expand_v7=True)
    x = torch.rand(32, 36)
    ext = torch.rand(32, 28) if version == TEMPORAL_VERSION else torch.zeros(32, 28)
    mask = torch.ones(32, 4, dtype=torch.bool)
    mask[:, 2] = False
    with torch.no_grad():
        q_parent = parent.online_net(x, mask)
        q_child = child.online_net(torch.cat((x, ext), dim=1), mask)
    torch.testing.assert_close(q_parent, q_child, atol=1e-5, rtol=1e-5)
    assert torch.equal(q_parent.masked_fill(~mask, -1e9).argmax(1), q_child.masked_fill(~mask, -1e9).argmax(1))
    assert torch.equal(checkpoint["online_net"]["feature_layer.0.weight"], original)
    assert not child.online_net.feature_layer[0].weight[:, 36:].any()
    child.online_net(torch.cat((x, ext), dim=1), mask).square().mean().backward()
    gradient = child.online_net.feature_layer[0].weight.grad[:, 36:]
    assert bool(gradient.any()) == (version == TEMPORAL_VERSION)
    path = tmp_path / "v8.pt"
    torch.save(child.get_checkpoint_state(), path)
    loaded = D3QNController(checkpoint_path=str(path))
    assert loaded.agent.obs_version == version and loaded.agent.state_dim == 64
    assert not loaded.agent.online_net.training


def test_expansion_needs_explicit_flag_and_correct_versions():
    parent = DQNAgent(36, OBSERVED_VERSION).get_checkpoint_state()
    with pytest.raises(ValueError, match="must match"):
        initialize_parent(DQNAgent(64, TEMPORAL_VERSION), parent)
    with pytest.raises(ValueError, match="v7 parent"):
        initialize_parent(DQNAgent(36, OBSERVED_VERSION), parent, expand_v7=True)
    parent["online_net"]["feature_layer.0.weight"][0, 0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        initialize_parent(DQNAgent(64, TEMPORAL_VERSION), parent, expand_v7=True)


@pytest.mark.parametrize("version", TEMPORAL_VERSIONS)
@pytest.mark.parametrize("shield", [False, True])
def test_v8_train_inference_inputs_and_actions_match(version, shield):
    torch.manual_seed(22)
    agent = DQNAgent(64, version)  # Nonzero history weights exercise real semantics.
    inputs = []
    handle = agent.online_net.register_forward_pre_hook(lambda net, args: inputs.append(args[0].clone()))
    sc = ScenarioConfig("train_v8_parity", "train", "Parity", duration_steps=600)
    fault = FaultProfile(miss_rate=.3, latency_ms=200, frame_drop_prob=.1)
    collected = collect_episode(agent, sc, 32001, fault, epsilon=0, learn=False, train_with_shield=shield)
    training_inputs = list(inputs)
    inputs.clear()
    controller = D3QNController(agent=agent)
    if shield:
        controller = FlowSyncUQController(d3qn_controller=controller, enable_shield=True, enable_fallback=False)
    result = ExperimentRunner().run(controller, sc, 32001, record_trajectory=False, allow_untrained=True,
        fault_injector=PerceptionFaultInjector(fault, seed=122001))
    handle.remove()
    assert len(inputs) == len(training_inputs) > 1
    for train, inference in zip(training_inputs, inputs):
        torch.testing.assert_close(train, inference, rtol=0, atol=0)
    assert collected["avg_delay"] == pytest.approx(result.avg_delay, abs=.001)
    assert result.executed_conflict_violations == result.executed_clearance_violations == 0
