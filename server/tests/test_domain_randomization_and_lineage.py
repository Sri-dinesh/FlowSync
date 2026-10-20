"""
Tests for domain randomization and model lineage tracking (Phase G / Task 1A.16 / Task G2 / Task G3).
"""

import tempfile
from pathlib import Path

import pytest

from research.scenarios.scenario_schema import DemandProfile, ScenarioConfig
from research.training.domain_randomizer import (
    DomainRandomizer,
    DomainRandomizerConfig,
)
from research.training.model_lineage import (
    AdaptationConfig,
    ModelLineageManager,
    compute_file_sha256,
)


def test_domain_randomization_reproducibility():
    base_scenario = ScenarioConfig(
        scenario_id="train_nominal_01",
        split="train",
        name="Nominal",
        description="Base scenario",
        demand_profile=DemandProfile(
            base_lambda=0.5,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
        duration_steps=720,
    )

    rand_config = DomainRandomizerConfig(
        rate_multiplier_min=0.8,
        rate_multiplier_max=1.2,
        imbalance_max=0.2,
        miss_rate_max=0.2,
        latency_max_ms=200,
        enable_bursts=True,
    )

    randomizer1 = DomainRandomizer(rand_config, seed=12345)
    randomizer2 = DomainRandomizer(rand_config, seed=12345)

    s1, f1 = randomizer1.randomize(base_scenario)
    s2, f2 = randomizer2.randomize(base_scenario)

    assert s1.demand_profile.base_lambda == s2.demand_profile.base_lambda
    assert s1.demand_profile.directional_weights == s2.demand_profile.directional_weights
    assert f1.miss_rate == f2.miss_rate
    assert f1.latency_ms == f2.latency_ms
    assert 0.0 <= f1.miss_rate <= 0.2
    assert 0 <= f1.latency_ms <= 200


def test_domain_randomization_distribution_bounds():
    base_scenario = ScenarioConfig(
        scenario_id="train_nominal_01",
        split="train",
        name="Nominal",
        description="Base scenario",
        demand_profile=DemandProfile(
            base_lambda=0.5,
            directional_weights={"north": 1.0, "south": 1.0, "east": 1.0, "west": 1.0},
        ),
        duration_steps=720,
    )
    rand_config = DomainRandomizerConfig(
        rate_multiplier_min=0.7,
        rate_multiplier_max=1.4,
        imbalance_max=0.3,
        miss_rate_max=0.35,
        latency_max_ms=400,
    )
    randomizer = DomainRandomizer(rand_config, seed=999)

    for _ in range(50):
        scenario, fault = randomizer.randomize(base_scenario)
        assert 0.35 <= scenario.demand_profile.base_lambda <= 0.70
        weights = list(scenario.demand_profile.directional_weights.values())
        assert all(w >= 0.1 for w in weights)
        assert 0.0 <= fault.miss_rate <= 0.35
        assert 0 <= fault.latency_ms <= 400


def test_model_lineage_and_catastrophic_forgetting():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        base_ckpt = tmp_path / "base_d3qn.pt"
        base_ckpt.write_bytes(b"dummy_base_weights_data_v1")

        adapted_ckpt = tmp_path / "adapted_d3qn.pt"
        adapted_ckpt.write_bytes(b"dummy_adapted_weights_data_v2")

        manager = ModelLineageManager(lineage_dir=tmp_path / "lineage")

        adapt_cfg = AdaptationConfig(
            target_scenario_id="test_burst_01",
            adaptation_episodes=20,
            learning_rate=5e-5,
            frozen_layers=["feature_network"],
        )

        record = manager.record_adaptation(
            lineage_id="adapt_exp_001",
            base_checkpoint_path=str(base_ckpt),
            adapted_checkpoint_path=str(adapted_ckpt),
            adaptation_config=adapt_cfg,
            zero_shot_metrics={"mean_delay": 28.5, "throughput": 850.0},
            adapted_metrics={"mean_delay": 17.2, "throughput": 960.0},
            source_base_metrics={"mean_delay": 12.0, "throughput": 1100.0},
            source_post_retention_metrics={"mean_delay": 13.5, "throughput": 1080.0},
        )

        assert record.base_checkpoint_hash == compute_file_sha256(base_ckpt)
        assert record.adapted_checkpoint_hash == compute_file_sha256(adapted_ckpt)

        # Catastrophic forgetting check
        # Delay went up from 12.0 to 13.5 -> delta = +1.5s
        assert abs(record.catastrophic_forgetting["mean_delay_delta"] - 1.5) < 1e-4
        # Relative degradation: 1.5 / 12.0 = 0.125 (12.5%)
        assert abs(record.catastrophic_forgetting["mean_delay_rel_degradation"] - 0.125) < 1e-4

        # Verify integrity
        integrity = manager.verify_integrity(record)
        assert integrity["base_hash_valid"] is True
        assert integrity["adapted_hash_valid"] is True

        # Test reload
        loaded = manager.load_record("adapt_exp_001")
        assert loaded is not None
        assert loaded.lineage_id == "adapt_exp_001"
        assert loaded.adapted_metrics["mean_delay"] == 17.2
