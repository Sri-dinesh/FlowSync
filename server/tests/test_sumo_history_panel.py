"""History factorial, controls and frozen screens use synthetic outcomes only."""
from copy import deepcopy

import pytest

from research.analysis.sumo_history_metrics import summarize
from research.pilots import run_sumo_history_panel as study


def rows():
    result=[]
    for job in study.jobs():
        value=dict(instant_clean=10,lag_clean=9.5,mean_clean=8,instant_mixed=9,mean_mixed=8.5)[job['method']]
        measured={str(end//10):dict(requested_vehicles=100,signal_samples=end,
            mean_stopped_wait_per_requested_vehicle_s=value,p95_accumulated_wait_s=2*value,completed_trips=150-value,
            measured_signal_violations=0,service=dict(green_ns_s=end/25,green_ew_s=end/25,clearance_s=end/50,history_changed_gates=1))
            for end in (1800,3600)}
        p=next(p for p in study.plans() if p['seed']==job['seed'])
        result.append(dict(**job,family=p['family'],measurements=measured))
    return result


def analyze(data): return study.analyze(data,False)


def test_full_factorial_and_pure_lag_control_are_frozen_before_collection():
    full,smoke=study.jobs(),study.jobs(True)
    assert len(full)==60 and sum(j['steps'] for j in full)==216000
    assert len(smoke)==36 and sum(j['steps'] for j in smoke)==24800
    assert {j['seed'] for j in full}.isdisjoint({j['seed'] for j in smoke})
    assert study.configuration()['window_ticks']==20
    assert study.anchor_for('lag_clean').fault=='delay2s'


@pytest.mark.parametrize('change',['method','window','gate','seed'])
def test_invalid_protocol_is_rejected_before_collection(tmp_path,monkeypatch,change):
    spec=study.protocol()
    if change=='method': spec['methods'][2]['fault']='delay2s_miss30'
    elif change=='window': spec['window_ticks']=19
    elif change=='gate': spec['candidate_screen']['no_start_group_mean_delay_loss']=False
    else: spec['families'][1]['seeds'][0]=spec['families'][0]['seeds'][0]
    path=tmp_path/study.SPEC; path.parent.mkdir(parents=True)
    path.write_text(study.json.dumps(spec))
    monkeypatch.setattr(study,'ROOT',tmp_path)
    with pytest.raises(ValueError): study.protocol()


def test_seed_level_inference_and_history_by_sensor_interaction():
    result=analyze(rows()); endpoint=result['endpoint_comparisons']['360']
    interaction=endpoint['contrasts']['history_by_sensing_interaction']
    wait=interaction['metrics']['mean_stopped_wait_per_requested_vehicle_s']
    assert wait['mean']==1.5 and wait['interval']==dict(lower=1.5,upper=1.5,ordered_draws=64)
    assert len(interaction['seed_rows'])==6 and len(interaction['context_rows'])==12
    assert result['replication']['traffic_seeds']==6 and result['replication']['prefix_endpoints_overlap']
    assert result['candidate_screen']['continue_to_bounded_development']
    assert not result['candidate_screen']['automatic_promotion']


def test_primary_aggregate_cannot_hide_bad_seed_or_replace_primary_with_noise_arm():
    data=rows(); seed=data[0]['seed']
    for row in data:
        if row['seed']==seed and row['method']=='mean_clean':
            row['measurements']['360']['mean_stopped_wait_per_requested_vehicle_s']=11
    screen=analyze(data)['candidate_screen']
    assert screen['comparisons']['mean_clean_vs_instant_clean']['delay_gain_fraction']>0.02
    assert 'seed_loss_mean_clean_vs_instant_clean' in screen['failures']
    assert not screen['continue_to_bounded_development']


def test_mixed_sensing_loss_blocks_continuation_even_when_primary_passes():
    data=rows()
    for row in data:
        if row['method']=='mean_mixed': row['measurements']['360']['mean_stopped_wait_per_requested_vehicle_s']=9.5
    screen=analyze(data)['candidate_screen']
    assert 'mean_wait_mean_mixed_vs_instant_mixed' in screen['failures']
    assert 'start_group_loss_mean_mixed_vs_instant_mixed' in screen['failures']
    assert not screen['continue_to_bounded_development']


def test_starts_are_averaged_inside_seed_but_start_group_harm_is_retained():
    data=rows()
    for row in data:
        if row['method']=='mean_clean':
            row['measurements']['360']['mean_stopped_wait_per_requested_vehicle_s']=11 if row['initial_phase']==0 else 5
    result=analyze(data)
    assert next(iter(result['endpoint_comparisons']['360']['seed_means'].values()))['mean_clean']['mean_stopped_wait_per_requested_vehicle_s']==8
    assert 'start_group_loss_mean_clean_vs_instant_clean' in result['candidate_screen']['failures']


@pytest.mark.parametrize('change',['missing','duplicate','order','denominator'])
def test_invalid_scientific_grid_is_rejected(change):
    data=rows()
    if change=='missing': data.pop()
    elif change=='duplicate': data[-1]=deepcopy(data[0])
    elif change=='order': data[0],data[1]=data[1],data[0]
    else: data[0]['measurements']['180']['requested_vehicles']=99
    with pytest.raises(ValueError): analyze(data)


def smoke_rows():
    result=[]
    for job in study.jobs(True):
        key=f"{job['initial_phase']}_{job['method']}"
        result.append(dict(**job,semantic_trace_sha256='prefix_'+key if job['kind']=='prefix' else key,
            prefix_trace_sha256='prefix_'+key,physical_trace_sha256=key,proposal_trace_sha256=key,
            historical_trace_sha256=key+('_sensor_delay' if job['kind']=='anchor' and job['method']=='lag_clean' else ''),
            measurements={'80':dict(service=dict(history_changed_gates=1))}))
    return result


def test_mechanics_requires_repeat_prefix_lag_anchor_and_active_mean_on_both_sensors():
    result=study.analyze(smoke_rows(),True)
    assert result['candidate_screen'] is None and not result['endpoint_comparisons']
    assert result['mechanics']['lag_physics_and_proposals_verified']
    assert result['mechanics']['mean_changed_gates']==dict(mean_clean=2,mean_mixed=2)


@pytest.mark.parametrize('change',['repeat','prefix','lag_proposal','instant_packet','inactive_mean'])
def test_smoke_cannot_pass_on_execution_alone(change):
    data=smoke_rows()
    if change=='repeat': data[1]['semantic_trace_sha256']='changed'
    elif change=='prefix': next(r for r in data if r['kind']=='prefix')['semantic_trace_sha256']='changed'
    elif change=='lag_proposal': next(r for r in data if r['kind']=='anchor' and r['method']=='lag_clean')['proposal_trace_sha256']='changed'
    elif change=='instant_packet': next(r for r in data if r['kind']=='anchor' and r['method']=='instant_mixed')['historical_trace_sha256']='changed'
    else:
        for row in data:
            if row['method']=='mean_mixed': row['measurements']['80']['service']['history_changed_gates']=0
    with pytest.raises(ValueError): study.analyze(data,True)
