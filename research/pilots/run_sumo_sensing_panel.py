"""Bounded SUMO count-fault characterization with a mandatory mechanics gate."""
import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_sensing_metrics import summarize
from research.audits.sumo_branch_feasibility import digest, file_hash, network
from research.experiments.sumo_classical_runtime import episode as clean_episode
from research.experiments.sumo_sensing import PLAN, SOURCE_FILES, configuration, episode, physical_view, plans, validate_trace
from research.observation.sumo_sensing import PRESETS
from research.policies.sumo_classical import CONTROLLERS

ROOT = Path(__file__).resolve().parents[2]
# The smoke's independent old-loop anchor is executable study evidence too.
SOURCES = SOURCE_FILES+("research/experiments/sumo_classical_runtime.py",)
SUMO_OPTIONS = ("--step-length",".1","--seed","1350000","--time-to-teleport","-1",
                "--no-step-log","true","--duration-log.disable","true","--xml-validation","never")


def write(path, value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def trace_name(seed, controller, fault, repeat):
    return f"trace_{seed}_{controller}_{fault}_r{repeat}.jsonl.gz"


def read_trace(path):
    with gzip.open(path,"rt") as stream:
        return [json.loads(line) for line in stream]


def save_trace(path, rows):
    trace = []
    with gzip.open(path,"xt") as stream:
        for row in rows:
            stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
            trace.append(row)
    return trace


def runtime():
    versions = {n:importlib.metadata.version(n) for n in ("eclipse-sumo","traci","sumolib")}
    if set(versions.values()) != {"1.24.0"}:
        raise ValueError("Install the pinned SUMO requirements in an isolated environment")
    binaries = {n:shutil.which(n,path=str(Path(sys.executable).parent)) for n in ("sumo","netconvert")}
    if not all(binaries.values()):
        raise ValueError("SUMO launchers missing from this interpreter's bin directory")
    native = {Path(f).name:importlib.metadata.distribution("eclipse-sumo").locate_file(f)
        for f in importlib.metadata.files("eclipse-sumo") if str(f) in ("sumo/bin/sumo","sumo/bin/netconvert")}
    if set(native) != {"sumo","netconvert"}:
        raise ValueError("Pinned SUMO native binaries not found")
    evidence = dict(python_version=sys.version, versions=versions,
        native_binary_sha256={n:file_hash(p) for n,p in native.items()},
        binary_versions={n:subprocess.check_output([p,"--version"],text=True).splitlines()[0] for n,p in binaries.items()})
    return binaries,evidence


def write_csv(path, rows):
    with path.open("x",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def csv_matches(path, rows):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        actual,fields = list(reader),reader.fieldnames
    return fields == list(rows[0]) and actual == [{k:"" if v is None else str(v) for k,v in row.items()} for row in rows]


def case_table(rows):
    return [dict(seed=r["seed"], family=r["family"],controller=r["controller"],fault=r["fault"], repeat=r["repeat"],
        **{k:v for k,v in r["metrics"].items() if k != "sensing"}, **r["metrics"]["sensing"]) for r in rows]


def run(output, smoke=False, mechanics=None):
    if output.exists():
        raise FileExistsError("Use a new directory; preserve completed and partial evidence")
    if subprocess.check_output(["git","status","--porcelain","--",*SOURCES],cwd=ROOT,text=True).strip():
        raise ValueError("Commit the executable protocol before collection")
    binaries, environment = runtime()
    mechanics_record = None
    if not smoke:
        if mechanics is None:
            raise ValueError("Full collection requires --mechanics pointing to a verified smoke")
        checked = verify(mechanics)
        proof = json.loads((mechanics/"manifest.json").read_text())
        if not checked["smoke"] or proof["runtime"] != environment:
            raise ValueError("Mechanics proof must be smoke under this runtime")
        if proof["source_hashes"] != {n:file_hash(ROOT/n) for n in SOURCES}:
            raise ValueError("Executable sources changed after mechanics")
        mechanics_record = dict(directory=str(mechanics.resolve()),report_sha256=file_hash(mechanics/"report.json"))
    cfg,frozen = configuration(smoke),plans(smoke)
    output.mkdir(parents=True)
    manifest = dict(plan=PLAN,configuration=cfg, runtime=environment,
        git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        source_hashes={n:file_hash(ROOT/n) for n in SOURCES},mechanics=mechanics_record)
    write(output/"manifest.json",manifest)
    write(output/"frozen_plans.json",frozen)
    with zipfile.ZipFile(output/"source_snapshot.zip","x") as archive:
        for name in SOURCES:
            archive.write(ROOT/name,name)
    start,conn,rows,active_job = time.monotonic(),None,[],None
    def budget():
        if time.monotonic()-start > cfg["cap_seconds"]:
            raise TimeoutError("Frozen sensing collection cap exceeded")
    report = dict(complete=False,scientific_panel_complete=False,smoke=smoke,policy_promoted=False,publication_ready=False)
    try:
        import traci
        budget()
        network(output,binaries["netconvert"])
        command = [binaries["sumo"],"-n",str((output/"network.net.xml").resolve()),"-r",str((output/"routes.rou.xml").resolve()),*SUMO_OPTIONS]
        write(output/"sumo_command.json",command)
        traci.start(command,label="sensing_panel",stdout=subprocess.DEVNULL)
        conn = traci.getConnection("sensing_panel")
        axes = [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0,0,1,1]:
            raise ValueError("Unexpected protected-movement mapping")
        anchor = None
        if smoke:
            conn.load(command[1:])
            anchor = save_trace(output/"clean_anchor.jsonl.gz",clean_episode(conn,axes,frozen[0],"max_pressure",budget))
        for index,plan in enumerate(frozen,1):
            fixed_hash = None
            for controller in CONTROLLERS:
                for fault in PRESETS:
                    repeated = None
                    for repeat in range(cfg["repeats"]):
                        budget()
                        active_job = dict(seed=plan["seed"],controller=controller,fault=fault.name,repeat=repeat)
                        conn.load(command[1:])
                        name = trace_name(plan["seed"],controller,fault.name,repeat)
                        trace = save_trace(output/name,episode(conn,axes,plan,controller,fault,budget))
                        metrics = validate_trace(trace,plan,controller,fault,axes)
                        semantic = digest(trace)
                        if repeated is not None and repeated != semantic:
                            raise ValueError("Deterministic sensing repeat differs")
                        repeated = semantic
                        if controller == "fixed":
                            physical = digest(physical_view(trace))
                            if fixed_hash is not None and fixed_hash != physical:
                                raise ValueError("Fixed traffic depends on sensing faults")
                            fixed_hash = physical
                        if smoke and controller == "max_pressure" and fault.name == "clean":
                            if [{k:v for k,v in row.items() if k != "sensing"} for row in trace] != anchor:
                                raise ValueError("Clean runtime anchor differs from historical loop")
                        rows.append(dict(**active_job,family=plan["family"],metrics=metrics,trace=name,
                            semantic_trace_sha256=semantic,requested_arrival_sha256=digest(plan["schedule"])))
                        with (output/"runs.jsonl").open("a") as stream:
                            stream.write(json.dumps(rows[-1],allow_nan=False)+"\n")
            print(f"Completed sensing case {index}/{len(frozen)} ({plan['family']}, seed {plan['seed']})",flush=True)
        summary = summarize(rows,frozen,cfg["repeats"])
        write_csv(output/"cases.csv",case_table(rows))
        write_csv(output/"aggregate.csv",summary["aggregate"])
        write_csv(output/"paired_contrasts.csv",summary["paired_contrasts"])
        report.update(complete=True,scientific_panel_complete=not smoke,cases=len(frozen),runs=len(rows),
            signal_samples=sum(r["metrics"]["signal_samples"] for r in rows),
            mechanics_anchor_runs=int(smoke),mechanics_anchor_signal_samples=cfg["steps"] if smoke else 0,
            fixed_invariance_verified=True,repeat_mechanics_verified=smoke,clean_anchor_verified=smoke,summary=summary)
    except (Exception,KeyboardInterrupt) as exc:
        report.update(completed_runs=len(rows),active_job=active_job,error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        try:
            if conn is not None:
                conn.close()
        finally:
            report["elapsed_seconds"] = time.monotonic()-start
            report["output_hashes"] = {p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            write(output/"report.json",report)
    return {k:v for k,v in report.items() if k not in ("summary","output_hashes")}


def verify(directory):
    report = json.loads((directory/"report.json").read_text())
    manifest = json.loads((directory/"manifest.json").read_text())
    smoke = report["smoke"]
    cfg,frozen = configuration(smoke),plans(smoke)
    if (type(smoke) is not bool or not report["complete"] or report["scientific_panel_complete"] != (not smoke)
            or report["policy_promoted"] or report["publication_ready"]
            or manifest["configuration"] != json.loads(json.dumps(cfg)) or manifest["plan"] != PLAN):
        raise ValueError("Incomplete or relabelled sensing study")
    environment = manifest["runtime"]
    def hex_digest(value, length):
        return isinstance(value,str) and len(value) == length and all(c in "0123456789abcdef" for c in value)
    if (set(environment) != {"python_version","versions","native_binary_sha256","binary_versions"}
            or not isinstance(environment["python_version"],str) or not environment["python_version"]
            or environment["versions"] != dict.fromkeys(("eclipse-sumo","traci","sumolib"),"1.24.0")
            or set(environment["native_binary_sha256"]) != {"sumo","netconvert"}
            or any(not hex_digest(h,64) for h in environment["native_binary_sha256"].values())
            or set(environment["binary_versions"]) != {"sumo","netconvert"}
            or any(not isinstance(v,str) or "Version 1.24.0" not in v for v in environment["binary_versions"].values())
            or not hex_digest(manifest.get("git_commit"),40)):
        raise ValueError("Missing or changed runtime/revision provenance")
    files = {p.name for p in directory.iterdir() if p.is_file() and p.name != "report.json"}
    expected = {"manifest.json","frozen_plans.json","source_snapshot.zip","sumo_command.json","runs.jsonl",
        "nodes.nod.xml","edges.edg.xml","connections.con.xml","network.net.xml","routes.rou.xml",
        "cases.csv","aggregate.csv","paired_contrasts.csv"}
    expected |= {trace_name(p["seed"],c,f.name,r) for p in frozen for c in CONTROLLERS for f in PRESETS for r in range(cfg["repeats"])}
    if smoke:
        expected.add("clean_anchor.jsonl.gz")
    if files != expected or set(report["output_hashes"]) != expected:
        raise ValueError("Changed output hash coverage")
    if any(file_hash(directory/n) != h for n,h in report["output_hashes"].items()):
        raise ValueError("Changed sensing output")
    if set(manifest["source_hashes"]) != set(SOURCES):
        raise ValueError("Missing executable source coverage")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if len(archive.namelist()) != len(SOURCES) or set(archive.namelist()) != set(SOURCES):
            raise ValueError("Changed source archive coverage")
        if any(hashlib.sha256(archive.read(n)).hexdigest() != h for n,h in manifest["source_hashes"].items()):
            raise ValueError("Changed archived source")
    if any(file_hash(ROOT/n) != h for n,h in manifest["source_hashes"].items()):
        raise ValueError("Historical replay requires the archived executable sources")
    command = json.loads((directory/"sumo_command.json").read_text())
    if (len(command) != 5+len(SUMO_OPTIONS) or command[1] != "-n" or command[3] != "-r"
            or Path(command[2]).name != "network.net.xml" or Path(command[4]).name != "routes.rou.xml"
            or command[5:] != list(SUMO_OPTIONS)):
        raise ValueError("Changed SUMO stepping command")
    if json.loads((directory/"frozen_plans.json").read_text()) != frozen:
        raise ValueError("Changed requested schedules")
    if not smoke:
        proof = manifest["mechanics"]
        if proof is None or file_hash(Path(proof["directory"])/"report.json") != proof["report_sha256"]:
            raise ValueError("Missing or changed mechanics basis")
        checked = verify(Path(proof["directory"]))
        old = json.loads((Path(proof["directory"])/"manifest.json").read_text())
        if not checked["smoke"] or old["source_hashes"] != manifest["source_hashes"] or old["runtime"] != manifest["runtime"]:
            raise ValueError("Mechanics basis differs from full study")
    links = [n for n in ET.parse(directory/"network.net.xml").getroot().findall("connection") if n.get("tl") == "c"]
    axes = [int(n.get("from").split("_")[0] in "ew") for n in sorted(links,key=lambda n:int(n.get("linkIndex")))]
    if sorted(axes) != [0,0,1,1]:
        raise ValueError("Unexpected signal mapping")
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    summary = summarize(rows,frozen,cfg["repeats"])
    if summary != report["summary"]:
        raise ValueError("Sensing contrast/summary mismatch")
    lookup,repeat_hashes,fixed_hashes = {p["seed"]:p for p in frozen},{},{}
    anchor = read_trace(directory/"clean_anchor.jsonl.gz") if smoke else None
    for row in rows:
        plan = lookup[row["seed"]]
        name = trace_name(row["seed"],row["controller"],row["fault"],row["repeat"])
        if row["family"] != plan["family"] or row["trace"] != name or row["requested_arrival_sha256"] != digest(plan["schedule"]):
            raise ValueError("Changed run identity or arrival pairing")
        trace = read_trace(directory/name)
        fault = next(f for f in PRESETS if f.name == row["fault"])
        if digest(trace) != row["semantic_trace_sha256"] or validate_trace(trace,plan,row["controller"],fault,axes) != row["metrics"]:
            raise ValueError("Sensing trace/metrics do not reconstruct")
        key = row["seed"],row["controller"],row["fault"]
        if repeat_hashes.setdefault(key,digest(trace)) != digest(trace):
            raise ValueError("Sensing repeat mismatch")
        if row["controller"] == "fixed":
            physical = digest(physical_view(trace))
            if fixed_hashes.setdefault(row["seed"],physical) != physical:
                raise ValueError("Fixed sensing negative control failed")
        if smoke and row["controller"] == "max_pressure" and row["fault"] == "clean":
            if [{k:v for k,v in r.items() if k != "sensing"} for r in trace] != anchor:
                raise ValueError("Clean historical anchor failed")
    if (not csv_matches(directory/"cases.csv",case_table(rows)) or not csv_matches(directory/"aggregate.csv",summary["aggregate"])
            or not csv_matches(directory/"paired_contrasts.csv",summary["paired_contrasts"])):
        raise ValueError("Sensing CSV reconstruction failed")
    if (report["runs"] != len(rows) or report["cases"] != len(frozen)
            or report["signal_samples"] != sum(r["metrics"]["signal_samples"] for r in rows)
            or report["mechanics_anchor_runs"] != int(smoke) or report["mechanics_anchor_signal_samples"] != (cfg["steps"] if smoke else 0)
            or report["repeat_mechanics_verified"] != smoke or report["clean_anchor_verified"] != smoke or not report["fixed_invariance_verified"]):
        raise ValueError("Changed sensing coverage/mechanics flags")
    return dict(verified=True,smoke=smoke,scientific_panel_complete=not smoke,runs=len(rows),
        signal_samples=report["signal_samples"],mechanics_anchor_signal_samples=report["mechanics_anchor_signal_samples"],
        packets_proposals_and_lamps_reconstructed=True,fixed_fault_invariance=True,independently_rerun_trajectories=0,publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output",type=Path)
    mode.add_argument("--verify",type=Path)
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--mechanics",type=Path)
    args = parser.parse_args()
    result = verify(args.verify) if args.verify else run(args.output,args.smoke,args.mechanics)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
