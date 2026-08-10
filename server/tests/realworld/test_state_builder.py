"""
Unit tests for StateBuilder in app/realworld/pipeline/state_builder.py
"""
import pytest
from app.realworld.pipeline.state_builder import StateBuilder
from app.realworld.models.schemas import WeightedLaneCounts


def test_state_builder_dimension():
    builder = StateBuilder()
    counts = WeightedLaneCounts(
        north_straight=2.0, north_left=1.0, north_right=0.5,
        south_straight=3.0, south_left=0.0, south_right=0.0,
        east_straight=0.0, east_left=0.0, east_right=0.0,
        west_straight=4.0, west_left=2.0, west_right=1.0,
    )
    obs = builder.build(
        weighted_counts=counts,
        current_phase=1,
        time_in_phase_seconds=15.0,
        is_transitioning=False,
    )

    assert len(obs) == 20
    # Queue values normalized by MAX_QUEUE_CAP (10.0)
    assert obs[0] == pytest.approx(2.0 / 10.0)  # north_straight
    assert obs[9] == pytest.approx(4.0 / 10.0)  # west_straight


def test_state_builder_one_hot_phase():
    builder = StateBuilder()
    counts = WeightedLaneCounts()
    obs = builder.build(
        weighted_counts=counts,
        current_phase=2,
        time_in_phase_seconds=10.0,
        is_transitioning=False,
    )

    # Phase 2 one-hot: indices 12..15 -> [0, 0, 1, 0]
    assert obs[12] == 0.0
    assert obs[13] == 0.0
    assert obs[14] == 1.0
    assert obs[15] == 0.0
