import os
from unittest.mock import MagicMock, patch

# Set dummy env vars for Settings validation
os.environ["SUPABASE_URL"] = "https://dummy.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "sb_secret_dummy"

# Mock create_client before importing the app
mock_create_client = patch("supabase.create_client", return_value=MagicMock()).start()

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def mock_supabase():
    with patch("app.services.supabase_service.supabase_client") as mock:
        yield mock

@pytest.fixture
def mock_model_service():
    with patch("app.services.model_service.save_checkpoint") as mock_save, \
         patch("app.services.model_service.load_checkpoint") as mock_load, \
         patch("app.services.model_service.list_all_models") as mock_list:
        yield {
            "save": mock_save,
            "load": mock_load,
            "list": mock_list
        }

@pytest.fixture
def client():
    # Use TestClient with the lifespan context manager
    with TestClient(app) as c:
        yield c

@pytest.fixture
def app_state(client):
    return app.state.app_state
