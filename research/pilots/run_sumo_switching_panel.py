"""Checkpointed SUMO margin/robustness panel; no fitting or policy promotion."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

from research.analysis.sumo_switching_metrics import summarize
from research.audits.sumo_branch_feasibility import digest, file_hash, network
from research.experiments.sumo_switching import (
    ROOT, configuration, episode, historical_view, job_name, jobs, measurements,
    method_for, physical_view, plans, protocol, trim,
)
from research.pilots.run_sumo_sensing_panel import (
    SOURCES as OLD_SOURCES, SUMO_OPTIONS, episode as anchor_episode,
    read_trace, runtime, save_trace, validate_trace as validate_anchor,
)
from research.observation.sumo_sensing import PRESETS

SOURCES = tuple(sorted(set(OLD_SOURCES) | {
    "research/manifests/sumo_switching.json", "research/policies/sumo_switching.py",
    "research/experiments/sumo_switching.py", "research/analysis/sumo_switching_metrics.py",
    "research/pilots/run_sumo_switching_panel.py",
}))
STATIC = {"frozen_plans.json", "source_snapshot.zip", "sumo_command.json", "nodes.nod.xml",
          "edges.edg.xml", "connections.con.xml", "network.net.xml", "routes.rou.xml"}


class SessionBudgetExceeded(TimeoutError):
    pass


class SmokeCheckpointPause(InterruptedError):
    pass


def atomic_json(path, value, replace=False):
    with tempfile.NamedTemporaryFile("w", prefix=path.name+".", suffix=".part", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        os.replace(temporary, path)
    else:
        os.link(temporary, path)  # Atomic publication without replacing an existing record.
        temporary.unlink()


def hashes(directory, exclude=()):
    return {p.relative_to(directory).as_posix(): file_hash(p) for p in sorted(directory.rglob("*"))
            if p.is_file() and p.relative_to(directory).as_posix() not in exclude}


def source_check(manifest):
    if any(file_hash(ROOT/n) != h for n, h in manifest["source_sha256"].items()):
        raise ValueError("Executable source changed during collection; preserve this attempt")


def fresh_output(output):
    if output.exists() or output.is_symlink():
        raise FileExistsError("Choose a new collection directory")
    if any((p/"manifest.json").exists() or (p/"report.json").exists() for p in output.resolve().parents):
        raise ValueError("Output must be outside recorded evidence directories")


def axes_for(directory):
    links = [n for n in ET.parse(directory/"network.net.xml").getroot().findall("connection") if n.get("tl") == "c"]
    axes = [int(n.get("from").split("_")[0] in "ew") for n in sorted(links, key=lambda n: int(n.get("linkIndex")))]
    if sorted(axes) != [0, 0, 1, 1]:
        raise ValueError("Unexpected protected movement mapping")
    return axes


def topology(directory):
    return digest(ET.tostring(ET.parse(directory/"network.net.xml").getroot(), encoding="unicode"))


def measured(trace, plan, job, axes, smoke):
    if job["kind"] != "anchor":
        return measurements(trace, plan, job, axes, smoke)
    method = method_for(job["method"])
    fault = next(f for f in PRESETS if f.name == method.fault)
    return {str(end//10): validate_anchor(trace[:end], trim(plan, end), method.controller, fault, axes)
            for end in configuration(smoke)["endpoint_ticks"] if end <= job["steps"]}


def static_check(directory):
    manifest = json.loads((directory/"manifest.json").read_text())
    smoke = manifest["configuration"]["smoke"]
    cfg = configuration(smoke)
    if (manifest["protocol"] != protocol() or manifest["configuration"] != cfg
            or manifest["planned_jobs"] != jobs(smoke) or set(manifest["source_sha256"]) != set(SOURCES)
            or any(file_hash(ROOT/n) != h for n, h in manifest["source_sha256"].items())
            or set(manifest["static_sha256"]) != STATIC
            or any(file_hash(directory/n) != h for n, h in manifest["static_sha256"].items())):
        raise ValueError("Recorded protocol/source/static evidence changed; use archived sources")
    environment = manifest["runtime"]
    def hex_digest(value, size):
        return isinstance(value, str) and len(value) == size and all(c in "0123456789abcdef" for c in value)
    if (set(environment) != {"python_version", "versions", "native_binary_sha256", "binary_versions"}
            or not isinstance(environment["python_version"], str) or not environment["python_version"]
            or environment["versions"] != dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0")
            or set(environment["native_binary_sha256"]) != {"sumo", "netconvert"}
            or not all(hex_digest(h, 64) for h in environment["native_binary_sha256"].values())
            or set(environment["binary_versions"]) != {"sumo", "netconvert"}
            or not all("Version 1.24.0" in v for v in environment["binary_versions"].values())
            or not hex_digest(manifest["git_commit"], 40)):
        raise ValueError("Missing or invalid native runtime/revision provenance")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if (len(archive.namelist()) != len(SOURCES) or set(archive.namelist()) != set(SOURCES)
                or any(hashlib.sha256(archive.read(n)).hexdigest() != h for n, h in manifest["source_sha256"].items())):
            raise ValueError("Source archive coverage/hash mismatch")
    if (set(protocol()["base_source_sha256"]) != set(OLD_SOURCES)
            or any(manifest["source_sha256"][n] != h for n, h in protocol()["base_source_sha256"].items())):
        raise ValueError("Frozen baseline/physical source pins changed")
    if json.loads((directory/"frozen_plans.json").read_text()) != plans(smoke):
        raise ValueError("Changed frozen arrival schedules")
    command = json.loads((directory/"sumo_command.json").read_text())
    if (len(command) != 5+len(SUMO_OPTIONS) or command[1] != "-n" or command[3] != "-r"
            or Path(command[2]).name != "network.net.xml" or Path(command[4]).name != "routes.rou.xml"
            or command[5:] != list(SUMO_OPTIONS) or topology(directory) != manifest["topology_sha256"]):
        raise ValueError("Changed SUMO command/topology")
    if not smoke:
        proof = manifest["mechanics"]
        basis = Path(proof["directory"])
        if file_hash(basis/"report.json") != proof["report_sha256"] or not verify(basis)["smoke"]:
            raise ValueError("Changed or invalid mechanics basis")
        old = json.loads((basis/"manifest.json").read_text())
        if any(old[key] != manifest[key] for key in ("source_sha256", "runtime", "topology_sha256")):
            raise ValueError("Full study differs from verified mechanics")
    return manifest


def records(directory, manifest):
    smoke = manifest["configuration"]["smoke"]
    tasks = {job_name(j): j for j in manifest["planned_jobs"]}
    plan_lookup = {p["seed"]: p for p in plans(smoke)}
    axes, found = axes_for(directory), {}
    for path in sorted((directory/"sessions").glob("session_*/record_*.json")):
        row = json.loads(path.read_text())
        if any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) or row[k] < 0
               for k in ("collection_seconds", "validation_seconds")):
            raise ValueError("Invalid episode timing telemetry")
        name = row["job_id"]
        if name not in tasks or name in found or path.name != "record_"+name+".json":
            raise ValueError("Unknown, duplicate or misnamed completed episode")
        task = tasks[name]
        expected_trace = path.parent.relative_to(directory)/("trace_"+name+".jsonl.gz")
        if (row["job"] != task or row["trace"] != expected_trace.as_posix()
                or not (directory/row["trace"]).resolve().is_relative_to(directory.resolve())
                or file_hash(directory/row["trace"]) != row["trace_sha256"]):
            raise ValueError("Completed episode identity/hash changed")
        trace = read_trace(directory/row["trace"])
        plan = trim(plan_lookup[task["seed"]], task["steps"])
        if (row["requested_arrival_sha256"] != digest(plan["schedule"])
                or row["semantic_trace_sha256"] != digest(trace)
                or row["physical_trace_sha256"] != digest(physical_view(trace))
                or row["historical_trace_sha256"] != digest(historical_view(trace))
                or row["prefix_trace_sha256"] != digest(trace[:configuration(smoke)["endpoint_ticks"][0]])
                or row["measurements"] != measured(trace, plan, task, axes, smoke)):
            raise ValueError("Completed sensor/policy/signal/metric record does not reconstruct")
        found[name] = dict(**task, family=plan["family"], **{k: v for k, v in row.items() if k not in ("job", "job_id")})
    ordered = [found[job_name(j)] for j in manifest["planned_jobs"] if job_name(j) in found]
    if {job_name(j) for j in manifest["planned_jobs"][:len(ordered)]} != set(found):
        raise ValueError("Completed markers are not the exact planned prefix")
    return ordered


def session_history(directory, cfg):
    result = []
    committed = 0
    planned = jobs(cfg["smoke"])
    for index, folder in enumerate(sorted((directory/"sessions").glob("session_*"))):
        if folder.name != f"session_{index:04d}" or index >= cfg["max_sessions"]:
            raise ValueError("Invalid or exhausted session history")
        started = json.loads((folder/"started.json").read_text())
        if started["session_index"] != index or started["cap_seconds"] != cfg["session_cap_seconds"]:
            raise ValueError("Changed session allowance")
        if type(started["completed_before"]) is not int or not 0 <= started["completed_before"] < len(planned):
            raise ValueError("Session cannot start after all planned jobs are complete")
        completed = {p.name for p in folder.glob("record_*.json")}
        expected = {"record_"+job_name(j)+".json" for j in planned[committed:committed+len(completed)]}
        if started["completed_before"] != committed or completed != expected:
            raise ValueError("Changed session checkpoint order")
        committed += len(completed)
        report_path = folder/"report.json"
        closed = json.loads(report_path.read_text()) if report_path.exists() else None
        if closed is not None:
            if closed["output_sha256"] != hashes(folder, ("report.json",)):
                raise ValueError("Closed session evidence changed")
            if type(closed["elapsed_seconds"]) not in (int, float) or not 0 <= closed["elapsed_seconds"] < float("inf"):
                raise ValueError("Invalid recorded session time")
            error = closed["error"]
            if error is not None and not isinstance(error, str):
                raise ValueError("Invalid session error metadata")
            if error is not None and error.startswith("SmokeCheckpointPause:") and (
                    not cfg["smoke"] or index != 0 or len(completed) != protocol()["smoke_pause_after_jobs"]):
                raise ValueError("Invalid planned smoke interruption")
        result.append(dict(session_index=index, closed=closed is not None,
                           elapsed_seconds=None if closed is None else closed["elapsed_seconds"],
                           error="hard_kill_or_unsealed_session" if closed is None else closed["error"],
                           allocated_cap_seconds=cfg["session_cap_seconds"]))
    return result


def restart_allowed(session, smoke):
    if not session["closed"] or session["error"] is None:
        return True
    return session["error"].startswith(("SessionBudgetExceeded:", "KeyboardInterrupt:")) or (
        smoke and session["error"].startswith("SmokeCheckpointPause:"))


def start_session(directory, index, cfg, completed):
    target = directory/"sessions"/f"session_{index:04d}"
    staged = Path(tempfile.mkdtemp(prefix=".session_prepare_", dir=directory/"sessions"))
    atomic_json(staged/"started.json", dict(session_index=index, cap_seconds=cfg["session_cap_seconds"],
                                          completed_before=completed, start_wall_time=time.time()))
    os.rename(staged, target)
    return target


def prepare(output, smoke, mechanics, binaries, environment):
    fresh_output(output)
    proof = None
    if not smoke:
        if mechanics is None or not verify(mechanics)["smoke"]:
            raise ValueError("Full study requires --mechanics pointing to a complete verified smoke")
        old = json.loads((mechanics/"manifest.json").read_text())
        if old["runtime"] != environment or old["source_sha256"] != {n: file_hash(ROOT/n) for n in SOURCES}:
            raise ValueError("Mechanics source/runtime differs")
        proof = dict(directory=str(mechanics.resolve()), report_sha256=file_hash(mechanics/"report.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=output.name+".prepare_", dir=output.parent))
    network(temporary, binaries["netconvert"])
    atomic_json(temporary/"frozen_plans.json", plans(smoke))
    command = [binaries["sumo"], "-n", str((output/"network.net.xml").resolve()),
               "-r", str((output/"routes.rou.xml").resolve()), *SUMO_OPTIONS]
    atomic_json(temporary/"sumo_command.json", command)
    with zipfile.ZipFile(temporary/"source_snapshot.zip", "x") as archive:
        for name in SOURCES: archive.write(ROOT/name, name)
    manifest = dict(protocol=protocol(), configuration=configuration(smoke), planned_jobs=jobs(smoke),
        runtime=environment, git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_sha256={n: file_hash(ROOT/n) for n in SOURCES}, static_sha256={n: file_hash(temporary/n) for n in STATIC},
        topology_sha256=topology(temporary), mechanics=proof)
    if not smoke and manifest["topology_sha256"] != old["topology_sha256"]:
        raise ValueError("Topology differs from mechanics; preserve preparation evidence")
    atomic_json(temporary/"manifest.json", manifest)
    (temporary/"sessions").mkdir()
    (temporary/"collection.lock").touch()
    os.rename(temporary, output)


@contextmanager
def exclusive(directory):
    with (directory/"collection.lock").open("rb") as handle:
        try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError("Another collector/verifier holds this collection") from None
        try: yield
        finally: fcntl.flock(handle, fcntl.LOCK_UN)


def report_for(directory, manifest, rows):
    cfg = manifest["configuration"]
    grid_complete = len(rows) == len(manifest["planned_jobs"])
    history = session_history(directory, cfg)
    blocked = [s["session_index"] for s in history if not restart_allowed(s, cfg["smoke"])]
    complete = grid_complete and not blocked
    result = dict(complete=complete, scientific_panel_complete=complete and not cfg["smoke"], smoke=cfg["smoke"],
        complete_episode_grid=grid_complete, integrity_error_sessions=blocked,
        completed_runs=len(rows), planned_runs=len(manifest["planned_jobs"]),
        signal_samples=sum(r["steps"] for r in rows), sessions=history, max_sessions=cfg["max_sessions"],
        maximum_declared_session_allowance_seconds=cfg["max_sessions"]*cfg["session_cap_seconds"],
        observed_session_seconds=math.fsum(s["elapsed_seconds"] or 0 for s in history),
        unobserved_session_times=sum(not s["closed"] for s in history),
        policy_promoted=False, publication_ready=False)
    try:
        source_check(manifest)
        if complete: result["analysis"] = summarize(rows, plans(cfg["smoke"]), cfg["smoke"])
    except ValueError as exc:
        result.update(complete=False, scientific_panel_complete=False, verification_error=str(exc))
    result["output_sha256"] = hashes(directory, ("report.json",))
    return result


def run(output, smoke=False, mechanics=None, resume=False):
    output = Path(output)
    if output.exists() and not resume:
        raise FileExistsError("Preserve existing output; use --resume only for its frozen pending jobs")
    if output.is_symlink() or resume and not output.is_dir():
        raise ValueError("Resume requires an existing real collection directory")
    if subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCES], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the executable protocol before native collection")
    if any(file_hash(ROOT/n) != h for n, h in protocol()["base_source_sha256"].items()):
        raise ValueError("Frozen pressure/sensing/physical dependencies changed")
    binaries, environment = runtime()
    if not resume: prepare(output, smoke, mechanics, binaries, environment)
    with exclusive(output):
        manifest = static_check(output)
        cfg = manifest["configuration"]
        if cfg["smoke"] != smoke or manifest["runtime"] != environment:
            raise ValueError("Resume mode/runtime differs from frozen collection")
        rows = records(output, manifest)
        history = session_history(output, cfg)
        if any(not restart_allowed(s, cfg["smoke"]) for s in history):
            raise ValueError("A previous integrity/runtime failure requires review before any continuation")
        if len(rows) == len(manifest["planned_jobs"]):
            result = report_for(output, manifest, rows)
            atomic_json(output/"report.json", result, replace=True)
            return brief(result)
        if len(history) >= cfg["max_sessions"]:
            raise ValueError("Frozen session allowance exhausted; preserve evidence and review budget")
        session = start_session(output, len(history), cfg, len(rows))
        start, conn, error, active = time.monotonic(), None, None, None
        def budget():
            if time.monotonic()-start > cfg["session_cap_seconds"]:
                raise SessionBudgetExceeded("Frozen switching collection session cap exceeded; resume preserves completed episodes")
        try:
            import traci
            command = json.loads((output/"sumo_command.json").read_text())
            label = f"switching_panel_{len(history)}"
            traci.start(command, label=label, stdout=subprocess.DEVNULL)
            conn = traci.getConnection(label)
            axes = axes_for(output)
            live = [int(link[0][0].split("_")[0] in "ew") for link in conn.trafficlight.getControlledLinks("c")]
            if live != axes: raise ValueError("Live canonical signal mapping differs")
            lookup = {p["seed"]: p for p in plans(smoke)}
            for job in manifest["planned_jobs"][len(rows):]:
                budget()
                active = job
                conn.load(command[1:])
                name = job_name(job)
                plan, method = trim(lookup[job["seed"]], job["steps"]), method_for(job["method"])
                trace_file = session/("trace_"+name+".jsonl.gz")
                collection_start = time.monotonic()
                if job["kind"] == "anchor":
                    fault = next(f for f in PRESETS if f.name == method.fault)
                    stream = anchor_episode(conn, axes, plan, method.controller, fault, budget)
                else: stream = episode(conn, axes, plan, method, job["initial_phase"], budget)
                trace = save_trace(trace_file, stream)
                collected_at = time.monotonic()
                row = dict(job_id=name, job=job, trace=trace_file.relative_to(output).as_posix(),
                    trace_sha256=file_hash(trace_file), requested_arrival_sha256=digest(plan["schedule"]),
                    semantic_trace_sha256=digest(trace), historical_trace_sha256=digest(historical_view(trace)),
                    physical_trace_sha256=digest(physical_view(trace)),
                    prefix_trace_sha256=digest(trace[:cfg["endpoint_ticks"][0]]),
                    measurements=measured(trace, plan, job, axes, smoke),
                    collection_seconds=collected_at-collection_start)
                row["validation_seconds"] = time.monotonic()-collected_at
                budget()
                source_check(manifest)
                atomic_json(session/("record_"+name+".json"), row)
                rows.append(dict(**job, family=plan["family"], **{k: v for k, v in row.items() if k not in ("job", "job_id")}))
                print(f"Completed switching job {len(rows)}/{len(manifest['planned_jobs'])}: {name}", flush=True)
                if smoke and len(history) == 0 and len(rows) == protocol()["smoke_pause_after_jobs"]:
                    raise SmokeCheckpointPause("Planned native restart after committed episode checkpoints")
        except (Exception, KeyboardInterrupt) as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            try:
                if conn is not None: conn.close()
            except Exception as exc:
                error = f"Connection close failed: {exc}"
                raise
            finally:
                atomic_json(session/"report.json", dict(error=error, active_job=active,
                    elapsed_seconds=time.monotonic()-start, output_sha256=hashes(session, ("report.json",))))
                atomic_json(output/"report.json", report_for(output, manifest, rows), replace=True)
        return brief(json.loads((output/"report.json").read_text()))


def brief(report):
    result = {k: report[k] for k in ("complete", "scientific_panel_complete", "smoke", "completed_runs", "planned_runs",
        "signal_samples", "observed_session_seconds", "unobserved_session_times", "publication_ready")}
    if report["complete"]: result["candidate_screen"] = report["analysis"]["candidate_screen"]
    if "verification_error" in report: result["verification_error"] = report["verification_error"]
    if report["integrity_error_sessions"]: result["integrity_error_sessions"] = report["integrity_error_sessions"]
    return result


def collect(output, smoke=False, mechanics=None, resume=False):
    for _ in range(configuration(smoke)["max_sessions"]):
        try:
            return run(output, smoke, mechanics, resume)
        except (SessionBudgetExceeded, SmokeCheckpointPause) as exc:
            cfg = configuration(smoke)
            if len(session_history(Path(output), cfg)) >= cfg["max_sessions"]:
                raise
            print(f"{type(exc).__name__}: {exc}. Continuing only frozen pending jobs.", flush=True)
            resume = True
    raise ValueError("Frozen session allowance exhausted")


def verify(directory):
    directory = Path(directory)
    with exclusive(directory):
        manifest = static_check(directory)
        rows = records(directory, manifest)
        report = json.loads((directory/"report.json").read_text())
        expected = report_for(directory, manifest, rows)
        if not report["complete"] or report != expected:
            raise ValueError("Incomplete or changed collection/summaries/coverage")
        return dict(verified=True, smoke=report["smoke"], scientific_panel_complete=report["scientific_panel_complete"],
            runs=len(rows), signal_samples=report["signal_samples"], sessions=len(report["sessions"]),
            completed_episode_checkpoints=True, independently_rerun_trajectories=0, publication_ready=False)


def preflight(output, mechanics):
    output = Path(output)
    fresh_output(output)
    if subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCES], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the executable protocol before collection")
    if mechanics is None or not verify(Path(mechanics))["smoke"]:
        raise ValueError("A verified mechanics smoke is required")
    _, environment = runtime()
    manifest = static_check(Path(mechanics))
    source_check(manifest)
    if environment != manifest["runtime"]:
        raise ValueError("Native runtime differs from mechanics")
    with tempfile.TemporaryDirectory(prefix="flowsync-switching-topology-") as temporary:
        binaries, _ = runtime()
        network(Path(temporary), binaries["netconvert"])
        if topology(Path(temporary)) != manifest["topology_sha256"]:
            raise ValueError("Current native topology differs from mechanics")
    cfg = configuration()
    return dict(ready_for_user_run=True, traffic_collected=False, planned_runs=len(jobs()),
                traffic_seeds=len(plans()), paired_start_contexts=len(plans())*2,
                planned_signal_samples=sum(j["steps"] for j in jobs()),
                primary_endpoint_seconds=cfg["steps"]//10,
                session_cap_seconds=cfg["session_cap_seconds"], max_sessions=cfg["max_sessions"],
                native_runtime_and_sources_match=True, topology_matches=True, output_created=False,
                publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    mode.add_argument("--preflight", type=Path, help="Proposed full output; no traffic collected or output created")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mechanics", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.verify and (args.smoke or args.mechanics or args.resume): parser.error("--verify takes no collection options")
    if args.preflight and (args.smoke or args.resume): parser.error("--preflight is for a new full collection")
    result = preflight(args.preflight, args.mechanics) if args.preflight else (
        verify(args.verify) if args.verify else collect(args.output, args.smoke, args.mechanics, args.resume))
    print(json.dumps(result, indent=2))
    if args.output and not result["complete"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
