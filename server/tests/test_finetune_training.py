import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient
import numpy as np
import torch

from app.main import app
from app.rl.dqn_agent import DQNAgent
from app.simulation.spawner import PoissonSpawner, SCENARIO_PROFILES, TrafficProfile
from app.services.model_service import list_all_models


def test_spawner_scenario_profiles():
    """Verify SCENARIO_PROFILES exist and PoissonSpawner respects directional weights."""
    spawner = PoissonSpawner(lambda_rate=1.0)
    assert "rush_hour" in SCENARIO_PROFILES
    assert "heavy_left" in SCENARIO_PROFILES
    assert "arterial_surge" in SCENARIO_PROFILES
    assert "platoon_burst" in SCENARIO_PROFILES

    # Set rush_hour profile
    spawner.set_profile("rush_hour")
    assert spawner.profile is not None
    assert spawner.profile.id == "rush_hour"
    assert spawner.profile.directional_weights["north"] == 1.8
    assert spawner.profile.directional_weights["east"] == 0.4

    # Test spawn distribution over simulated steps
    lanes = {
        f"{d}_{t}": []
        for d in ["north", "south", "east", "west"]
        for t in ["straight", "left", "right"]
    }
    ns_count = 0
    ew_count = 0
    spawner.set_seed(42)
    for _ in range(500):
        for q in lanes.values():
            q.clear()
        vehicles = spawner.spawn(0.1, lanes)
        for v in vehicles:
            if v.lane in ("north", "south"):
                ns_count += 1
            else:
                ew_count += 1

    # In rush hour (1.8 NS vs 0.4 EW), NS volume should be substantially higher than EW
    assert ns_count > ew_count * 2


def test_dqn_agent_prepare_for_finetuning():
    """Verify prepare_for_finetuning keeps weights, updates LR, and clears replay buffer."""
    agent = DQNAgent()
    
    # Simulate an agent with some weights and transitions
    initial_weights = agent.online_net.feature_layer[0].weight.clone()
    agent.replay_buffer.push(
        np.zeros(28), 0, 1.0, np.zeros(28), False, None
    )
    assert len(agent.replay_buffer) == 1

    # Prepare for fine-tuning with a smaller learning rate
    ft_lr = 5e-5
    agent.prepare_for_finetuning(learning_rate=ft_lr)

    # Weights must be exactly identical
    assert torch.equal(agent.online_net.feature_layer[0].weight, initial_weights)
    # Replay buffer must be cleared
    assert len(agent.replay_buffer) == 0
    # Optimizer learning rate must be updated
    assert agent.optimizer.param_groups[0]["lr"] == ft_lr
    # Step counters reset
    assert agent.step_count == 0
    assert agent.total_train_steps == 0


@pytest.mark.anyio
async def test_scenarios_endpoint():
    """Verify /training/scenarios returns predefined scenario profiles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/training/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        scenario_ids = [s["id"] for s in data["scenarios"]]
        assert "rush_hour" in scenario_ids
        assert "heavy_left" in scenario_ids
        assert "arterial_surge" in scenario_ids
        assert "platoon_burst" in scenario_ids


@pytest.mark.anyio
async def test_start_training_endpoint_with_finetuning():
    """Verify /training/start in finetune mode forks model ID and passes fine-tuning params."""
    mock_trainer = MagicMock()
    mock_trainer.is_training = False
    mock_trainer.train = AsyncMock()
    app.state.trainer = mock_trainer
    app.state.training_task = None

    base_model = "089035ea-3b87-4279-8230-00f1c4f10457"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/training/start",
            json={
                "mode": "finetune",
                "num_episodes": 100,
                "resume_model_id": f"{base_model}:1000",
                "resume_episode": 1000,
                "finetune_scenario": "rush_hour",
                "finetune_lr": 1e-4,
                "finetune_epsilon": 0.25,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["mode"] == "finetune"
        assert data["is_finetuned"] is True
        assert data["scenario"] == "rush_hour"
        # Forked simulation_id
        expected_sim_id = f"{base_model}-ft-rush_hour"
        assert data["simulation_id"] == expected_sim_id

        mock_trainer.train.assert_called_once_with(
            num_episodes=100,
            simulation_id=expected_sim_id,
            resume_model_id=f"{base_model}:1000",
            resume_episode=1000,
            is_finetune=True,
            finetune_scenario="rush_hour",
            finetune_lr=1e-4,
            finetune_epsilon=0.25,
            custom_profile=None,
        )


@pytest.mark.anyio
async def test_start_training_endpoint_with_custom_finetuning():
    """Verify /training/start in finetune mode with custom user-defined traffic profile."""
    mock_trainer = MagicMock()
    mock_trainer.is_training = False
    mock_trainer.train = AsyncMock()
    app.state.trainer = mock_trainer
    app.state.training_task = None

    base_model = "089035ea-3b87-4279-8230-00f1c4f10457"
    custom_profile_data = {
        "name": "Stadium Rush",
        "directional_weights": {"north": 2.5, "south": 0.5, "east": 0.5, "west": 0.5},
        "turn_probs": [0.7, 0.2, 0.1],
        "base_lambda": 1.2,
        "lambda_multiplier": 1.3,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/training/start",
            json={
                "mode": "finetune",
                "num_episodes": 75,
                "resume_model_id": f"{base_model}:500",
                "resume_episode": 500,
                "finetune_scenario": "custom",
                "finetune_lr": 8e-5,
                "finetune_epsilon": 0.20,
                "custom_profile": custom_profile_data,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["mode"] == "finetune"
        assert data["is_finetuned"] is True
        assert data["scenario"] == "Stadium Rush"
        expected_sim_id = f"{base_model}-ft-custom_stadium_rush"
        assert data["simulation_id"] == expected_sim_id

        mock_trainer.train.assert_called_once_with(
            num_episodes=75,
            simulation_id=expected_sim_id,
            resume_model_id=f"{base_model}:500",
            resume_episode=500,
            is_finetune=True,
            finetune_scenario="custom",
            finetune_lr=8e-5,
            finetune_epsilon=0.20,
            custom_profile=custom_profile_data,
        )


def test_spawner_custom_dict_profile():
    """Verify PoissonSpawner instantiates and applies a dictionary custom traffic profile."""
    spawner = PoissonSpawner(lambda_rate=0.5)
    custom_dict = {
        "id": "custom",
        "name": "Arterial Split",
        "directional_weights": {"north": 0.2, "south": 0.2, "east": 2.0, "west": 2.0},
        "turn_probs": [0.6, 0.2, 0.2],
        "base_lambda": 0.8,
        "lambda_multiplier": 1.1,
    }
    spawner.set_profile(custom_dict)
    assert spawner.profile is not None
    assert spawner.profile.name == "Arterial Split"
    assert spawner.profile.directional_weights["east"] == 2.0
    assert spawner.profile.turn_probs == [0.6, 0.2, 0.2]
    assert spawner.lambda_rate == 0.8

