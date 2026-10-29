"""Supervised sensing prerequisite, then conditional matched control evaluation."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.observation.count_restoration import (
    CountRestorer, PacketHistory, RestorationInjector, EMA_ALPHAS, VERSION, counts, predict, update_ema,
)
from research.pilots.run_switch_margin_pilot import PARENTS, PARENT_ROOT, ROOT, sha, write
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import load_split, VALIDATION_FAULTS, RunBudget, BudgetExceeded
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.simulation.benchmark_harness import seed_everything

SEEDS=(101,202,303)
PLAN=dict(schema_version="count_restoration_pilot_v1",max_wall_seconds=600,horizon_ticks=1200,
    hypothesis="Causal supervised count restoration can reduce sensing error and improve frozen D3QN control; matched Max-Pressure receives identical restoration.",
    fitting="Six train templates, two traffic realizations/roles each, clean and mixed: 24 raw-policy sources. Role zero shielded pressure, role one round-robin parent D3QN.",
    fit_seed_rule="1321001 + 100*template_index + role_index",
    probe="Six train templates, new seed 1322001 + template_index, alternating pressure/parent role, clean and mixed: 12 sources collected after models freeze.",
    features="Shared per-movement current/lag-1/5/10 counts, one-second mean/max/min, green service flag, signal age, delivered age/drop, lag availability, turn one-hot. No profile ID, clean counts, future packet or simulator state at inference.",
    targets="Current pre-corruption count labels every five ticks, available only in supervised fit and scoring.",
    model="17-32-32-1 residual MLP; zero final layer starts at identity, nonnegative outputs bounded by observed one-second maximum +2; all-zero history remains zero; round before control.",
    training=dict(seeds=SEEDS,updates=500,batch_size=1024,optimizer="Adam",lr=.001,loss="smooth_l1_count_units",gradient_clip=5.),
    ema_alphas=EMA_ALPHAS,ema_selection="Minimum fitting count MAE on identical labeled frames; ties prefer larger alpha. Frozen before probe.",
    reconstruction_screen="All three models: >=10% overall and >=5% positive-truth count MAE reduction vs raw; >=5% overall reduction vs fitted EMA; clean MAE <=0.05 counts/movement. Complete sources, no measured signal violations.",
    control="Three existing validation templates, one new realization each (1323001 + template_index), clean and mixed: six cases. Each parent: raw, fitted EMA, restored, full raw UQ. Pressure: raw shielded, EMA shielded, restoration per seed shielded, bare raw. 108 runs only after reconstruction passes.",
    control_screen="Mixed: >=3% delay gain vs raw/EMA D3QN, no aggregate p95/throughput loss, no parent >1% worse than raw. Clean: <=1% mean/p95 loss and no throughput loss vs raw. All cases: >=2% delay gain and no p95/throughput loss vs raw/EMA/restored/bare pressure; complete paired arrivals, no measured violations.",
    scope="New supervised restoration models, frozen D3QN weights, known synthetic faults/templates; not new Q training, independent final testing, camera validation or a novelty claim.",
    related_work="https://www.ijcai.org/proceedings/2023/0251.pdf; https://arxiv.org/abs/2410.22938 (missing-data TSC precedents; not reproduced algorithms)",
    automatic_promotion=False,publication_ready=False)


def raw_controller(actor,uq=False,bare=False):
    if actor=="pressure": base=MaxPressureController()
    elif uq: return FlowSyncUQController(checkpoint_path=str(PARENT_ROOT/PARENTS[actor][0]))
    else: base=D3QNController(checkpoint_path=str(PARENT_ROOT/PARENTS[actor][0]))
    return base if bare else ShieldedController(base)


def dataset_cases(role):
    result=[]
    for i,scenario in enumerate(load_split("train")):
        for j in (range(2) if role=="fit" else range(1)):
            actor="pressure" if (j==0 if role=="fit" else i%2==0) else str(SEEDS[i%3])
            seed=1321001+100*i+j if role=="fit" else 1322001+i
            for fault in VALIDATION_FAULTS:
                result.append(dict(case_id=f"{role}_{scenario.scenario_id}_{seed}_{fault.name}",scenario=scenario.to_dict(),
                                   actor=actor,seed=seed,fault=asdict(fault)))
    return result


def collect(cases,budget,output):
    x,y,raw,ema,case_ids=[],[],[],[],[]
    summaries=[]
    chunk_dir=output.parent/f"{output.stem}_sources"
    chunk_dir.mkdir(exist_ok=False)
    for index,case in enumerate(cases):
        start=len(x)
        seed_everything(case["seed"])
        scenario=ScenarioConfig.from_dict(case["scenario"])
        env,profile=build_environment(scenario)
        obs,_=env.reset(seed=case["seed"])
        sensor,history=ObservedState(),PacketHistory()
        injector=PerceptionFaultInjector(FaultProfile(**case["fault"]),seed=case["seed"]+90000)
        controller=raw_controller(case["actor"])
        controller.reset(case["seed"])
        audit=SignalAudit()
        ema_state=None
        for step in range(1200):
            budget.check("restoration dataset collection")
            apply_scenario_step(env.intersection,profile,scenario.demand_profile,step)
            delivered,context=sensor.build(env,obs,step,injector)
            features=history.update(delivered,context)
            received=counts(delivered)
            if ema_state is None: ema_state=np.tile(received,(len(EMA_ALPHAS),1))
            else:
                alpha=np.asarray(EMA_ALPHAS,dtype=np.float32)[:,None]
                ema_state=update_ema(ema_state,received,alpha)
            if step%5==0:
                x.append(features); y.append(counts(obs));raw.append(received);ema.append(np.rint(ema_state));case_ids.append(index)
            signal=env.intersection.signal
            before=(signal.current_phase,signal.color.name,signal.time_in_phase)
            obs,_,_,_,_=env.step(controller.act(delivered,context))
            audit.observe(before,signal)
        chunk=chunk_dir/f"{index:03}.npz"
        np.savez_compressed(chunk,x=np.asarray(x[start:]),y=np.asarray(y[start:]),raw=np.asarray(raw[start:]),ema=np.asarray(ema[start:]))
        summary=dict(case=case,signal_samples=audit.samples,signal_violations=audit.conflicts+audit.clearance_violations,
                     avg_delay=env.intersection.get_avg_wait_time(),passed=env.intersection.total_passed,
                     checkpoint_sha256=controller.get_diagnostics().get("checkpoint_hash"),data_sha256=sha(chunk))
        summaries.append(summary)
        write(chunk.with_suffix(".json"),summary)
        print(f"Collected {case['case_id']}",flush=True)
    data=dict(x=np.asarray(x,dtype=np.float32),y=np.asarray(y,dtype=np.float32),raw=np.asarray(raw,dtype=np.float32),
              ema=np.asarray(ema,dtype=np.float32),case_ids=np.asarray(case_ids,dtype=np.int32))
    np.savez_compressed(output,**data)
    write(output.with_suffix(".json"),summaries)
    return data,summaries


def fit_model(data,seed,budget):
    x=torch.as_tensor(data["x"].reshape(-1,17))
    y=torch.as_tensor(data["y"].reshape(-1))
    torch.manual_seed(seed)
    rng=np.random.default_rng(seed)
    model=CountRestorer()
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    curve=[]
    for step in range(500):
        budget.check("supervised restoration updates")
        indices=torch.as_tensor(rng.integers(len(y),size=1024))
        loss=torch.nn.functional.smooth_l1_loss(model(x[indices]),y[indices])
        optimizer.zero_grad();loss.backward()
        norm=torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
        if not torch.isfinite(loss) or not torch.isfinite(norm): raise ValueError("Nonfinite supervised update.")
        optimizer.step()
        if step%50==0 or step==499: curve.append(dict(update=step+1,loss=float(loss.detach()),gradient_norm=float(norm)))
    model.eval()
    return model,curve


def train(data,output,budget):
    for seed in SEEDS:
        model,curve=fit_model(data,seed,budget)
        torch.save(dict(schema_version=VERSION,state_dict=model.state_dict(),training_seed=seed,updates=500,
                        fit_data_sha256=sha(output/"fit.npz"),curve=curve),output/f"restorer_{seed}.pt")
    errors=np.abs(data["ema"]-data["y"][:,None,:]).mean(axis=(0,2))
    choice=min(range(4),key=lambda i:(float(errors[i]),-EMA_ALPHAS[i]))
    frozen=dict(ema_alpha=EMA_ALPHAS[choice],ema_fit_mae=errors.tolist(),
                models={str(seed):sha(output/f"restorer_{seed}.pt") for seed in SEEDS},fit_data_sha256=sha(output/"fit.npz"))
    write(output/"frozen_models.json",frozen)
    return frozen


def count_metrics(prediction,data,cases):
    error=np.abs(prediction-data["y"])
    positive=data["y"]>0
    clean=np.asarray([cases[int(i)]["fault"]["name"]=="clean" for i in data["case_ids"]])
    return dict(mae=float(error.mean()),positive_mae=float(error[positive].mean()),clean_mae=float(error[clean].mean()))


def reconstruction(data,cases,output,frozen):
    alpha_index=EMA_ALPHAS.index(frozen["ema_alpha"])
    raw=count_metrics(data["raw"],data,cases)
    ema=count_metrics(data["ema"][:,alpha_index,:],data,cases)
    metrics={"raw":raw,"ema":ema}
    checks={}
    for seed in SEEDS:
        payload=torch.load(output/f"restorer_{seed}.pt",map_location="cpu",weights_only=True)
        model=CountRestorer();model.load_state_dict(payload["state_dict"]);model.eval()
        prediction=predict(model,data["x"])
        measured=count_metrics(prediction,data,cases)
        metrics[str(seed)]=measured
        checks[str(seed)]=dict(raw_mae=raw["mae"]>0 and measured["mae"]<=.9*raw["mae"],
                               positive_mae=raw["positive_mae"]>0 and measured["positive_mae"]<=.95*raw["positive_mae"],
                               ema_mae=ema["mae"]>0 and measured["mae"]<=.95*ema["mae"],clean_mae=measured["clean_mae"]<=.05)
    return dict(metrics=metrics,checks=checks,continue_to_control=all(all(row.values()) for row in checks.values()))


def control_cases():
    return [dict(case_id=f"{scenario.scenario_id}_{1323001+i}_{fault.name}",scenario=scenario.to_dict(),seed=1323001+i,fault=asdict(fault))
            for i,scenario in enumerate(load_split("validation")) for fault in VALIDATION_FAULTS]


def control_jobs():
    return [(str(seed),arm) for seed in SEEDS for arm in ("raw","ema","restored","uq")]+[
        ("pressure",arm) for arm in ("raw","ema","restored_101","restored_202","restored_303","bare")]


def means(rows):
    return {key:float(np.mean([r[key] for r in rows])) for key in ("delay","p95","passed")}


def control_summary(rows):
    def group(actor,arm,fault=None):
        return [r for r in rows if (r["actor"]!="pressure" if actor=="d3qn" else r["actor"]==actor)
                and (r["arm"].startswith("restored_") if arm=="restored_pressure" else r["arm"]==arm)
                and (fault is None or r["fault"]==fault)]
    checks={}
    restored=means(group("d3qn","restored","validation_mixed"))
    for reference in ("raw","ema"):
        base=means(group("d3qn",reference,"validation_mixed"))
        checks[f"mixed_delay_vs_{reference}"]=restored["delay"]<=.97*base["delay"]
        checks[f"mixed_p95_vs_{reference}"]=restored["p95"]<=base["p95"]
        checks[f"mixed_throughput_vs_{reference}"]=restored["passed"]>=base["passed"]
    checks["every_parent_mixed_delay"]=all(means(group(str(s),"restored","validation_mixed"))["delay"]<=1.01*means(group(str(s),"raw","validation_mixed"))["delay"] for s in SEEDS)
    clean,raw=means(group("d3qn","restored","clean")),means(group("d3qn","raw","clean"))
    checks.update(clean_delay=clean["delay"]<=1.01*raw["delay"],clean_p95=clean["p95"]<=1.01*raw["p95"],clean_throughput=clean["passed"]>=raw["passed"])
    overall=means(group("d3qn","restored"))
    for arm in ("raw","ema","restored_pressure","bare"):
        base=means(group("pressure",arm))
        checks[f"delay_vs_pressure_{arm}"]=overall["delay"]<=.98*base["delay"]
        checks[f"p95_vs_pressure_{arm}"]=overall["p95"]<=base["p95"]
        checks[f"throughput_vs_pressure_{arm}"]=overall["passed"]>=base["passed"]
    checks["no_violations"]=all(r["violations"]==0 for r in rows)
    return dict(means={f"{actor}_{arm}":means(group(actor,arm)) for actor,arms in (("d3qn",("raw","ema","restored","uq")),("pressure",("raw","ema","restored_pressure","bare"))) for arm in arms},
                checks=checks,continue_to_expanded_validation=all(checks.values()))


def run(output):
    torch.set_num_threads(1)
    for path,expected in PARENTS.values():
        if sha(PARENT_ROOT/path)!=expected: raise ValueError("Frozen D3QN parent changed.")
    fit_cases,probe_cases,dev_cases=dataset_cases("fit"),dataset_cases("probe"),control_cases()
    if len(fit_cases)!=24 or len(probe_cases)!=12 or len(dev_cases)!=6: raise ValueError("Unexpected panel.")
    output.mkdir(parents=True,exist_ok=False)
    (output/"raw").mkdir()
    paths=[p for base in (ROOT/"research",ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    write(output/"manifest.json",dict(plan=PLAN,fit_cases=fit_cases,probe_cases=probe_cases,control_cases=dev_cases,jobs=control_jobs(),
        git_commit=ExperimentRunner.get_git_commit(),python_version=sys.version,torch_version=torch.__version__,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}))
    with zipfile.ZipFile(output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths: archive.write(path,str(path.relative_to(ROOT)))
    budget=RunBudget(600)
    restoration_report=control_report=frozen=None
    rows=[]
    reason="completed"
    try:
        fit,fit_summary=collect(fit_cases,budget,output/"fit.npz")
        frozen=train(fit,output,budget)
        probe,probe_summary=collect(probe_cases,budget,output/"probe.npz")
        restoration_report=reconstruction(probe,probe_cases,output,frozen)
        restoration_report["checks"]["source_violations"]={"none":all(s["signal_violations"]==0 and s["signal_samples"]==1200 for s in fit_summary+probe_summary)}
        restoration_report["continue_to_control"] &= restoration_report["checks"]["source_violations"]["none"]
        write(output/"reconstruction.json",restoration_report)
        if restoration_report["continue_to_control"]:
            runner=ExperimentRunner()
            for case in dev_cases:
                for actor,arm in control_jobs():
                    budget.check("matched restoration control")
                    seed_everything(case["seed"])
                    fault=FaultProfile(**case["fault"])
                    if arm=="ema": injector=RestorationInjector(fault,case["seed"]+90000,alpha=frozen["ema_alpha"])
                    elif arm.startswith("restored"):
                        model_seed=actor if actor!="pressure" else arm.split("_")[1]
                        injector=RestorationInjector(fault,case["seed"]+90000,model_path=output/f"restorer_{model_seed}.pt")
                    else: injector=PerceptionFaultInjector(fault,seed=case["seed"]+90000)
                    result=runner.run(raw_controller(actor,uq=arm=="uq",bare=arm=="bare"),ScenarioConfig.from_dict(case["scenario"]),case["seed"],
                                      fault_injector=injector,record_trajectory=True)
                    target=output/"raw"/f"{len(rows):04}.json.gz"
                    with gzip.open(target,"wt") as raw: json.dump(dict(case=case,result=result.to_dict()),raw,allow_nan=False)
                    row=dict(actor=actor,arm=arm,case_id=case["case_id"],fault=fault.name,delay=result.avg_delay,p95=result.p95_delay,
                        passed=result.total_vehicles_passed,violations=result.executed_conflict_violations+result.executed_clearance_violations,
                        samples=result.safety_samples,arrival_trace_hash=result.arrival_trace_hash,checkpoint_hash=result.checkpoint_hash,
                        raw_file=str(target.relative_to(output)),raw_sha256=sha(target))
                    rows.append(row)
                    with (output/"control.jsonl").open("a") as stream: stream.write(json.dumps(row)+"\n")
                print(f"Control case complete: {case['case_id']}",flush=True)
            control_report=control_summary(rows)
            if not control_report["continue_to_expanded_validation"]: reason="control_screen_failed"
        else: reason="reconstruction_prerequisite_failed"
    except BudgetExceeded: reason="budget_exceeded"
    report=dict(complete=reason!="budget_exceeded",stop_reason=reason,reconstruction=restoration_report,control=control_report,
                control_runs=len(rows),elapsed_seconds=budget.elapsed,publication_ready=False,automatic_promotion=False,
                continue_to_expanded_validation=bool(control_report and control_report["continue_to_expanded_validation"] and reason!="budget_exceeded"))
    report["output_sha256"]={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
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
    if not report["complete"] or manifest["plan"]!=json.loads(json.dumps(PLAN)):
        raise ValueError("Incomplete experiment or changed protocol.")
    if manifest["python_version"]!=sys.version or manifest["torch_version"]!=torch.__version__:
        raise ValueError("Historical verification requires original runtime.")
    files={str(p.relative_to(output)) for p in output.rglob("*") if p.is_file() and p.name!="report.json"}
    if files!=set(report["output_sha256"]) or any(sha(output/name)!=expected for name,expected in report["output_sha256"].items()):
        raise ValueError("Output hash or file coverage mismatch.")
    with zipfile.ZipFile(output/"source_snapshot.zip") as archive:
        if set(archive.namelist())!=set(manifest["source_sha256"]): raise ValueError("Incomplete archived sources.")
        for name,expected in manifest["source_sha256"].items():
            if sha(ROOT/name)!=expected or hashlib.sha256(archive.read(name)).hexdigest()!=expected:
                raise ValueError("Historical verification requires archived implementation.")
    for path,expected in PARENTS.values():
        if sha(PARENT_ROOT/path)!=expected: raise ValueError("Parent checkpoint changed.")
    data={}
    source_summaries=[]
    for role,n in (("fit",24),("probe",12)):
        cases=manifest[f"{role}_cases"]
        if len(cases)!=n or cases!=dataset_cases(role): raise ValueError("Dataset case mismatch.")
        loaded=dict(np.load(output/f"{role}.npz",allow_pickle=False))
        if loaded["x"].shape!=(n*240,12,17) or loaded["y"].shape!=(n*240,12): raise ValueError("Incomplete labeled frames.")
        summaries=json.loads((output/f"{role}.json").read_text())
        if len(summaries)!=n: raise ValueError("Source coverage mismatch.")
        source_summaries+=summaries
        for index,(case,summary) in enumerate(zip(cases,summaries)):
            chunk=output/f"{role}_sources"/f"{index:03}.npz"
            if summary["case"]!=case or summary["signal_samples"]!=1200 or summary["data_sha256"]!=sha(chunk):
                raise ValueError("Source case/sample/hash mismatch.")
            if case["actor"]!="pressure" and summary["checkpoint_sha256"]!=PARENTS[case["actor"]][1]: raise ValueError("Source actor checkpoint mismatch.")
            part=dict(np.load(chunk,allow_pickle=False))
            for key in ("x","y","raw","ema"):
                if not np.array_equal(loaded[key][loaded["case_ids"]==index],part[key]): raise ValueError("Dataset chunk reconstruction mismatch.")
        data[role]=loaded
    frozen=json.loads((output/"frozen_models.json").read_text())
    errors=np.abs(data["fit"]["ema"]-data["fit"]["y"][:,None,:]).mean(axis=(0,2))
    selected=min(range(4),key=lambda i:(float(errors[i]),-EMA_ALPHAS[i]))
    if frozen["ema_alpha"]!=EMA_ALPHAS[selected] or frozen["ema_fit_mae"]!=errors.tolist(): raise ValueError("EMA selection changed.")
    for seed in SEEDS:
        path=output/f"restorer_{seed}.pt"
        if sha(path)!=frozen["models"][str(seed)]: raise ValueError("Restorer checkpoint hash mismatch.")
        payload=torch.load(path,map_location="cpu",weights_only=True)
        if payload["schema_version"]!=VERSION or payload["updates"]!=500 or payload["fit_data_sha256"]!=sha(output/"fit.npz"):
            raise ValueError("Restorer training provenance mismatch.")
        model,curve=fit_model(data["fit"],seed,RunBudget(60))
        if curve!=payload["curve"] or any(not torch.equal(value,payload["state_dict"][key]) for key,value in model.state_dict().items()):
            raise ValueError("Supervised model refit does not reproduce.")
    reconstruction_report=reconstruction(data["probe"],manifest["probe_cases"],output,frozen)
    reconstruction_report["checks"]["source_violations"]={"none":all(s["signal_violations"]==0 and s["signal_samples"]==1200 for s in source_summaries)}
    reconstruction_report["continue_to_control"] &= reconstruction_report["checks"]["source_violations"]["none"]
    if reconstruction_report!=report["reconstruction"] or reconstruction_report!=json.loads((output/"reconstruction.json").read_text()):
        raise ValueError("Reconstruction prerequisite changed.")
    rows=[json.loads(line) for line in (output/"control.jsonl").read_text().splitlines()] if (output/"control.jsonl").exists() else []
    if reconstruction_report["continue_to_control"]:
        expected={(c["case_id"],actor,arm) for c in manifest["control_cases"] for actor,arm in control_jobs()}
        if len(rows)!=len(expected) or {(r["case_id"],r["actor"],r["arm"]) for r in rows}!=expected: raise ValueError("Control coverage mismatch.")
        if report["control"]!=control_summary(rows): raise ValueError("Control summary changed.")
        arrivals={}
        for row in rows:
            with gzip.open(output/row["raw_file"],"rt") as stream: raw=json.load(stream)
            result=raw["result"]
            values=dict(delay=result["avg_delay"],p95=result["p95_delay"],passed=result["total_vehicles_passed"],
                samples=result["safety_samples"],arrival_trace_hash=result["arrival_trace_hash"],checkpoint_hash=result["checkpoint_hash"],
                violations=result["executed_conflict_violations"]+result["executed_clearance_violations"])
            if any(row[key]!=value for key,value in values.items()) or row["samples"]!=1200 or sha(output/row["raw_file"])!=row["raw_sha256"]:
                raise ValueError("Raw control results do not match.")
            if row["actor"]!="pressure" and row["checkpoint_hash"]!=PARENTS[row["actor"]][1]: raise ValueError("Evaluated D3QN hash mismatch.")
            diagnostics=result["fault_diagnostics"]
            if row["arm"].startswith("restored"):
                seed=row["actor"] if row["actor"]!="pressure" else row["arm"].split("_")[1]
                if diagnostics["restoration_sha256"]!=frozen["models"][seed]: raise ValueError("Restoration model mismatch.")
            if row["arm"]=="ema" and diagnostics["ema_alpha"]!=frozen["ema_alpha"]: raise ValueError("EMA setting mismatch.")
            arrivals.setdefault(row["case_id"],set()).add(row["arrival_trace_hash"])
        if any(len(value)!=1 for value in arrivals.values()): raise ValueError("Unpaired control arrivals.")
    elif rows or report["control"] is not None or report["stop_reason"]!="reconstruction_prerequisite_failed":
        raise ValueError("Control stage proceeded despite failed prerequisite.")
    if report["control_runs"]!=len(rows) or report["continue_to_expanded_validation"]!=bool(report["control"] and report["control"]["continue_to_expanded_validation"]):
        raise ValueError("Incorrect continuation flags.")
    return dict(verified=True,fit_sources=24,probe_sources=12,restoration_models_refitted=3,control_runs=len(rows),
                independently_rerun_traffic_trajectories=0,continue_to_expanded_validation=report["continue_to_expanded_validation"],
                scope="Raw/source/output hashes, dataset reconstruction, exact supervised refits, scoring and matched control summaries. No new traffic rerun.")


if __name__=="__main__": main()
