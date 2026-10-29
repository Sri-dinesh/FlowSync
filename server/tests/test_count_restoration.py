from dataclasses import replace

import numpy as np
import pytest
import torch

from research.observation.count_restoration import CountRestorer,PacketHistory,RestorationInjector,counts,predict,update_ema,EMA_ALPHAS,VERSION
from research.noise.fault_injector import FaultProfile,PerceptionFaultInjector
from research.pilots.run_count_restoration_pilot import dataset_cases,control_jobs,reconstruction,control_summary,collect,fit_model
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.training.train_policy import load_split
from research.training.train_policy import RunBudget
from server.app.controllers.base import ControllerContext
from server.app.controllers.max_pressure import MaxPressureController


def observation(n):
    result=np.zeros(28,dtype=np.float32)
    result[:12]=np.tanh(np.asarray(n if isinstance(n,list) else [n]*12,dtype=np.float32)/15)
    return result


def context(step=0):
    return ControllerContext(timestep=step,current_phase=0,time_in_phase=10.,outgoing_counts={"north":4},extra_telemetry={})


def checkpoint(tmp_path,bias=0.):
    model=CountRestorer()
    with torch.no_grad(): model.net[-1].bias.fill_(bias)
    path=tmp_path/'restorer.pt'
    torch.save(dict(schema_version=VERSION,state_dict=model.state_dict()),path)
    return path


def test_history_is_causal_resets_gaps_and_marks_missing_lags():
    history=PacketHistory()
    first=history.update(observation(1),context())
    assert first.shape==(12,17) and not first[:,11:14].any()
    second=history.update(observation(2),context(1))
    assert np.allclose(second[:,1],1/15) and np.all(second[:,11]==1)
    assert np.allclose(first[:,5],1/15)  # Future input never mutates previous features.
    gap=history.update(observation(3),context(20))
    assert not gap[:,11:14].any() and np.allclose(gap[:,4],3/15)
    with pytest.raises(ValueError): history.update(observation(4),context(20))


def test_zero_model_is_identity_and_unsupported_demand_stays_zero():
    model=CountRestorer()
    features=PacketHistory().update(observation([0,1,2,3,4,5,6,7,8,9,10,11]),context())
    assert np.array_equal(predict(model,features),np.arange(12))
    with torch.no_grad(): model.net[-1].bias.fill_(100)
    estimated=predict(model,features)
    assert estimated[0]==0 and np.all(estimated<=np.arange(12)+2)
    with torch.no_grad(): model.net[-1].bias.fill_(-100)
    assert not predict(model,features).any()


def test_only_delivered_packet_can_influence_nontrivial_restoration(tmp_path):
    adapter=RestorationInjector(FaultProfile(miss_rate=.9),9,model_path=checkpoint(tmp_path,.2))
    delivered=observation(1)
    def fixed_packet(clean_obs,step,ctx):
        ctx.extra_telemetry={"observation_age_ms":0,"frame_dropped":False}
        ctx.outgoing_counts={"north":1}
        return delivered.copy()
    adapter.base.corrupt_observation=fixed_packet
    first=adapter.corrupt_observation(observation(2),0,context())
    adapter.reset(9)
    second=adapter.corrupt_observation(observation(90),0,context())
    assert np.array_equal(first,second) and not np.array_equal(first,delivered)
    assert np.array_equal(first[12:],delivered[12:])


def test_identity_preserves_fault_draws_metadata_and_reset(tmp_path):
    fault=FaultProfile(miss_rate=.2,latency_ms=200,frame_drop_prob=.3,false_positive_lambda=.1)
    original=PerceptionFaultInjector(fault,seed=9123)
    adapter=RestorationInjector(fault,9123,model_path=checkpoint(tmp_path))
    for step in range(20):
        first,second=context(step),context(step)
        clean=observation(step%6)
        raw=original.corrupt_observation(clean,step,first)
        restored=adapter.corrupt_observation(clean,step,second)
        assert np.array_equal(raw,restored)
        assert first.extra_telemetry==second.extra_telemetry and first.outgoing_counts==second.outgoing_counts
    adapter.reset(9123)
    assert adapter.changed_packets==0 and adapter.history.last_step is None


@pytest.mark.parametrize("alpha",EMA_ALPHAS)
def test_ema_bank_and_deployed_scalar_use_identical_arithmetic(alpha):
    bank=np.zeros((4,12),dtype=np.float32)
    scalar=np.zeros(12,dtype=np.float32)
    rng=np.random.default_rng(10)
    for _ in range(30):
        raw=rng.integers(0,20,size=12).astype(np.float32)
        bank=update_ema(bank,raw,np.asarray(EMA_ALPHAS,dtype=np.float32)[:,None])
        scalar=update_ema(scalar,raw,alpha)
        assert np.array_equal(scalar,bank[EMA_ALPHAS.index(alpha)])


