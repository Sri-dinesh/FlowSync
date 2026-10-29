import copy
from types import SimpleNamespace

import numpy as np
import pytest

from research.audits.audit_decision_cadence import due_probe, early_state, future_seed, summarize, source
from research.pilots.run_switch_margin_pilot import PARENTS, PARENT_ROOT
from research.scenarios.loader import load_scenario
from research.training.train_policy import RunBudget
import torch
from server.app.controllers.base import ControllerContext
from server.app.controllers.safety_shield import SafetyShield


def context(step=205):
    return ControllerContext(timestep=step,current_phase=0,time_in_phase=15.,valid_action_mask=np.array([True,True,False,False]),
                             movement_queues={"east_straight":2},phase_starvation_times={})


@pytest.mark.parametrize("step,deadline,held,expected", [(205,220,0,True),(200,200,0,False),(206,220,0,False),
                                                      (195,220,0,False),(605,620,0,False),(205,220,1,False)])
def test_probe_only_inside_aligned_cached_current_phase_holds(step,deadline,held,expected):
    assert bool(due_probe(context(step),deadline,held)) is expected


def test_early_decision_resets_hold_in_copied_controller_only():
    original=SimpleNamespace(d3qn=SimpleNamespace(_held_action=0,_next_decision_step=220,_last_diagnostics={}),safety_shield=SafetyShield())
    copied=copy.deepcopy(original)
    state=(None,None,None,copied)
    assert early_state(state,1,context())==1
    assert copied.d3qn._next_decision_step==225 and copied.d3qn._held_action==1
    assert original.d3qn._next_decision_step==220 and original.d3qn._held_action==0
    with pytest.raises(ValueError): early_state(state,2,context())


def test_future_keys_stable_and_distinct():
    case=dict(parent="101",scenario={"scenario_id":"train_mod_balanced_01"},seed=1310001)
    assert future_seed(case,205,0)==future_seed(case,205,0)
    assert len({future_seed(case,205,i) for i in range(8)})==8


def test_empty_or_concentrated_gate_panel_cannot_continue():
    sources=[dict(case=dict(parent=p),gate=None,signal_samples=1200,signal_violations=0) for p in ("101","202","303") for _ in range(3)]
    report=summarize(sources,[])
    assert not report["continue_to_scheduler_pilot"] and report["mean_gain"] is None
    for source in sources[:3]: source["gate"]={"step":205}
    assert not summarize(sources,[])["checks"]["eligible_sources"]


def test_positive_screen_requires_stable_gates_and_limits_harm():
    sources=[dict(case=dict(parent=p),gate={"step":205},signal_samples=1200,signal_violations=0) for p in PARENTS for _ in range(3)]
    good=dict(gain=[2.,0.,0.],qualified=True,harmful=False,outcomes={a:dict(signal_samples=400,signal_violations=0) for a in ("parent","early")})
    records=[dict(case=s["case"],futures=[copy.deepcopy(good) for _ in range(8)]) for s in sources]
    assert summarize(sources,records)["continue_to_scheduler_pilot"]
    for record in records:
        for future in record["futures"][:3]: future.update(gain=[-2.,0.,0.],qualified=False,harmful=True)
    assert not summarize(sources,records)["continue_to_scheduler_pilot"]


def test_actual_source_and_fork_replay_when_local_parent_available():
    if not (PARENT_ROOT/PARENTS["101"][0]).exists(): pytest.skip("Optional local frozen checkpoint.")
    torch.set_num_threads(1)
    case=dict(parent="101",scenario=load_scenario("train_mod_balanced_01").to_dict(),seed=1310901)
    baseline,_=source(case,RunBudget(60))
    replay,branches=source(case,RunBudget(60),baseline["gate"])
    assert replay==baseline and baseline["signal_samples"]==1200
    if baseline["gate"] is not None:
        assert len(branches)==8
        assert all(f["outcomes"]["parent"]["arrival_trace_hash"]==f["outcomes"]["early"]["arrival_trace_hash"] for f in branches)
