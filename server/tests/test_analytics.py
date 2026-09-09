"""
Unit tests for analytics router.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_dashboard_summary_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/analytics/dashboard-summary")
        assert response.status_code == 200
        data = response.json()

        assert "overview" in data
        assert "approach_totals" in data
        assert "vehicle_type_counts" in data
        assert "mode_benchmarks" in data
        assert "phase_distribution" in data
        assert "sessions" in data

        ov = data["overview"]
        assert ov["total_sessions"] >= 0
        assert ov["total_vehicles_processed"] >= 0
        assert ov["avg_wait_reduction_pct"] > 0
        assert ov["avg_intersection_wait_s"] >= 0
        assert ov["total_movement_occurrences"] >= 0
        assert ov["total_footage_duration_s"] >= 0
        assert ov["peak_queue_observed"] >= 0

