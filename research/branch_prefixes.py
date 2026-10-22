"""Read branch metrics at fixed prefixes without resetting its physical history."""
import hashlib
import json

from research.audit_control_interventions import phase_wait_truth
from research.experiments.runtime import SignalAudit, apply_scenario_step


def rollout_prefixes(state, scenario, start, horizons, first_action, budget=None):
    horizons = tuple(horizons)
    if not horizons or horizons != tuple(sorted(set(horizons))) or any(type(h) is not int or h < 1 for h in horizons):
        raise ValueError("Expected increasing positive integer horizons")
    env,sensor,injector,controller = state
    if scenario.split != "train" or start+max(horizons)>scenario.duration_steps:
        raise ValueError("Prefixes require training traffic and a complete source horizon")
    audit,arrivals,delay,passed = SignalAudit(),hashlib.sha256(),0.,env.intersection.total_passed
    reward,switches,components,outputs = 0.,0,{},{}
    for offset in range(max(horizons)):
        if budget: budget.check("branch_prefix")
        step = start+offset
        if offset:
            apply_scenario_step(env.intersection,env.intersection.spawner.profile,scenario.demand_profile,step)
            obs,context=sensor.build(env,env._get_obs(),step,injector)
            action=controller.act(obs,context)
        else:
            action=first_action
        signal=env.intersection.signal
        before=signal.current_phase,signal.color.name,signal.time_in_phase
        _,tick_reward,_,_,info=env.step(action)
        reward+=tick_reward
        switches+=int(before[1]=="GREEN" and signal.color.name=="YELLOW")
        for name,value in info["reward_components"].items():
            components[name]=components.get(name,0.)+value
        audit.observe(before,signal)
        delay+=env.intersection._delay_this_tick
        arrivals.update(json.dumps([step,env.intersection.spawner.generated_movements_last_tick]).encode())
        if offset+1 in horizons:
            outputs[offset+1]=dict(incremental_delay_vehicle_seconds=delay,
                undiscounted_training_reward=reward,reward_components=dict(components),physical_switches=switches,
                vehicles_passed=env.intersection.total_passed-passed,
                upstream_max_wait_s=max(v["max_accumulated_wait_s"] for v in phase_wait_truth(env.intersection).values()),
                arrival_trace_hash=arrivals.hexdigest(),signal_samples=audit.samples,
                signal_violations=audit.conflicts+audit.clearance_violations)
    return outputs
