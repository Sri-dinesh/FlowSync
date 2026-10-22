import copy
import hashlib
import json

import numpy as np
import pytest
import torch

from research.policies.action_rank_policy import (ActionRankController, BOOTSTRAPS, FEATURES, RankedD3QN,
    RankingModel, TARGET_SCALE, action_features, fit_model)
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile,PerceptionFaultInjector
from research.pilots.run_action_rank_pilot import BASELINES, SEEDS, VALIDATION_SEEDS, VARIANTS, summarize_validation
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import VALIDATION_FAULTS
from server.app.controllers.base import ControllerContext
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent


def payload(parent_hash="fixture",gain=.1):
    point=np.zeros((8,3)); point[6,0]=gain
    return dict(version="action_rank_ridge_v1",features=list(FEATURES),parent_sha256=parent_hash,
        scale=[1.]*8,point=point.tolist(),ensemble=np.tile(point,(BOOTSTRAPS,1,1)).tolist(),
        target_scale=TARGET_SCALE.tolist())


def test_features_are_relative_and_ignore_common_q_offset():
    obs=np.linspace(0,.9,36); q=np.array([-10.,-11.,-12.,-13.])
    assert np.array_equal(action_features(obs,0,10.,q,0,0),np.zeros(8))
    np.testing.assert_allclose(action_features(obs,0,10.,q,0,2),action_features(obs,0,10.,q+100,0,2))
    with pytest.raises(ValueError): action_features(np.zeros(28),0,1.,q,0,1)


def test_mask_nonfinite_and_bootstrap_abstention():
    data=payload(); ensemble=np.asarray(data["ensemble"]); ensemble[:10,6,0]=-.2
    data["ensemble"]=ensemble.tolist(); model=RankingModel(data)
    inputs=(np.zeros(36),0,10.,np.zeros(4),0)
    assert model.choose(*inputs,[1,1,1,1],"mean")[0]==2
    assert model.choose(*inputs,[1,1,1,1],"uncertain")[0]==0
    assert model.choose(*inputs,[1,1,0,0],"mean")[0]==0
    assert model.choose(np.full(36,np.nan),*inputs[1:],[1,1,1,1],"mean")[0]==0
    data["scale"][0]=0
    with pytest.raises(ValueError,match="Invalid ranking"): RankingModel(data)


def training_rows():
    rows=[]
    for i in range(4):
        base=dict(incremental_delay_vehicle_seconds=20.,vehicles_passed=2,upstream_max_wait_s=10.)
        rows.append(dict(training_seed=101,checkpoint_hash="fixture",split="train",scenario=f"train_{i}",seed=94001,
            fault=dict(name="clean"),events=[dict(policy_proposal=0,phase=0,phase_age=10.+i,
                policy_observation=(np.linspace(0,.5,36)+i*.01).tolist(),q_values=[0.,-1.,-2.,-3.],
                all_action_branches=[dict(proposal=a,outcome=dict(base,incremental_delay_vehicle_seconds=20.-a)) for a in (0,1,2)])]))
    return rows


def test_fit_is_deterministic_parent_bound_and_training_only():
    rows=training_rows()
    first=fit_model(rows,101,"fixture")
    assert first==fit_model(rows,101,"fixture")
    assert first["fit_source_groups"]==4 and first["fit_examples"]==8
    RankingModel(first)
    rows[0]["split"]="validation"
    with pytest.raises(ValueError,match="Only training"): fit_model(rows,101,"fixture")
    with pytest.raises(ValueError,match="Mixed parent"): fit_model(training_rows(),202,"fixture")


@pytest.fixture
def artifacts(tmp_path):
    torch.set_num_threads(1)
    agent=DQNAgent(36,"v7_36dim_observed")
    with torch.no_grad():
        for p in agent.online_net.parameters(): p.zero_()
    cp=tmp_path/"parent.pt"; torch.save(agent.get_checkpoint_state(),cp)
    digest=hashlib.sha256(cp.read_bytes()).hexdigest()
    model=tmp_path/"rank.json"; model.write_text(json.dumps(payload(digest)))
    return cp,model