def test_panels_use_disjoint_traffic_seeds_and_training_only_sources():
    fit,probe=dataset_cases('fit'),dataset_cases('probe')
    assert len(fit)==24 and len(probe)==12 and len(control_jobs())==18
    assert {c['seed'] for c in fit}.isdisjoint(c['seed'] for c in probe)
    assert all(c['scenario']['split']=='train' for c in fit+probe)


def test_perfect_reconstruction_passes_and_identity_cannot_fake_gain(tmp_path):
    from research.pilots.run_count_restoration_pilot import count_metrics
    data=dict(x=np.zeros((2,12,17),dtype=np.float32),y=np.ones((2,12),dtype=np.float32),
              raw=np.ones((2,12),dtype=np.float32),case_ids=np.array([0,1]))
    cases=[dict(fault=dict(name='clean')),dict(fault=dict(name='validation_mixed'))]
    measured=count_metrics(data['raw'],data,cases)
    assert measured==dict(mae=0.,positive_mae=0.,clean_mae=0.)
    # A reconstruction screen needs actual error reduction, checked on nonzero errors.
    data['raw'][1]=0
    data['ema']=np.repeat(data['raw'][:,None,:],4,axis=1)
    for seed in (101,202,303):
        model=CountRestorer()
        torch.save(dict(state_dict=model.state_dict()),tmp_path/f'restorer_{seed}.pt')
    report=reconstruction(data,cases,tmp_path,dict(ema_alpha=1.))
    assert not report['continue_to_control']
    # A real tiny network implementing max(current, history max) recovers this toy dropout.
    data['x'][0,:,0]=1/15
    data['x'][:,:,5]=1/15
    for seed in (101,202,303):
        model=CountRestorer()
        with torch.no_grad():
            for parameter in model.parameters(): parameter.zero_()
            model.net[0].weight[0,5]=1
            model.net[0].weight[0,0]=-1
            model.net[2].weight[0,0]=1
            model.net[4].weight[0,0]=1
        torch.save(dict(state_dict=model.state_dict()),tmp_path/f'restorer_{seed}.pt')
    assert reconstruction(data,cases,tmp_path,dict(ema_alpha=1.))['continue_to_control']


def test_control_screen_rejects_gain_with_tail_loss():
    rows=[]
    for fault in ('clean','validation_mixed'):
        for actor,arm in control_jobs():
            rows.append(dict(actor=actor,arm=arm,fault=fault,delay=8. if arm=='restored' else 10.,
                             p95=30. if arm=='restored' else 20.,passed=90,violations=0))
    report=control_summary(rows)
    assert not report['continue_to_expanded_validation']
    assert not report['checks']['mixed_p95_vs_raw']


def test_identity_restoration_matches_pressure_closed_loop(tmp_path):
    torch.set_num_threads(1)
    scenario=replace(load_split('train')[0],duration_steps=300,scenario_hash='')
    fault=FaultProfile(miss_rate=.2,latency_ms=200,false_positive_lambda=.1)
    raw=ExperimentRunner().run(ShieldedController(MaxPressureController()),scenario,1320901,
        fault_injector=PerceptionFaultInjector(fault,seed=1410901))
    restored=ExperimentRunner().run(ShieldedController(MaxPressureController()),scenario,1320901,
        fault_injector=RestorationInjector(fault,1410901,model_path=checkpoint(tmp_path)))
    assert raw.trajectory==restored.trajectory and raw.avg_delay==restored.avg_delay


def test_supervised_updates_move_weights_and_refit_exactly():
    torch.set_num_threads(1)
    x=PacketHistory().update(observation(1),context())
    data=dict(x=x[None],y=np.full((1,12),2.,dtype=np.float32))
    first,curve=fit_model(data,101,RunBudget(30))
    second,repeated=fit_model(data,101,RunBudget(30))
    assert curve==repeated and all(torch.equal(value,second.state_dict()[key]) for key,value in first.state_dict().items())
    assert curve[-1]['loss']<curve[0]['loss']
    assert torch.count_nonzero(first.net[-1].weight)>0


def test_real_source_collection_pairs_current_truth_with_delivered_features(tmp_path):
    torch.set_num_threads(1)
    case=dataset_cases('fit')[0]
    case.update(seed=1320901,case_id='mechanics_clean')
    data,summary=collect([case],RunBudget(30),tmp_path/'fixture.npz')
    assert data['x'].shape==(240,12,17)
    assert np.array_equal(data['raw'],data['y'])
    assert np.allclose(data['x'][:,:,0]*15,data['raw'])
    assert summary[0]['signal_samples']==1200 and summary[0]['signal_violations']==0
