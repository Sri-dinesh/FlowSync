import copy
from types import SimpleNamespace

import numpy as np
import pytest

from research.audits.audit_teacher_alignment import (
    FUTURES, NAMES, freeze_sources, future_seed, resample, score,
)
from server.app.controllers.base import ControllerContext
from server.app.controllers.safety_shield import SafetyShield


def inputs():
    rows, cases = [], {}
    for seed in (101,202,303):
        cases[f"spatial_{seed}"]=[]
        for index in (1,46,90):
            case=dict(role="online",index=index,seed=seed*1000+index,
                scenario=dict(split="train",scenario_id="fixture"))
            cases[f"spatial_{seed}"].append(case)
            rows.append(dict(role="online",acting="spatial",training_seed=seed,index=index,seed=case["seed"],
                events=[dict(step=s,mask=[True,True,False,False],proposal=0,
                             teacher_proposals=dict(historical_mp=0,upstream_mp=1)) for s in (100,200,300,1100)]))
    return rows,dict(cases=cases)


def panel():
    originals,manifest=inputs()
    frozen=freeze_sources(originals,manifest)
    rows=[]
    for source in frozen:
        events=[]
        for gate in source["gates"]:
            futures=[]
            for role,indices in FUTURES.items():
                for index in indices:
                    outcomes={p:dict(proposal=p,first_execution=p,outcome=dict(
                        incremental_delay_vehicle_seconds=100.-10*p,vehicles_passed=3,
                        upstream_max_wait_s=10.,arrival_trace_hash=f"paired{index}",signal_samples=200,signal_violations=0)) for p in (0,1)}
                    futures.append(dict(role=role,replicate=index,arrival_seed=future_seed(source["training_seed"],"fixture",
                        source["case"]["seed"],gate["step"],index),branches={n:outcomes[p] for n,p in gate["proposals"].items()}))
            events.append(dict(step=gate["step"],teacher_futures=futures))
        rows.append(dict(training_seed=source["training_seed"],index=source["index"],seed=source["case"]["seed"],
                         signal_samples=1200,signal_violations=0,source_replay_verified=True,events=events))
    return frozen,rows


def test_freeze_uses_first_two_eligible_disagreements_and_disjoint_keys():
    rows,manifest=inputs()
    frozen=freeze_sources(rows,manifest)
    assert len(frozen)==9 and all([g["step"] for g in s["gates"]]==[100,200] for s in frozen)
    gate=frozen[0]["gates"][0]
    first={v["seed"] for v in gate["future_seeds"]["first"]}
    excluded={v["seed"] for v in gate["future_seeds"]["excluded"]}
    assert len(first)==len(excluded)==8 and not first & excluded
    rows[0]["events"]=[]
    assert freeze_sources(rows,manifest)[0]["gates"]==[]
    manifest["cases"]["spatial_101"][0]["scenario"]["split"]="test"
    with pytest.raises(ValueError,match="training cases"):
        freeze_sources(rows,manifest)


def test_screen_counts_unique_branches_and_requires_all_replicates():
    frozen,rows=panel()
    r=score(rows,frozen)
    assert r["complete"] and r["continue_to_learning_pilot"]
    assert r["eligible_gates"]==18 and r["signal_samples"]==9*1200+18*16*2*200
    assert r["panels"]["excluded"]["comparisons"]["policy"]["mean_gain"]==[10.,0.,0.]
    assert not score(rows[:-1],frozen)["continue_to_learning_pilot"]
    assert not score(rows,frozen,"wall_clock_budget")["continue_to_learning_pilot"]
    for row in rows:
        if row["training_seed"]==303:
            row["events"]=[]
    for s in frozen:
        if s["training_seed"]==303:
            s["gates"]=[]
    assert not score(rows,frozen)["checks"]["each_parent_robustly_beneficial"]


def test_excluded_harm_cannot_be_hidden_by_first_future_success():
    frozen,rows=panel()
    for f in rows[0]["events"][0]["teacher_futures"]:
        if f["role"]=="excluded":
            f["branches"]["upstream_mp"]["outcome"]["upstream_max_wait_s"]=20.
    r=score(rows,frozen)
    assert r["checks"]["positive_aggregate_delay_vs_both"]
    assert not r["checks"]["every_gate_robust"] and not r["continue_to_learning_pilot"]
    assert r["panels"]["first"]["joint_nonharm_cases"]==18*8


@pytest.mark.parametrize("mutation,match",[("seed","seed"),("trace","Unpaired"),("coverage","partition"),
    ("source","Duplicate"),("samples","signal samples"),("proposal","frozen branch")])
def test_raw_integrity_failures_are_rejected(mutation,match):
    frozen,rows=panel()
    f=rows[0]["events"][0]["teacher_futures"][0]
    if mutation=="seed": f["arrival_seed"]+=1
    if mutation=="trace": f["branches"]["upstream_mp"]["outcome"]["arrival_trace_hash"]="wrong"
    if mutation=="coverage": rows[0]["events"][0]["teacher_futures"].pop()
    if mutation=="source": rows.append(copy.deepcopy(rows[0]))
    if mutation=="samples": f["branches"]["upstream_mp"]["outcome"]["signal_samples"]=0
    if mutation=="proposal": f["branches"]["upstream_mp"]["proposal"]=0
    with pytest.raises(ValueError,match=match): score(rows,frozen)


def test_resampling_forks_only_future_rng_and_preserves_hold_schedule(monkeypatch):
    from research.audits import audit_teacher_alignment as module
    env=SimpleNamespace(intersection=SimpleNamespace(spawner=SimpleNamespace(_rng=np.random.default_rng(42),pending=[1,2])))
    controller=SimpleNamespace(d3qn=SimpleNamespace(_held_action=0,_next_decision_step=120),safety_shield=SafetyShield())
    context=ControllerContext(100,time_in_phase=10.,valid_action_mask=np.array([True,True,False,False]))
    original=copy.deepcopy(env.intersection.spawner._rng.bit_generator.state)
    monkeypatch.setattr(module,"fork_state",lambda *state:copy.deepcopy(state))
    seen=[]
    def rollout(state,scenario,step,horizon,first):
        assert state[0].intersection.spawner.pending==[1,2]
        assert state[3].d3qn._next_decision_step==120
        seen.append(state[3].d3qn._held_action)
        return dict(arrival_trace_hash=str(state[0].intersection.spawner._rng.integers(1000000)))
    monkeypatch.setattr(module,"rollout_branch",rollout)
    out=resample(dict(step=100),env,None,None,controller,context,SimpleNamespace(scenario_id="fixture"),101,601001,
                 dict(zip(NAMES,[0,0,1])))
    assert len(out)==16 and len(seen)==32 and seen==[0,1]*16
    assert env.intersection.spawner._rng.bit_generator.state==original
    assert controller.d3qn._held_action==0 and controller.safety_shield.total_evaluations==0
