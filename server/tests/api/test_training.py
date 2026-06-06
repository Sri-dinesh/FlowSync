import pytest
from unittest.mock import MagicMock

def test_start_training(client, mock_supabase, app_state):
    mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "test-sim-id"}])
    
    response = client.post("/training/start", json={"num_episodes": 1, "simulation_id": "test-sim-id"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"

def test_stop_training(client, app_state):
    app_state["trainer"].is_training = True
    response = client.post("/training/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopping"

def test_training_status(client):
    response = client.get("/training/status")
    assert response.status_code == 200
    assert "is_training" in response.json()

def test_list_models(client, mock_model_service):
    mock_model_service["list"].return_value = [{"id": "model1", "episodes": 100}]
    response = client.get("/training/models")
    assert response.status_code == 200
    assert len(response.json()["models"]) == 1
