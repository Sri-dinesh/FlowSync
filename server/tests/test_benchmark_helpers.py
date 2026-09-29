from app.websockets.simulation_ws import (
    _controller_winners,
    _normalize_scenario_modes,
)


def test_scenario_modes_support_single_controller_and_remove_duplicates():
    assert _normalize_scenario_modes(["greedy"]) == ["greedy"]
    assert _normalize_scenario_modes(["AI", "fixed", "ai", "unknown"]) == [
        "ai",
        "fixed",
    ]
    assert _normalize_scenario_modes(None) == ["ai", "fixed", "greedy"]


def test_controller_winners_reports_exact_displayed_tie():
    results = {
        "ai": {"avg_wait_time": 3.01, "total_passed": 8, "max_queue": 1},
        "fixed": {"avg_wait_time": 6.15, "total_passed": 6, "max_queue": 2},
        "greedy": {"avg_wait_time": 3.01, "total_passed": 8, "max_queue": 1},
    }

    assert _controller_winners(results) == ["ai", "greedy"]


def test_controller_winners_uses_throughput_then_peak_queue_as_tiebreakers():
    results = {
        "ai": {"avg_wait_time": 3.0, "total_passed": 9, "max_queue": 2},
        "greedy": {"avg_wait_time": 3.0, "total_passed": 8, "max_queue": 0},
    }

    assert _controller_winners(results) == ["ai"]
