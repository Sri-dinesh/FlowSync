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
        )
