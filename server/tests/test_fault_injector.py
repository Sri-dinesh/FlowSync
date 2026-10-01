"""
test_fault_injector.py — Unit & Validation Tests for Perception Fault Injector
==============================================================================
Task 1A.9 & E2 Acceptance Criteria:
- Noise uses independent seeds (reproducible).
- Requested vs realized fault rates are measurable.
- Ground truth is untouched.
- Clean profile produces zero corruption.
- Latency correctly shifts observations through ring buffer.
"""
import numpy as np
import pytest

from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile, FAULT_PRESETS


def test_clean_profile_identity():
    """Clean profile must return exact copy without modification."""
    clean_obs = np.array([0.5] * 12 + [1.0, 0.0, 0.0, 0.0] + [0.2, 0.0, 0.3, 0.1] + [0.0] * 8, dtype=np.float32)
    injector = PerceptionFaultInjector(FAULT_PRESETS["clean"], seed=42)

    corrupted = injector.corrupt_observation(clean_obs, step=1)
    assert np.allclose(clean_obs, corrupted)
    diag = injector.get_realized_diagnostics()
    assert diag["total_missed_detections"] == 0
    assert diag["total_false_positives"] == 0


def test_bernoulli_miss_corruption():
    """Miss rate 0.40 must systematically scale down queues."""
    clean_obs = np.array([0.8] * 12 + [1.0, 0.0, 0.0, 0.0] + [0.2, 0.0, 0.3, 0.1] + [0.0] * 8, dtype=np.float32)
    injector = PerceptionFaultInjector(FaultProfile(name="test_miss", miss_rate=0.50), seed=1337)

    # Over 100 steps, queues should be reduced on missed steps
    total_diff = 0.0
    for s in range(100):
        corrupted = injector.corrupt_observation(clean_obs, step=s)
        total_diff += np.sum(clean_obs[:12] - corrupted[:12])

    assert total_diff > 0.0
    diag = injector.get_realized_diagnostics()
    assert diag["total_missed_detections"] > 0
    assert 0.35 <= diag["realized_miss_rate"] <= 0.65  # Expected ~50% miss rate


def test_latency_ring_buffer_delay():
    """Latency of 200ms (2 steps at 100ms dt) must emit observation from 2 steps prior."""
    profile = FaultProfile(name="test_latency", latency_ms=200)
    injector = PerceptionFaultInjector(profile, seed=42)

    obs_0 = np.full(28, 0.0, dtype=np.float32)
    obs_1 = np.full(28, 1.0, dtype=np.float32)
    obs_2 = np.full(28, 2.0, dtype=np.float32)
    obs_3 = np.full(28, 3.0, dtype=np.float32)

    e0 = injector.corrupt_observation(obs_0, step=0)
    e1 = injector.corrupt_observation(obs_1, step=1)
    e2 = injector.corrupt_observation(obs_2, step=2)  # Ring buffer reaches size 3: [obs_0, obs_1, obs_2]
    e3 = injector.corrupt_observation(obs_3, step=3)  # Ring buffer: [obs_1, obs_2, obs_3] -> emits obs_1

    # At step 3, emitted observation should be obs_1 (delayed by 2 steps)
    assert np.allclose(e3, obs_1)


def test_seed_reproducibility():
    """Two injectors with same seed produce identical sequence of corrupted observations."""
    profile = FAULT_PRESETS["combined_moderate"]
    inj1 = PerceptionFaultInjector(profile, seed=2026)
    inj2 = PerceptionFaultInjector(profile, seed=2026)

    obs = np.random.RandomState(99).randn(28).astype(np.float32)

    for step in range(50):
        c1 = inj1.corrupt_observation(obs, step=step)
        c2 = inj2.corrupt_observation(obs, step=step)
        assert np.allclose(c1, c2)
