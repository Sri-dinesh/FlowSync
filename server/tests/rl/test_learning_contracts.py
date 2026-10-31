"""Atomic checkpoint loading and supervisor input contracts."""
from copy import deepcopy
import pytest
import torch
from app.controllers.supervisor import ControllerSupervisor, ControlAuthority
from app.rl.dqn_agent import DQNAgent


def test_supervisor_rejected_input_preserves_authority_and_counters():
    for args in (dict(threshold_low=.9,threshold_high=.1),dict(min_dwell_steps=-1),dict(recovery_window_steps=.5)):
        with pytest.raises(ValueError):
            ControllerSupervisor(**args)
    supervisor = ControllerSupervisor(min_dwell_steps=1,recovery_window_steps=1)
    state = deepcopy(vars(supervisor))
    with pytest.raises(ValueError):
        supervisor.update(float("nan"),1)
    assert vars(supervisor) == state
    assert supervisor.update(.9,1) == ControlAuthority.FALLBACK_ACTIVE
    assert supervisor.update(.1,2) == ControlAuthority.RL_ACTIVE



def test_same_shape_different_schema_and_bad_target_reject_atomically():
    agent = DQNAgent(state_dim=48,obs_version="v9_48dim_zero_spatial")
    state = deepcopy(agent.get_checkpoint_state())
    other = deepcopy(state)
    other["obs_version"] = "v9_48dim_spatial"
    with pytest.raises(ValueError,match="observation"):
        agent.load_checkpoint_state(other)
    bad = deepcopy(state)
    key = next(iter(bad["target_net"]))
    bad["target_net"][key] = torch.zeros(1)
    with pytest.raises(ValueError,match="Incompatible"):
        agent.load_checkpoint_state(bad)
    assert all(torch.equal(v,state["online_net"][k]) for k,v in agent.online_net.state_dict().items())
    state.update(step_count=4,total_train_steps=11)
    agent.load_checkpoint_state(state)
    assert (agent.step_count,agent.total_train_steps) == (4,11)
