from dataclasses import replace

import numpy as np
import pytest
import torch

from research.policies.switch_margin import SwitchMarginD3QN, SwitchMarginPressure
from research.pilots.run_switch_margin_pilot import select, GRIDS, PARENTS, PARENT_ROOT
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.training.train_policy import load_split
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.max_pressure import MaxPressureController


@pytest.mark.parametrize("margin", [-1., float("nan"), float("inf")])
def test_invalid_margin_rejected(margin):
    with pytest.raises(ValueError): SwitchMarginPressure(margin)


def test_pressure_margin_holds_small_advantage_and_preserves_zero_behavior():
    context = ControllerContext(timestep=100, current_phase=0, movement_queues={"north_straight":2,"east_straight":3},outgoing_counts={})
    obs = np.zeros(28)
    assert SwitchMarginPressure(0).act(obs,context) == MaxPressureController().act(obs,context) == 1
    controller = SwitchMarginPressure(.1)
    assert controller.act(obs,context) == 0
    assert controller.get_diagnostics()["margin_holds"] == 1
    assert controller.act(obs,replace(context,movement_queues={"north_straight":2,"east_straight":10})) == 1


def test_d3qn_margin_acts_only_at_original_decisions_and_respects_mask():
    # Exercise actual masked dueling inference and cadence with fixed advantages.
    controller = SwitchMarginD3QN.__new__(SwitchMarginD3QN)
    D3QNController.__init__(controller)
    with torch.no_grad():
        for parameter in controller.agent.online_net.parameters(): parameter.zero_()
        controller.agent.online_net.advantage_stream[-1].bias.copy_(torch.tensor([0.,.4,-10.,-10.]))
    controller.margin, controller.margin_holds, controller.switch_proposals = .5, 0, 0
    context = ControllerContext(timestep=0,current_phase=0,valid_action_mask=np.array([True,True,False,False]),
                                outgoing_counts={},phase_starvation_times={})
    obs = np.zeros(28)
    assert controller.act(obs,context) == 0
    assert controller.act(obs,replace(context,timestep=1)) == 0
    assert controller.margin_holds == 1
    assert controller.act(obs,replace(context,timestep=20,valid_action_mask=np.array([False,True,False,False]))) == 1


def test_fit_selection_rejects_tail_tradeoff_and_keeps_zero_on_ties():
    rows=[]
    for model,grid in GRIDS.items():
        for margin in grid:
            rows.append(dict(model=model,margin=margin,delay=10. if margin==0 else 9.,p95=20. if margin==0 else 21.,passed=90,violations=0))
    result=select(rows)
    assert all(m==0 for m in result["parameters"].values())
    assert not result["continue_to_development"]
    for row in rows: row.update(delay=10.,p95=20.)
    assert all(m==0 for m in select(rows)["parameters"].values())


def test_zero_margin_pressure_matches_original_closed_loop():
    scenario=replace(load_split("train")[0],duration_steps=300,scenario_hash="")
    original=ExperimentRunner().run(ShieldedController(MaxPressureController()),scenario,1300902)
    zero=ExperimentRunner().run(ShieldedController(SwitchMarginPressure(0)),scenario,1300902)
    assert original.trajectory == zero.trajectory and original.events == zero.events


@pytest.mark.parametrize("seed", list(PARENTS))
def test_zero_margin_closed_loop_matches_frozen_parent_when_available(seed):
    path=PARENT_ROOT/PARENTS[seed][0]
    if not path.exists(): pytest.skip("Local frozen research checkpoints are optional.")
    torch.set_num_threads(1)
    scenario=replace(load_split("train")[0],duration_steps=300,scenario_hash="")
    original=ExperimentRunner().run(ShieldedController(D3QNController(checkpoint_path=str(path))),scenario,1300901)
    zero=ExperimentRunner().run(ShieldedController(SwitchMarginD3QN(str(path),0)),scenario,1300901)
    for name in ("avg_delay","p95_delay","total_vehicles_passed","arrival_trace_hash","trajectory","events"):
        assert getattr(original,name)==getattr(zero,name)
