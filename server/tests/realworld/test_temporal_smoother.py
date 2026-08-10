"""
Unit tests for TemporalSmoother in app/realworld/utils/temporal_smoother.py
"""
import pytest
from app.realworld.utils.temporal_smoother import TemporalSmoother


def test_temporal_smoother_initialization():
    smoother = TemporalSmoother(alpha=0.3)
    raw = {"north_straight": 10.0, "south_straight": 5.0}
    res1 = smoother.update(raw)

    # First update should adopt initial values
    assert res1["north_straight"] == 10.0
    assert res1["south_straight"] == 5.0


def test_temporal_smoother_ema_step():
    smoother = TemporalSmoother(alpha=0.3)
    smoother.update({"north_straight": 10.0})

    # Second step: raw = 0.0 -> EMA = 0.3 * 0.0 + 0.7 * 10.0 = 7.0
    res2 = smoother.update({"north_straight": 0.0})
    assert res2["north_straight"] == pytest.approx(7.0)


def test_temporal_smoother_reset():
    smoother = TemporalSmoother(alpha=0.3)
    smoother.update({"north_straight": 10.0})
    smoother.reset()

    # After reset, first update takes raw value directly
    res = smoother.update({"north_straight": 2.0})
    assert res["north_straight"] == 2.0
