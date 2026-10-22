import pytest

from research.audits.audit_control_interventions import fork_state, rollout_branch
from research.audits.audit_spatial_inputs import audit_source
from research.experiments.branch_prefixes import rollout_prefixes
from research.noise.fault_injector import FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig
from server.tests.test_spatial_input_audit import spatial_model


@pytest.mark.parametrize("fault",[FaultProfile(),FaultProfile(miss_rate=.2,latency_ms=200,frame_drop_prob=.1)])
def test_prefixes_equal_independent_original_rollouts(spatial_model,fault):
    path,model=spatial_model
    scenario=ScenarioConfig("train_fixture","train","Fixture",duration_steps=1200)
    case=dict(role="online",index=1,seed=10201,fault=fault.to_dict(),scenario=scenario.to_dict(),acting="spatial")
    compared=[]
    def hook(event,env,sensor,injector,controller,context,scenario):
        if compared or event["step"]+600>1200: return
        action=event["execution"]
        states=[fork_state(env,sensor,injector,controller) for _ in range(3)]
        before=controller.d3qn._held_action,controller.d3qn._next_decision_step
        outputs=rollout_prefixes(states[0],scenario,event["step"],(200,600),action)
        assert outputs[200]==rollout_branch(states[1],scenario,event["step"],200,action)
        assert outputs[600]==rollout_branch(states[2],scenario,event["step"],600,action)
        assert (controller.d3qn._held_action,controller.d3qn._next_decision_step)==before
        compared.append(True)
    audit_source(case,path,{"spatial_90":model},branches=False,gate_hook=hook)
    assert compared


@pytest.mark.parametrize("horizons",[(),(0,),(200,200),(600,200),(1.5,),(-1,)])
def test_invalid_horizons_fail_before_simulation(horizons):
    with pytest.raises(ValueError,match="integer horizons"):
        rollout_prefixes(None,None,0,horizons,0)


def test_horizon_extension_cannot_promote_a_failed_teacher():
    import copy
    from research.audits.audit_teacher_horizon import summarize
    from server.tests.test_teacher_alignment import panel
    frozen,originals=panel()
    rows=[]
    for old in originals:
        events=[]
        for event in old["events"]:
            futures=[]
            for future in event["teacher_futures"]:
                branches={}
                for name,branch in future["branches"].items():
                    short=dict(branch["outcome"],physical_switches=1)
                    long=dict(short,signal_samples=600)
                    branches[name]=dict(proposal=branch["proposal"],first_execution=branch["first_execution"],
                        prefixes={"200":short,"600":long})
                futures.append(dict(role=future["role"],replicate=future["replicate"],arrival_seed=future["arrival_seed"],branches=branches))
            events.append(dict(step=event["step"],prefix_20_reproduced=True,futures=futures))
        rows.append(dict(training_seed=old["training_seed"],index=old["index"],source_replay_verified=True,
                         signal_samples=1200,signal_violations=0,events=events))
    result=summarize(rows,frozen,"completed")
    assert result["complete"] and result["aggregate_reversal_without_throughput_or_wait_loss"]
    assert result["every_parent_nonnegative"]
    assert not result["continue_to_training"] and result["original_20_second_screen"].startswith("failed")
    assert result["signal_samples"]==9*1200+18*16*2*600
    with pytest.raises(ValueError,match="Duplicate"):
        summarize(rows+[copy.deepcopy(rows[0])],frozen,"completed")
    rows[0]["events"][0]["futures"][0]["branches"]["upstream_mp"]["prefixes"]["600"]["arrival_trace_hash"]="wrong"
    with pytest.raises(ValueError,match="Unpaired"):
        summarize(rows,frozen,"completed")
