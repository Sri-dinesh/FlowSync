"""Checkpointed runner for new SUMO studies; historical collectors stay frozen.

A study supplies SOURCES, protocol/configuration/plans/jobs, episode,
measurements and analyze. Physical stepping and persistence primitives are
reused from the archived switching collector without rebinding its globals.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from research.pilots import run_sumo_switching_panel as base

ROOT = base.ROOT


class Panel:
    def __init__(self, study):
        self.study = study

    def prepare(self, output, smoke, mechanics, binaries, environment):
        base.fresh_output(output)
        proof, old = None, None
        if not smoke:
            if mechanics is None or not self.verify(mechanics)["smoke"]:
                raise ValueError("Full study requires a complete verified mechanics smoke")
            old = json.loads((mechanics/"manifest.json").read_text())
            if old["runtime"] != environment or old["source_sha256"] != {n:base.file_hash(ROOT/n) for n in self.study.SOURCES}:
                raise ValueError("Mechanics source/runtime differs")
            proof = dict(directory=str(mechanics.resolve()), report_sha256=base.file_hash(mechanics/"report.json"))
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=output.name+".prepare_", dir=output.parent))
        base.network(temporary, binaries["netconvert"])
        base.atomic_json(temporary/"frozen_plans.json", self.study.plans(smoke))
        command = [binaries["sumo"], "-n", str((output/"network.net.xml").resolve()),
                   "-r", str((output/"routes.rou.xml").resolve()), *base.SUMO_OPTIONS]
        base.atomic_json(temporary/"sumo_command.json", command)
        with zipfile.ZipFile(temporary/"source_snapshot.zip", "x") as archive:
            for name in self.study.SOURCES: archive.write(ROOT/name, name)
        manifest = dict(protocol=self.study.protocol(), configuration=self.study.configuration(smoke),
            planned_jobs=self.study.jobs(smoke), runtime=environment,
            git_commit=subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
            source_sha256={n:base.file_hash(ROOT/n) for n in self.study.SOURCES},
            static_sha256={n:base.file_hash(temporary/n) for n in base.STATIC}, topology_sha256=base.topology(temporary), mechanics=proof)
        if old is not None and old["topology_sha256"] != manifest["topology_sha256"]:
            raise ValueError("Native topology differs from mechanics")
        base.atomic_json(temporary/"manifest.json", manifest)
        (temporary/"sessions").mkdir(); (temporary/"collection.lock").touch()
        base.fresh_output(output)
        os.rename(temporary, output)

    def static_check(self, directory):
        manifest = json.loads((directory/"manifest.json").read_text())
        smoke = manifest["configuration"]["smoke"]
        if (manifest["protocol"] != self.study.protocol() or manifest["configuration"] != self.study.configuration(smoke)
                or manifest["planned_jobs"] != self.study.jobs(smoke)
                or set(manifest["source_sha256"]) != set(self.study.SOURCES)
                or any(base.file_hash(ROOT/n) != h for n,h in manifest["source_sha256"].items())
                or set(manifest["static_sha256"]) != base.STATIC
                or any(base.file_hash(directory/n) != h for n,h in manifest["static_sha256"].items())
                or json.loads((directory/"frozen_plans.json").read_text()) != self.study.plans(smoke)):
            raise ValueError("Protocol/source/static evidence changed; use archived sources")
        def hex_value(value, size):
            return isinstance(value,str) and len(value)==size and all(c in "0123456789abcdef" for c in value)
        env = manifest["runtime"]
        if (set(env) != {"python_version","versions","native_binary_sha256","binary_versions"}
                or not isinstance(env["python_version"],str) or not env["python_version"]
                or env["versions"] != dict.fromkeys(("eclipse-sumo","traci","sumolib"),"1.24.0")
                or set(env["native_binary_sha256"]) != {"sumo","netconvert"}
                or not all(hex_value(h,64) for h in env["native_binary_sha256"].values())
                or set(env["binary_versions"]) != {"sumo","netconvert"}
                or not all("Version 1.24.0" in v for v in env["binary_versions"].values())
                or not hex_value(manifest["git_commit"],40)):
            raise ValueError("Invalid native runtime or revision provenance")
        with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
            if (len(archive.namelist()) != len(self.study.SOURCES) or set(archive.namelist()) != set(self.study.SOURCES)
                    or any(hashlib.sha256(archive.read(n)).hexdigest()!=h for n,h in manifest["source_sha256"].items())):
                raise ValueError("Source archive coverage/hash mismatch")
        pins = self.study.protocol()["base_source_sha256"]
        if not pins or any(manifest["source_sha256"].get(n) != h for n,h in pins.items()):
            raise ValueError("Frozen baseline source pins changed")
        command = json.loads((directory/"sumo_command.json").read_text())
        if (len(command)!=5+len(base.SUMO_OPTIONS) or command[1]!="-n" or command[3]!="-r"
                or Path(command[2]).name!="network.net.xml" or Path(command[4]).name!="routes.rou.xml"
                or command[5:]!=list(base.SUMO_OPTIONS) or base.topology(directory)!=manifest["topology_sha256"]):
            raise ValueError("SUMO command/topology changed")
        if not smoke:
            proof = manifest["mechanics"]; basis = Path(proof["directory"])
            if base.file_hash(basis/"report.json")!=proof["report_sha256"] or not self.verify(basis)["smoke"]:
                raise ValueError("Invalid or changed mechanics basis")
            old = json.loads((basis/"manifest.json").read_text())
            if any(old[k]!=manifest[k] for k in ("source_sha256","runtime","topology_sha256")):
                raise ValueError("Full study differs from verified mechanics")
        return manifest

    def evidence(self, trace, job, plan, axes, smoke):
        return dict(requested_arrival_sha256=base.digest(plan["schedule"]), semantic_trace_sha256=base.digest(trace),
            physical_trace_sha256=base.digest(base.physical_view(trace)),
            proposal_trace_sha256=base.digest([{k:r["decision"][k] for k in ("before_fsm","proposal")}
                                              for r in trace if "decision" in r]),
            historical_trace_sha256=base.digest(base.historical_view(trace)),
            prefix_trace_sha256=base.digest(trace[:self.study.configuration(smoke)["endpoint_ticks"][0]]),
            measurements=self.study.measurements(trace,plan,job,axes,smoke))

    def records(self, directory, manifest):
        smoke = manifest["configuration"]["smoke"]
        tasks = {base.job_name(j):j for j in manifest["planned_jobs"]}
        plans = {p["seed"]:p for p in self.study.plans(smoke)}
        axes, found = base.axes_for(directory), {}
        for path in sorted((directory/"sessions").glob("session_*/record_*.json")):
            row = json.loads(path.read_text()); name = row["job_id"]
            if name not in tasks or name in found or path.name!="record_"+name+".json":
                raise ValueError("Unknown, duplicate or misnamed episode checkpoint")
            expected_path = path.parent.relative_to(directory)/("trace_"+name+".jsonl.gz")
            if (row["job"]!=tasks[name] or row["trace"]!=expected_path.as_posix()
                    or not (directory/row["trace"]).resolve().is_relative_to(directory.resolve())
                    or base.file_hash(directory/row["trace"])!=row["trace_sha256"]):
                raise ValueError("Episode identity/hash changed")
            if any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) or row[k]<0
                   for k in ("collection_seconds","validation_seconds")):
                raise ValueError("Invalid episode timing")
            plan = base.trim(plans[tasks[name]["seed"]],tasks[name]["steps"])
            expected = self.evidence(base.read_trace(directory/row["trace"]),tasks[name],plan,axes,smoke)
            if any(row[k]!=v for k,v in expected.items()):
                raise ValueError("Sensor/policy/signal/metric evidence does not reconstruct")
            found[name] = dict(**tasks[name],family=plan["family"],**{k:v for k,v in row.items() if k not in ("job","job_id")})
        ordered = [found[base.job_name(j)] for j in manifest["planned_jobs"] if base.job_name(j) in found]
        if {base.job_name(j) for j in manifest["planned_jobs"][:len(ordered)]}!=set(found):
            raise ValueError("Episode checkpoints are not the exact planned prefix")
        return ordered

    def history(self, directory, manifest):
        cfg, planned, committed, result = manifest["configuration"],manifest["planned_jobs"],0,[]
        for index, folder in enumerate(sorted((directory/"sessions").glob("session_*"))):
            if folder.name!=f"session_{index:04d}" or index>=cfg["max_sessions"]:
                raise ValueError("Invalid or exhausted session history")
            started = json.loads((folder/"started.json").read_text())
            completed = {p.name for p in folder.glob("record_*.json")}
            expected = {"record_"+base.job_name(j)+".json" for j in planned[committed:committed+len(completed)]}
            if (started["session_index"]!=index or started["cap_seconds"]!=cfg["session_cap_seconds"]
                    or type(started["completed_before"]) is not int or started["completed_before"]!=committed
                    or not 0<=committed<len(planned) or completed!=expected):
                raise ValueError("Session allowance or checkpoint order changed")
            committed += len(completed)
            path = folder/"report.json"
            closed = json.loads(path.read_text()) if path.exists() else None
            if closed is not None:
                if (closed["output_sha256"]!=base.hashes(folder,("report.json",))
                        or type(closed["elapsed_seconds"]) not in (int,float)
                        or not 0<=closed["elapsed_seconds"]<float("inf")
                        or closed["error"] is not None and not isinstance(closed["error"],str)):
                    raise ValueError("Closed session evidence changed")
                if closed["error"] and closed["error"].startswith("SmokeCheckpointPause:") and (
                        not cfg["smoke"] or index!=0 or len(completed)!=self.study.protocol()["smoke_pause_after_jobs"]):
                    raise ValueError("Invalid planned smoke pause")
            result.append(dict(session_index=index,closed=closed is not None,
                elapsed_seconds=closed["elapsed_seconds"] if closed else None,
                error=closed["error"] if closed else "hard_kill_or_unsealed_session",allocated_cap_seconds=cfg["session_cap_seconds"]))
        return result

    def report(self, directory, manifest, rows):
        cfg = manifest["configuration"]; history = self.history(directory,manifest)
        blocked = [s["session_index"] for s in history if not base.restart_allowed(s,cfg["smoke"])]
        complete = len(rows)==len(manifest["planned_jobs"]) and not blocked
        result = dict(complete=complete,scientific_panel_complete=complete and not cfg["smoke"],smoke=cfg["smoke"],
            completed_runs=len(rows),planned_runs=len(manifest["planned_jobs"]),signal_samples=sum(r["steps"] for r in rows),
            sessions=history,integrity_error_sessions=blocked,unobserved_session_times=sum(not s["closed"] for s in history),
            observed_session_seconds=math.fsum(s["elapsed_seconds"] or 0 for s in history),
            maximum_declared_session_allowance_seconds=cfg["max_sessions"]*cfg["session_cap_seconds"],
            publication_ready=False,policy_promoted=False)
        try:
            base.source_check(manifest)
            if complete: result["analysis"] = self.study.analyze(rows,cfg["smoke"])
        except ValueError as exc:
            result.update(complete=False,scientific_panel_complete=False,verification_error=str(exc))
        result["output_sha256"] = base.hashes(directory,("report.json",))
        return result

    def run(self, output, smoke=False, mechanics=None, resume=False):
        output = Path(output)
        if output.exists() and not resume: raise FileExistsError("Preserve existing output; frozen pending jobs require --resume")
        if output.is_symlink() or resume and not output.is_dir(): raise ValueError("Resume requires a real existing directory")
        if subprocess.check_output(["git","status","--porcelain","--",*self.study.SOURCES],cwd=ROOT,text=True).strip():
            raise ValueError("Commit executable sources and protocol before collection")
        if any(base.file_hash(ROOT/n)!=h for n,h in self.study.protocol()["base_source_sha256"].items()):
            raise ValueError("Frozen baseline/physical dependencies changed")
        binaries,environment = base.runtime()
        if not resume: self.prepare(output,smoke,mechanics,binaries,environment)
        with base.exclusive(output):
            manifest = self.static_check(output); cfg = manifest["configuration"]
            if cfg["smoke"]!=smoke or manifest["runtime"]!=environment: raise ValueError("Mode/runtime differs from frozen collection")
            rows = self.records(output,manifest); history = self.history(output,manifest)
            if any(not base.restart_allowed(s,smoke) for s in history): raise ValueError("Previous integrity/runtime failure requires review")
            if len(rows)==len(manifest["planned_jobs"]):
                result = self.report(output,manifest,rows)
                saved = json.loads((output/"report.json").read_text()) if (output/"report.json").exists() else None
                if saved and saved["complete"]:
                    if saved!=result: raise ValueError("Sealed completed collection changed; cannot reseal it")
                    return self.brief(saved)
                base.atomic_json(output/"report.json",result,replace=True)
                return self.brief(result)
            if len(history)>=cfg["max_sessions"]: raise ValueError("Frozen session allowance exhausted")
            session = base.start_session(output,len(history),cfg,len(rows))
            start,conn,error,active = time.monotonic(),None,None,None
            def budget():
                if time.monotonic()-start>cfg["session_cap_seconds"]: raise base.SessionBudgetExceeded("Frozen session cap exceeded")
            try:
                import traci
                command = json.loads((output/"sumo_command.json").read_text())
                label = f"{self.study.protocol()['version']}_{len(history)}"
                traci.start(command,label=label,stdout=subprocess.DEVNULL); conn = traci.getConnection(label)
                axes = base.axes_for(output)
                if [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]!=axes:
                    raise ValueError("Live signal mapping differs from frozen canonical axes")
                lookup = {p["seed"]:p for p in self.study.plans(smoke)}
                for job in manifest["planned_jobs"][len(rows):]:
                    budget(); active = job; conn.load(command[1:])
                    name = base.job_name(job); plan = base.trim(lookup[job["seed"]],job["steps"])
                    path = session/("trace_"+name+".jsonl.gz"); began = time.monotonic()
                    trace = base.save_trace(path,self.study.episode(conn,axes,plan,job,budget))
                    collected = time.monotonic()
                    row = dict(job_id=name,job=job,trace=path.relative_to(output).as_posix(),trace_sha256=base.file_hash(path),
                               **self.evidence(trace,job,plan,axes,smoke),collection_seconds=collected-began)
                    row["validation_seconds"] = time.monotonic()-collected
                    budget(); base.source_check(manifest)
                    base.atomic_json(session/("record_"+name+".json"),row)
                    rows.append(dict(**job,family=plan["family"],**{k:v for k,v in row.items() if k not in ("job","job_id")}))
                    print(f"Completed panel job {len(rows)}/{len(manifest['planned_jobs'])}: {name}",flush=True)
                    if smoke and not history and len(rows)==self.study.protocol()["smoke_pause_after_jobs"]:
                        raise base.SmokeCheckpointPause("Planned native checkpoint restart")
            except (Exception,KeyboardInterrupt) as exc:
                error = f"{type(exc).__name__}: {exc}"; raise
            finally:
                try:
                    if conn is not None: conn.close()
                except Exception as exc:
                    error = f"Connection close failed: {exc}"; raise
                finally:
                    base.atomic_json(session/"report.json",dict(error=error,active_job=active,elapsed_seconds=time.monotonic()-start,
                                                               output_sha256=base.hashes(session,("report.json",))))
                    base.atomic_json(output/"report.json",self.report(output,manifest,rows),replace=True)
            return self.brief(json.loads((output/"report.json").read_text()))

    def collect(self, output, smoke=False, mechanics=None, resume=False):
        for _ in range(self.study.configuration(smoke)["max_sessions"]):
            try: return self.run(output,smoke,mechanics,resume)
            except (base.SessionBudgetExceeded,base.SmokeCheckpointPause) as exc:
                manifest = json.loads((Path(output)/"manifest.json").read_text())
                if len(self.history(Path(output),manifest))>=manifest["configuration"]["max_sessions"]: raise
                print(f"{type(exc).__name__}: {exc}. Continuing only frozen pending jobs.",flush=True)
                resume = True
        raise ValueError("Frozen session allowance exhausted")

    def verify(self, directory):
        directory = Path(directory)
        with base.exclusive(directory):
            manifest = self.static_check(directory); rows = self.records(directory,manifest)
            saved = json.loads((directory/"report.json").read_text())
            if not saved["complete"] or saved!=self.report(directory,manifest,rows):
                raise ValueError("Incomplete or changed collection/summary/coverage")
            return dict(verified=True,smoke=saved["smoke"],scientific_panel_complete=saved["scientific_panel_complete"],
                runs=len(rows),signal_samples=saved["signal_samples"],sessions=len(saved["sessions"]),
                completed_episode_checkpoints=True,independently_rerun_trajectories=0,publication_ready=False)

    def preflight(self, output, mechanics):
        base.fresh_output(Path(output))
        if subprocess.check_output(["git","status","--porcelain","--",*self.study.SOURCES],cwd=ROOT,text=True).strip():
            raise ValueError("Commit executable sources and protocol before collection")
        if mechanics is None or not self.verify(Path(mechanics))["smoke"]: raise ValueError("Verified mechanics smoke required")
        binaries,environment = base.runtime(); manifest = self.static_check(Path(mechanics))
        if environment!=manifest["runtime"]: raise ValueError("Native runtime differs from mechanics")
        with tempfile.TemporaryDirectory(prefix="flowsync-panel-topology-") as path:
            base.network(Path(path),binaries["netconvert"])
            if base.topology(Path(path))!=manifest["topology_sha256"]: raise ValueError("Native topology differs")
        cfg = self.study.configuration(False); jobs = self.study.jobs(False)
        return dict(ready_for_user_run=True,traffic_collected=False,planned_runs=len(jobs),traffic_seeds=len(self.study.plans(False)),
            paired_start_contexts=2*len(self.study.plans(False)),planned_signal_samples=sum(j["steps"] for j in jobs),
            primary_endpoint_seconds=cfg["steps"]//10,session_cap_seconds=cfg["session_cap_seconds"],
            max_sessions=cfg["max_sessions"],output_created=False,publication_ready=False)

    @staticmethod
    def brief(report):
        result = {k:report[k] for k in ("complete","scientific_panel_complete","smoke","completed_runs","planned_runs",
                   "signal_samples","observed_session_seconds","unobserved_session_times","publication_ready")}
        if report["complete"]: result["candidate_screen"] = report["analysis"]["candidate_screen"]
        if "verification_error" in report: result["verification_error"] = report["verification_error"]
        return result
