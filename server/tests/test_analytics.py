"""
Unit tests for analytics router.
"""
from __future__ import annotations

import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routers.analytics import (
    _clean_legacy_model_label,
    _deduplicate_auto_stop_files,
    _infer_benchmark_winners,
)


def _write_session(path, session_id: str, created_at: str, throughput: int = 34):
    path.write_text(json.dumps({
        "session_id": session_id,
        "created_at": created_at,
        "mode": "ai",
        "model_name": "model-id",
        "model_episodes": 25,
        "throughput": throughput,
        "stats": {
            "frame_count": 1200,
            "duration_s": 120.0,
            "total_detections": 40,
            "throughput": throughput,
            "avg_wait_s": 7.22,
            "peak_queue": 3,
        },
    }))


def test_auto_stop_duplicate_filter_keeps_uuid_record(tmp_path):
    canonical = tmp_path / "4b021fe7.json"
    duplicate = tmp_path / "sim_ai_1790669902.json"
    _write_session(canonical, "4b021fe7", "2026-09-29T08:18:05+00:00")
    _write_session(duplicate, "sim_ai_1790669902", "2026-09-29T08:18:22+00:00")

    assert _deduplicate_auto_stop_files([canonical, duplicate]) == [canonical]


def test_auto_stop_duplicate_filter_does_not_merge_distinct_runs(tmp_path):
    canonical = tmp_path / "4b021fe7.json"
    later_run = tmp_path / "sim_ai_1790670000.json"
    _write_session(canonical, "4b021fe7", "2026-09-29T08:18:05+00:00")
    _write_session(later_run, "sim_ai_1790670000", "2026-09-29T08:19:05+00:00")

    assert _deduplicate_auto_stop_files([canonical, later_run]) == [canonical, later_run]


def test_legacy_raw_reward_rating_is_removed_from_model_label():
    label = "Model 2026-09-29 11:14 - 1000eps - Failing — Best validated"

    assert _clean_legacy_model_label(label) == (
        "Model 2026-09-29 11:14 - 1000eps — Best validated"
    )


def test_legacy_benchmark_exact_tie_returns_every_winner():
    results = {
        "ai": {"avg_wait_time": 3.01, "total_passed": 8, "max_queue": 0},
        "fixed": {"avg_wait_time": 6.15, "total_passed": 6, "max_queue": 2},
        "greedy": {"avg_wait_time": 3.01, "total_passed": 8, "max_queue": 0},
    }

    assert _infer_benchmark_winners(results) == ["ai", "greedy"]


@pytest.mark.anyio
async def test_dashboard_summary_endpoint(monkeypatch):
    monkeypatch.setattr("app.routers.analytics._fetch_supabase_simulations", lambda: [])
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
        assert "benchmarks" in data

        ov = data["overview"]
        assert ov["total_sessions"] >= 0
        assert ov["total_vehicles_processed"] >= 0
        assert isinstance(ov["avg_wait_reduction_pct"], (int, float))
        assert ov["avg_intersection_wait_s"] >= 0
        assert ov["total_movement_occurrences"] >= 0
        assert ov["total_footage_duration_s"] >= 0
        assert ov["peak_queue_observed"] >= 0


@pytest.mark.anyio
async def test_benchmarks_endpoint(monkeypatch):
    monkeypatch.setattr("app.routers.analytics._fetch_supabase_simulations", lambda: [])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/analytics/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert "count" in data
        assert isinstance(data["benchmarks"], list)