def test_correction_preserves_decision_clock_and_resets(artifacts):
    cp,model=artifacts
    ctrl=RankedD3QN(cp,model,"mean")
    ctx=ControllerContext(100,time_in_phase=10.,valid_action_mask=np.ones(4,dtype=bool))
    assert ctrl.act(np.zeros(28),ctx)==2
    clock=ctrl._next_decision_step
    ctx.timestep=101
    assert ctrl.act(np.zeros(28),ctx)==2 and ctrl._next_decision_step==clock and ctrl.rank_evaluations==1
    ctx.is_decision_step=False
    assert ctrl.act(np.zeros(28),ctx)==ctx.current_phase
    ctrl.reset(1)
    assert ctrl.rank_corrections==ctrl.rank_evaluations==0
    bad=json.loads(model.read_text()); bad["parent_sha256"]="different"; model.write_text(json.dumps(bad))
    with pytest.raises(ValueError,match="does not match"): RankedD3QN(cp,model,"mean")


def test_abstaining_wrapper_reproduces_parent_and_keeps_shield(artifacts):
    cp,model=artifacts
    data=json.loads(model.read_text()); data.update(payload(data["parent_sha256"],gain=0.)); model.write_text(json.dumps(data))
    sc=ScenarioConfig("val_fixture","validation","fixture",duration_steps=500)
    fault=FaultProfile(miss_rate=.2,latency_ms=200)
    parent=FlowSyncUQController(checkpoint_path=str(cp),enable_fallback=False)
    candidate=ActionRankController(cp,model,"uncertain")
    def run(ctrl):
        return ExperimentRunner().run(ctrl,sc,25001,record_trajectory=False,
            fault_injector=PerceptionFaultInjector(fault,seed=115001))
    a,b=run(parent),run(candidate)
    for field in ("avg_delay","p95_delay","total_vehicles_passed","arrival_trace_hash","executed_conflict_violations","executed_clearance_violations"):
        assert getattr(a,field)==getattr(b,field)
    assert b.controller_diagnostics["rank_corrections"]==0
    assert b.controller_diagnostics["rank_executed_changes"]==0
    assert b.controller_diagnostics["shield_enabled"] and not b.controller_diagnostics["fallback_enabled"]


def fake_validation():
    rows=[]
    for traffic in VALIDATION_SEEDS:
        for fault in VALIDATION_FAULTS:
            for name,seed in ([(n,s) for n in ("parent",*VARIANTS) for s in SEEDS]+[(n,None) for n in BASELINES]):
                result=dict(avg_delay=9. if name=="uncertain" else 10.,p95_delay=40.,total_vehicles_passed=50,
                    num_steps=100,safety_samples=100,arrival_trace_hash=str(traffic),executed_conflict_violations=0,
                    executed_clearance_violations=0,controller_diagnostics=dict(rank_corrections=1,rank_executed_changes=1))
                rows.append(dict(name=name,training_seed=seed,scenario="val_fixture",seed=traffic,fault=fault.name,result=result))
    return rows


def test_validation_counts_classical_cells_once_and_rejects_incomplete():
    rows=fake_validation(); result=summarize_validation(rows,["val_fixture"])
    assert result["validation_runs"]==56 and result["continue_to_expanded_validation"]
    assert not result["publication_ready"]
    with pytest.raises(ValueError,match="Incomplete/duplicate"): summarize_validation(rows[:-1],["val_fixture"])
    rows[0]["result"]["arrival_trace_hash"]="different"
    with pytest.raises(ValueError,match="Unpaired"): summarize_validation(rows,["val_fixture"])


def test_inactive_or_parent_regressing_primary_cannot_pass():
    rows=fake_validation()
    for r in rows:
        r["result"]["controller_diagnostics"]["rank_executed_changes"]=0
    assert not summarize_validation(rows,["val_fixture"])["continue_to_expanded_validation"]
