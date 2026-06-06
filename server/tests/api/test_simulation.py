import pytest
from unittest.mock import MagicMock

def test_start_simulation(client, mock_supabase):
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "test-sim-id"}])
    
    response = client.post("/simulation/start")
    assert response.status_code == 200
    assert "simulation_id" in response.json()

def test_stop_simulation(client, mock_supabase, app_state):
    app_state["sim_running"] = True
    app_state["current_simulation_id"] = "test-sim-id"
    
    response = client.post("/simulation/stop")
    assert response.status_code == 200
    assert response.json() == {"status": "stopped"}
    assert app_state["sim_running"] is False

def test_reset_simulation(client, app_state):
    app_state["sim_running"] = True
    response = client.post("/simulation/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert app_state["sim_running"] is False

def test_set_mode(client, app_state):
    response = client.put("/simulation/mode", json={"mode": "ai"})
    assert response.status_code == 200
    assert response.json() == {"mode": "ai"}
    assert app_state["mode"] == "ai"

def test_get_status(client):
    response = client.get("/simulation/status")
    assert response.status_code == 200
    data = response.json()
    assert "avg_wait_time" in data
    assert "throughput" in data
