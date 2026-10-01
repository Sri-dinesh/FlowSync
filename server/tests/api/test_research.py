from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_research_scenarios():
    response = client.get("/research/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "total_scenarios" in data
    assert data["total_scenarios"] >= 16
    assert "scenarios" in data
    assert len(data["scenarios"]) >= 16


def test_research_controllers():
    response = client.get("/research/controllers")
    assert response.status_code == 200
    data = response.json()
    assert "controllers" in data
    ids = [c["id"] for c in data["controllers"]]
    assert "flowsync_uq" in ids
    assert "d3qn" in ids
    assert "max_pressure" in ids
    assert "fixed" in ids


def test_research_seeds():
    response = client.get("/research/seeds")
    assert response.status_code == 200
    data = response.json()
    assert data["seed_count"] == 20
    assert 1101 in data["seeds"]


def test_research_noise_presets():
    response = client.get("/research/noise-presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    keys = [p["key"] for p in data["presets"]]
    assert "clean" in keys
    assert "miss_30" in keys


def test_research_summary():
    response = client.get("/research/summary")
    assert response.status_code == 200
    data = response.json()
    assert "benchmark_summary" in data
    assert "statistical_report" in data
