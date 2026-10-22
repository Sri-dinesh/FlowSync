import copy

import pytest
import torch

from research.audits.audit_policy_decisions import audit_run
from research.datasets.collect_action_rank_labels import HORIZON, SCENARIOS, SEEDS, TRAFFIC_SEED, summarize
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import VALIDATION_FAULTS
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent


@pytest.mark.parametrize("fault",[FaultProfile(),FaultProfile(miss_rate=.2,latency_ms=200)])
def test_all_action_forks_preserve_source_and_cover_mask(tmp_path,fault):
    torch.set_num_threads(1)
    path=tmp_path/"policy.pt"
    torch.manual_seed(812)
    agent=DQNAgent(36,"v7_36dim_observed")
    torch.save(agent.get_checkpoint_state(),path)
    original=path.read_bytes()
    scenario=ScenarioConfig("train_fixture","train","Fixture",duration_steps=1200)
    measured=audit_run(path,scenario,94001,fault,horizon=400,max_events=3,all_actions=True)
    regular=ExperimentRunner().run(FlowSyncUQController(checkpoint_path=str(path),enable_fallback=False),
        scenario,94001,record_trajectory=False,fault_injector=PerceptionFaultInjector(fault,seed=184001))
    assert round(measured["avg_delay"],3)==regular.avg_delay
    assert measured["arrival_trace_hash"]==regular.arrival_trace_hash
    assert path.read_bytes()==original
    events=[e for e in measured["events"] if "all_action_branches" in e]
    assert 0<len(events)<=3
    assert events[0]["step"]>=200 and all(b["step"]-a["step"]>=200 for a,b in zip(events,events[1:]))
    for event in events:
        branches=event["all_action_branches"]
        assert {b["proposal"] for b in branches}=={i for i,v in enumerate(event["mask"]) if v}
        assert len({b["outcome"]["arrival_trace_hash"] for b in branches})==1
        assert all(b["outcome"]["signal_samples"]==400 and b["outcome"]["signal_violations"]==0 for b in branches)


def synthetic_rows():
    rows=[]
    for seed in SEEDS:
        for scenario in SCENARIOS:
            for fault in VALIDATION_FAULTS:
                branches=[dict(proposal=a,first_execution=a,outcome=dict(
                    incremental_delay_vehicle_seconds=10.-2*a,vehicles_passed=2,upstream_max_wait_s=5.,
                    signal_samples=HORIZON,signal_violations=0,arrival_trace_hash="fixture")) for a in (0,1)]
                rows.append(dict(training_seed=seed,scenario=scenario,fault=fault.to_dict(),split="train",
                    seed=TRAFFIC_SEED,signal_samples=1200,signal_violations=0,events=[dict(step=200,
                        policy_proposal=0,mask=[True,True,False,False],policy_observation=[0.]*36,
                        horizon_steps=HORIZON,all_action_branches=branches)]))
    return rows


def test_summary_distinguishes_hindsight_and_qualified_labels():
    rows=synthetic_rows()
    report=summarize(rows)
    assert report["events_with_qualified_alternative"]==18
    assert not report["learned_controller_evaluated"] and not report["publication_ready"]
    for row in rows:
        row["events"][0]["all_action_branches"][1]["outcome"]["vehicles_passed"]=1
    report=summarize(rows)
    assert report["events_with_delay_opportunity"]==18
    assert report["events_with_qualified_alternative"]==0


@pytest.mark.parametrize("mutation,match",[("missing","Incomplete/duplicate label"),
    ("action","Incomplete/duplicate action"),("pair","Unpaired branch"),("safety","Incomplete branch")])
def test_summary_rejects_incomplete_or_unpaired_evidence(mutation,match):
    rows=synthetic_rows()
    branches=rows[0]["events"][0]["all_action_branches"]
    if mutation=="missing": rows.pop()
    elif mutation=="action": branches.pop()
    elif mutation=="pair": branches[0]["outcome"]["arrival_trace_hash"]="other"
    else: branches[0]["outcome"]["signal_samples"]=0
    with pytest.raises(ValueError,match=match):
        summarize(rows)
