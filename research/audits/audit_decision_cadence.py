"""Training-only prerequisite: fresh observed decisions inside cached holds."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import zipfile

import numpy as np
import torch

from research.audits.audit_arrival_label_stability import replace_future_rng, qualified, harmful
from research.audits.audit_control_interventions import fork_state, rollout_branch
from research.audits.audit_training_drift import score_actions
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.pilots.run_switch_margin_pilot import PARENTS, PARENT_ROOT, ROOT, sha, write
from research.scenarios.loader import load_scenario
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import RunBudget, BudgetExceeded
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.base import ControllerContext
from server.app.controllers.safety_shield import SafetyShield
from server.app.rl.hyperparams import HyperParams
from server.app.rl.observations import encode_policy_observation
from server.app.simulation.benchmark_harness import seed_everything

SCENARIOS = ("train_mod_balanced_01", "train_ns_asymmetric_01", "train_platoon_burst_01")
PLAN = dict(schema_version="decision_cadence_audit_v1", scenarios=SCENARIOS,
    traffic_seeds=[1310001,1310002,1310003], parents=PARENTS, clean_only=True,
    source_ticks=1200, probe_every_ticks=5, eligible_window_ticks=[200,600], branch_ticks=400,
    futures=8, max_wall_seconds=180,
    question="Does delayed reconsideration inside a two-second current-phase hold create a repeatable actionable opportunity?",
    gate="First half-second-aligned step in [200,600] with a cached hold not yet due, executable fresh Q proposal different from current phase, and parent still executing current phase.",
    alternative="Reconsider now using delivered observation; set proposed action and next ordinary decision to now + 2s, then resume unchanged policy/shield/FSM.",
    selection="Freeze all first-eligible gates and future keys after complete source scans, before any branch outcome.",
    availability_prerequisite="Nine sources complete; at least two gates per parent.",
    benefit_screen="All branches complete and paired; mean delay saved >=1 vehicle-second, aggregate throughput not lower, aggregate endpoint max wait saved >=-1s, every parent mean delay nonnegative and at least one gate qualifying on >=6/8 futures, harmful cases <=25%, no measured violations.",
    no_training=True, no_final_test_access=True, no_policy_promotion=True, publication_ready=False,
    related_work="https://ojs.aaai.org/index.php/AAAI/article/view/10918 (action repetition is established; not a reproduced implementation)")


def due_probe(context, deadline, held_action):
    return (200 <= context.timestep <= 600 and context.timestep % 5 == 0
            and context.is_decision_step and context.timestep < deadline
            and held_action == context.current_phase)


def early_state(state, proposal, context):
    controller = state[3]
    if not context.valid_action_mask[proposal] or proposal == context.current_phase:
        raise ValueError("Early proposal must be a valid different phase.")
    controller.d3qn._held_action = proposal
    controller.d3qn._next_decision_step = context.timestep + round(HyperParams().DECISION_DT/context.dt)
    controller.d3qn._last_diagnostics["selected_action"] = proposal
    first = controller.safety_shield.filter_context(proposal, context).executed_action
    if first != proposal:
        raise ValueError("Selected early proposal is not executable under the shared shield.")
    return first


def future_seed(case, step, replicate):
    key = ["cadence-opportunity-v1",case["parent"],case["scenario"]["scenario_id"],case["seed"],step,replicate]
    return int.from_bytes(hashlib.sha256(json.dumps(key).encode()).digest()[:8],"big")


def branches(env,sensor,injector,controller,context,scenario,case,gate,budget):
    results=[]
    for replicate in range(8):
        outcomes={}
        key=future_seed(case,context.timestep,replicate)
        for arm in ("parent","early"):
            budget.check("cadence branches")
            state=fork_state(env,sensor,injector,controller)
            replace_future_rng(state,key)
            first=gate["parent_execution"]
            if arm == "early": first=early_state(state,gate["fresh_proposal"],context)
            outcomes[arm]=rollout_branch(state,scenario,context.timestep,400,first)
        if outcomes["parent"]["arrival_trace_hash"] != outcomes["early"]["arrival_trace_hash"]:
            raise ValueError("Counterfactual arrivals are unpaired.")
        base,new=outcomes["parent"],outcomes["early"]
        gain=[base["incremental_delay_vehicle_seconds"]-new["incremental_delay_vehicle_seconds"],
              new["vehicles_passed"]-base["vehicles_passed"],base["upstream_max_wait_s"]-new["upstream_max_wait_s"]]
        results.append(dict(replicate=replicate,future_seed=key,outcomes=outcomes,gain=gain,
                            qualified=qualified(gain),harmful=harmful(gain)))
    return results


def source(case,budget,branch_gate=None):
    seed_everything(case["seed"])
    scenario=ScenarioConfig.from_dict(case["scenario"])
    env,profile=build_environment(scenario)
    obs,_=env.reset(seed=case["seed"])
    sensor=ObservedState()
    injector=PerceptionFaultInjector(FaultProfile(),seed=case["seed"]+90000)
    controller=FlowSyncUQController(checkpoint_path=str(PARENT_ROOT/PARENTS[case["parent"]][0]),enable_fallback=False)
    controller.reset(case["seed"])
    audit,arrival=SignalAudit(),hashlib.sha256()
    probes,gate,trace,branch_results=[],None,[],None
    for step in range(1200):
        budget.check("cadence source")
        apply_scenario_step(env.intersection,profile,scenario.demand_profile,step)
        delivered,context=sensor.build(env,obs,step,injector)
        deadline=controller.d3qn._next_decision_step
        held=controller.d3qn._held_action
        action=controller.act(delivered,context)
        if due_probe(context,deadline,held):
            encoded=encode_policy_observation(delivered,context,controller.d3qn.agent.obs_version)
            scores=score_actions(controller.d3qn.agent.online_net,encoded,context.valid_action_mask)
            proposed=scores["action"]
            executed=copy.deepcopy(controller.safety_shield).filter_context(proposed,context).executed_action
            event=dict(step=step,phase=context.current_phase,deadline=deadline,parent_execution=action,
                       cached_action=held,
                       fresh_proposal=proposed,fresh_execution=executed,q_values=scores["q_values"],
                       mask=context.valid_action_mask.tolist(),observation=encoded.tolist(),
                       phase_age=context.time_in_phase,phase_waits=context.phase_starvation_times,
                       movement_queues=context.movement_queues)
            probes.append(event)
            if gate is None and action==context.current_phase and proposed!=context.current_phase and executed==proposed:
                gate=event
                if branch_gate is not None:
                    if gate != branch_gate: raise ValueError("First eligible gate did not replay exactly.")
                    branch_results=branches(env,sensor,injector,controller,context,scenario,case,gate,budget)
        signal=env.intersection.signal
        before=(signal.current_phase,signal.color.name,signal.time_in_phase)
        obs,_,_,_,_=env.step(action)
        audit.observe(before,signal)
        arrival.update(json.dumps([step,env.intersection.spawner.generated_movements_last_tick]).encode())
        if step%5==0 or step==1199:
            trace.append([step,signal.current_phase,signal.color.name,action,env.intersection.get_total_waiting()])
    if branch_gate is not None and branch_results is None: raise ValueError("Frozen branch gate was not visited.")
    return dict(case=case,checkpoint_sha256=controller.d3qn.get_diagnostics()["checkpoint_hash"],
                avg_delay=env.intersection.get_avg_wait_time(),passed=env.intersection.total_passed,
                arrival_trace_hash=arrival.hexdigest(),signal_samples=audit.samples,
                signal_violations=audit.conflicts+audit.clearance_violations,probes=probes,gate=gate,trace=trace),branch_results


def summarize(sources,records):
    counts={parent:sum(s["case"]["parent"]==parent and s["gate"] is not None for s in sources) for parent in PARENTS}
    available=len(sources)==9 and all(count>=2 for count in counts.values())
    by_parent={parent:[f for row in records if row["case"]["parent"]==parent for f in row["futures"]] for parent in PARENTS}
    futures=[f for row in records for f in row["futures"]]
    means=[statistics.mean(f["gain"][i] for f in futures) for i in range(3)] if futures else None
    checks=dict(eligible_sources=available,
        complete_branches=bool(available and len(records)==sum(counts.values()) and all(len(r["futures"])==8 for r in records)),
        mean_delay_gain=bool(means and means[0]>=1.),no_throughput_loss=bool(means and means[1]>=0.),
        endpoint_wait=bool(means and means[2]>=-1.),
        every_parent_nonnegative=all(rows and statistics.mean(f["gain"][0] for f in rows)>=0 for rows in by_parent.values()),
        every_parent_stable_gate=all(any(row["case"]["parent"]==p and sum(f["qualified"] for f in row["futures"])>=6 for row in records) for p in PARENTS),
        harmful_fraction=bool(futures and sum(f["harmful"] for f in futures)<=.25*len(futures)),
        no_signal_violations=all(s["signal_violations"]==0 for s in sources) and all(
            out["signal_violations"]==0 and out["signal_samples"]==400 for f in futures for out in f["outcomes"].values()))
    return dict(source_runs=len(sources),eligible_gates=counts,gate_futures=len(futures),branches=2*len(futures),
                source_replay_runs=len(records),signal_samples=sum(s["signal_samples"] for s in sources)+1200*len(records)+800*len(futures),
                mean_gain=means,qualified=sum(f["qualified"] for f in futures),harmful=sum(f["harmful"] for f in futures),
                per_parent={p:dict(cases=len(rows),mean_gain=[statistics.mean(f["gain"][i] for f in rows) for i in range(3)] if rows else None) for p,rows in by_parent.items()},
                checks=checks,continue_to_scheduler_pilot=all(checks.values()),publication_ready=False,automatic_promotion=False)


def run(output):
    torch.set_num_threads(1)
    if HyperParams().DECISION_DT != 2.: raise ValueError("Audit requires the original two-second decision interval.")
    for path,expected in PARENTS.values():
        if sha(PARENT_ROOT/path)!=expected: raise ValueError("Frozen checkpoint hash mismatch.")
    cases=[dict(parent=p,scenario=load_scenario(s).to_dict(),seed=1310001+i) for p in PARENTS for i,s in enumerate(SCENARIOS)]
    if any(c["scenario"]["split"]!="train" for c in cases): raise ValueError("Training-only diagnostic required.")
    output.mkdir(parents=True,exist_ok=False)
    paths=[p for directory in (ROOT/"research",ROOT/"server/app") for p in sorted(directory.rglob("*.py"))]
    manifest=dict(plan=PLAN,cases=cases,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  python_version=sys.version,torch_version=torch.__version__,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths})
    write(output/"manifest.json",manifest)
    with zipfile.ZipFile(output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths: archive.write(path,str(path.relative_to(ROOT)))
    sources,records,budget,reason=[],[],RunBudget(180),"completed"
    try:
        for case in cases:
            row,_=source(case,budget)
            sources.append(row)
            write(output/f"source_{len(sources):02}.json",row)
            print(f"Scanned {case['parent']} {case['scenario']['scenario_id']}: gate {row['gate']['step'] if row['gate'] else None}",flush=True)
        frozen=[dict(case=s["case"],gate=s["gate"],future_seeds=[future_seed(s["case"],s["gate"]["step"],i) for i in range(8)]) for s in sources if s["gate"]]
        write(output/"frozen_gates.json",frozen)
        coverage=summarize(sources,[])["checks"]["eligible_sources"]
        if coverage:
            for original in sources:
                if original["gate"] is None: continue
                replay,futures=source(original["case"],budget,original["gate"])
                if replay!=original: raise ValueError("Branching changed the source trajectory or scores.")
                records.append(dict(case=original["case"],gate=original["gate"],source_replayed=True,futures=futures))
                write(output/f"branches_{len(records):02}.json",records[-1])
                print(f"Branched {len(records)}/{len(frozen)} frozen gates",flush=True)
        else: reason="insufficient_opportunity_coverage"
    except BudgetExceeded: reason="budget_exceeded"
    report=dict(**summarize(sources,records),complete=reason!="budget_exceeded",stop_reason=reason,elapsed_seconds=budget.elapsed)
    if not report["complete"]: report["continue_to_scheduler_pilot"]=False
    elif reason=="completed" and not report["continue_to_scheduler_pilot"]: report["stop_reason"]="benefit_screen_failed"
    report["output_sha256"]={path.name:sha(path) for path in sorted(output.iterdir()) if path.is_file()}
    write(output/"report.json",report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output",type=Path)
    mode.add_argument("--verify",type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.verify) if args.verify else run(args.output),indent=2))


def verify(output):
    torch.set_num_threads(1)
    manifest=json.loads((output/"manifest.json").read_text())
    report=json.loads((output/"report.json").read_text())
    sources=[json.loads(path.read_text()) for path in sorted(output.glob("source_*.json"))]
    records=[json.loads(path.read_text()) for path in sorted(output.glob("branches_*.json"))]
    if manifest["plan"]!=json.loads(json.dumps(PLAN)) or not report["complete"] or len(sources)!=9:
        raise ValueError("Incomplete panel or protocol mismatch.")
    if manifest["python_version"]!=sys.version or manifest["torch_version"]!=torch.__version__:
        raise ValueError("Historical audit requires its original runtime.")
    if set(report["output_sha256"])!={p.name for p in output.iterdir() if p.is_file() and p.name!="report.json"} or any(sha(output/name)!=expected for name,expected in report["output_sha256"].items()):
        raise ValueError("Recorded output hash/coverage mismatch.")
    if [s["case"] for s in sources]!=manifest["cases"]:
        raise ValueError("Source case coverage/order mismatch.")
    frozen=json.loads((output/"frozen_gates.json").read_text())
    expected=[dict(case=s["case"],gate=s["gate"],future_seeds=[future_seed(s["case"],s["gate"]["step"],i) for i in range(8)]) for s in sources if s["gate"]]
    if frozen!=expected: raise ValueError("Frozen gate or future key mismatch.")
    models={}
    probes_verified=0
    for row in sources:
        if row["checkpoint_sha256"]!=PARENTS[row["case"]["parent"]][1] or row["signal_samples"]!=1200:
            raise ValueError("Source checkpoint or signal coverage mismatch.")
        parent=row["case"]["parent"]
        if parent not in models:
            if sha(PARENT_ROOT/PARENTS[parent][0])!=PARENTS[parent][1]: raise ValueError("Parent file hash mismatch.")
            seed_everything(row["case"]["seed"])
            models[parent]=D3QNController(checkpoint_path=str(PARENT_ROOT/PARENTS[parent][0]))
        for event in row["probes"]:
            mask=np.asarray(event["mask"],dtype=bool)
            scores=score_actions(models[parent].agent.online_net,np.asarray(event["observation"],dtype=np.float32),mask)
            if scores["action"]!=event["fresh_proposal"] or scores["q_values"]!=event["q_values"]:
                raise ValueError("Saved fresh Q proposal does not reproduce.")
            context=ControllerContext(timestep=event["step"],current_phase=event["phase"],time_in_phase=event["phase_age"],
                movement_queues=event["movement_queues"],phase_starvation_times={int(k):v for k,v in event["phase_waits"].items()},valid_action_mask=mask)
            if not due_probe(context,event["deadline"],event["cached_action"]) or SafetyShield().filter_context(scores["action"],context).executed_action!=event["fresh_execution"]:
                raise ValueError("Probe clock or shield execution mismatch.")
            probes_verified+=1
        eligible=[e for e in row["probes"] if e["parent_execution"]==e["phase"] and e["fresh_proposal"]!=e["phase"] and e["fresh_execution"]==e["fresh_proposal"]]
        if row["gate"]!=(eligible[0] if eligible else None): raise ValueError("Not the first eligible gate.")
        if any(not (200<=e["step"]<=600 and e["step"]%5==0 and e["deadline"]>e["step"]) for e in row["probes"]):
            raise ValueError("Probe outside the original hold window.")
    lookup={(s["case"]["parent"],s["case"]["scenario"]["scenario_id"]):s for s in sources}
    seen=set()
    for row in records:
        key=(row["case"]["parent"],row["case"]["scenario"]["scenario_id"])
        if key in seen or key not in lookup or row["gate"]!=lookup[key]["gate"] or row["case"]!=lookup[key]["case"] or not row["source_replayed"]:
            raise ValueError("Branch source/gate replay mismatch.")
        seen.add(key)
        if len(row["futures"])!=8 or {f["replicate"] for f in row["futures"]}!=set(range(8)):
            raise ValueError("Incomplete or duplicate future coverage.")
        for future in row["futures"]:
            if future["future_seed"]!=future_seed(row["case"],row["gate"]["step"],future["replicate"]): raise ValueError("Future RNG key mismatch.")
            base,new=future["outcomes"]["parent"],future["outcomes"]["early"]
            if base["arrival_trace_hash"]!=new["arrival_trace_hash"]: raise ValueError("Unpaired arrivals.")
            gain=[base["incremental_delay_vehicle_seconds"]-new["incremental_delay_vehicle_seconds"],new["vehicles_passed"]-base["vehicles_passed"],base["upstream_max_wait_s"]-new["upstream_max_wait_s"]]
            if future["gain"]!=gain or future["qualified"]!=qualified(gain) or future["harmful"]!=harmful(gain):
                raise ValueError("Branch gain/qualification mismatch.")
    rebuilt=summarize(sources,records)
    if any(report.get(key)!=value for key,value in rebuilt.items()): raise ValueError("Summary does not reconstruct.")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist())!=set(manifest["source_sha256"]): raise ValueError("Incomplete source archive.")
        for name,expected_hash in manifest["source_sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=expected_hash or sha(ROOT/name)!=expected_hash:
                raise ValueError("Historical reports require original archived implementation/runtime.")
    return dict(verified=True,source_runs=9,branches=report["branches"],source_replays_recorded=len(records),
                network_probes_reproduced=probes_verified,
                independently_rerun_trajectories=0,continue_to_scheduler_pilot=report["continue_to_scheduler_pilot"],
                scope="Source/gate/future coverage, paired outcomes, summary and archived/current source reconstruction; no new trajectory rerun.")


if __name__=="__main__": main()
