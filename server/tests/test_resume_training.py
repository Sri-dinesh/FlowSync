import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import torch

from app.rl.trainer import Trainer
from app.rl.dqn_agent import DQNAgent
from app.services import model_service
from httpx import AsyncClient, ASGITransport
from app.main import app


def test_checkpoint_path_strips_colon_suffix():
    p1 = model_service._checkpoint_path("test-uuid", 500)
    p2 = model_service._checkpoint_path("test-uuid:500", 500)
    assert p1 == "models/test-uuid/checkpoint_500.pt"
    assert p2 == "models/test-uuid/checkpoint_500.pt"

    lp1 = model_service._local_checkpoint_path("test-uuid", 500)
    lp2 = model_service._local_checkpoint_path("test-uuid:500", 500)
    assert lp1.name == "checkpoint_500.pt"
    assert lp1.parent.name == "test-uuid"
    assert lp2.name == "checkpoint_500.pt"
    assert lp2.parent.name == "test-uuid"


@pytest.mark.anyio
async def test_trainer_resume_state_initialization():
    mock_env = MagicMock()
    mock_agent = DQNAgent()
    mock_supabase = MagicMock()
    # Plain callables avoid exercising MagicMock concurrently from the
    # trainer's background persistence thread and checkpoint metadata thread.
    mock_supabase.save_episode = lambda *args, **kwargs: None
    mock_supabase.save_model_metadata = lambda *args, **kwargs: None
    mock_model_service = MagicMock()
    mock_broadcast = AsyncMock()

    checkpoint_state = {
        "online_net": mock_agent.online_net.state_dict(),
        "target_net": mock_agent.target_net.state_dict(),
        "optimizer": mock_agent.optimizer.state_dict(),
        "step_count": 12345,
        "total_train_steps": 5432,
        "obs_version": "v6_28dim_smdp",
        "reward_version": "v4_incremental_delay",
    }
    mock_model_service.load_checkpoint.return_value = checkpoint_state

    trainer = Trainer(
        env=mock_env,
        agent=mock_agent,
        supabase_service=mock_supabase,
        model_service=mock_model_service,
        ws_broadcast_fn=mock_broadcast,
        enable_greedy_warmup=False,
    )

    # Mock environment reset and step to stop immediately
    mask = torch.ones(4, dtype=torch.bool).numpy()
    mock_env.reset_to_decision.return_value = (
        torch.zeros(28).numpy(), {"valid_action_mask": mask}
    )
    mock_env.step_decision.return_value = (
        torch.zeros(28).numpy(),
        0.0,
        True,
        False,
        {
            "executed_action": 0,
            "valid_action_mask": mask,
            "bootstrap_discount": 0.99,
        },
    )
    mock_env.max_steps = 1
    mock_env.intersection.timestep = 0
    mock_env.get_episode_telemetry.return_value = {}
    mock_env.intersection.get_avg_wait_time.return_value = 12.5
    mock_env.intersection.total_passed = 10

    # Train for 1 episode resuming from 1000
    await trainer.train(
        simulation_id="model-abc",
        num_episodes=1,
        resume_model_id="model-abc:1000",
        resume_episode=1000,
    )

    assert trainer.start_episode == 1000
    assert trainer.target_episodes == 1001
    assert trainer.is_resumed is True
    assert trainer.resume_model_id == "model-abc:1000"
    assert trainer.current_episode == 1001
    # Resume deliberately re-opens exploration because replay is not serialized.
    assert trainer.epsilon >= 0.19

    # Verify model_service.load_checkpoint was called with clean id and episode 1000
    mock_model_service.load_checkpoint.assert_called_once_with("model-abc", 1000)

    # Verify resume notification broadcast was sent
    calls = [c[0][0] for c in mock_broadcast.call_args_list]
    resume_calls = [c for c in calls if c.get("type") == "training_resumed"]
    assert len(resume_calls) == 1
    assert resume_calls[0]["start_episode"] == 1000
    assert resume_calls[0]["total_target_episodes"] == 1001

    # Verify episode metric had resume metadata
    metric_calls = [c for c in calls if "episode" in c]
    assert len(metric_calls) >= 1
    assert metric_calls[0]["episode"] == 1001
    assert metric_calls[0]["start_episode"] == 1000
    assert metric_calls[0]["target_episodes"] == 1001
    assert metric_calls[0]["is_resumed"] is True


@pytest.mark.anyio
async def test_start_training_endpoint_with_resume():
    mock_trainer = MagicMock()
    mock_trainer.is_training = False
    mock_trainer.train = AsyncMock()
    app.state.trainer = mock_trainer
    app.state.training_task = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/training/start",
            json={
                "num_episodes": 300,
                "resume_model_id": "089035ea-3b87-4279-8230-00f1c4f10457:1000",
                "resume_episode": 1000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["is_resumed"] is True
        assert data["resume_model_id"] == "089035ea-3b87-4279-8230-00f1c4f10457:1000"
        mock_trainer.train.assert_called_once_with(
            num_episodes=300,
            simulation_id="089035ea-3b87-4279-8230-00f1c4f10457",
            resume_model_id="089035ea-3b87-4279-8230-00f1c4f10457:1000",
            resume_episode=1000,
            is_finetune=False,
            finetune_scenario="rush_hour",
            finetune_lr=1e-4,
            finetune_epsilon=0.25,
            custom_profile=None,
        )
