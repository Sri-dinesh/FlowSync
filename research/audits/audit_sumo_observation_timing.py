"""Same-state sensing/proposal audit on saved SUMO trajectories; no new traffic."""
import argparse
import csv
from dataclasses import asdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import zipfile

from research.experiments.sumo_switching import ROOT, method_for
from research.observation.sumo_sensing import CountSensor, Delivery, PRESETS
from research.pilots.run_sumo_switching_panel import (
    SOURCES as COLLECTION_SOURCES, file_hash, fresh_output, hashes, verify as verify_collection,
)
from research.policies.sumo_classical import Clock, Counts, choose_action, phase_pressures
from research.policies.sumo_switching import Method, propose

SPEC = "research/manifests/sumo_observation_timing_audit.json"
SOURCES = tuple(sorted((*COLLECTION_SOURCES, SPEC, "research/audits/audit_sumo_observation_timing.py")))
MARGIN = Method("margin1", "max_pressure", "clean", 1)


def plan():
    return json.loads((ROOT/SPEC).read_text())


def probe(clock, delivered):
    packets = {fault.name: Counts.from_dict(delivered[fault.name]["counts"]) for fault in PRESETS}
    margin = propose(MARGIN, packets["clean"], clock)
    return dict(eligible=clock.stage == "green" and clock.age >= 80,
        proposals={**{name: choose_action("max_pressure", packet, clock) for name, packet in packets.items()},
                   "margin1": margin["proposal"]},
        pressures={name: list(phase_pressures(packet)) for name, packet in packets.items()},
        margin_held=margin["margin_held"])


def audit_trace(trace, job, family, steps):
    """Use the previous completed step, never the current/future snapshot."""
    method = method_for(job["method"])
    sensors = {fault.name: CountSensor(fault, job["seed"]) for fault in PRESETS}
    previous, seen = [], 0
    for tick, row in enumerate(trace):
        if tick >= steps or row["tick"] != tick:
            raise ValueError("Extended, reordered or duplicate trace tick")
        delivered = {name: sensor.step(previous, tick).to_dict() for name, sensor in sensors.items()}
        actual = delivered[method.fault]
        if row["sensing"] != actual:
            raise ValueError("Recorded sensing does not reconstruct")
        if tick % 20 == 0:
            decision = row["decision"]
            before = decision["before_fsm"]
            clock = Clock(before["phase"], before["stage"], before["age"])
            chosen = propose(method, Counts.from_dict(actual["counts"]), clock)
            if (decision["packet"] != actual["counts"] or decision["policy"] != chosen
                    or decision["proposal"] != chosen["proposal"]):
                raise ValueError("Recorded packet/proposal/policy does not reconstruct")
            yield dict(seed=job["seed"], family=family, initial_phase=job["initial_phase"],
                method=job["method"], tick=tick, clock=asdict(clock), delivered=delivered,
                recorded_proposal=decision["proposal"], **probe(clock, delivered))
        elif "decision" in row:
            raise ValueError("Off-cadence decision")
        previous, seen = row["vehicles"], tick+1
    if seen != steps:
        raise ValueError("Incomplete trace")


def compare(gates, candidate, reference):
    eligible = [g for g in gates if g["eligible"]]
    changed = [g for g in eligible if g["proposals"][candidate] != g["proposals"][reference]]
    suppressed = sum(g["proposals"][candidate] == g["clock"]["phase"] for g in changed)
    return dict(scheduled_gates=len(gates), eligible_gates=len(eligible), changed_proposals=len(changed),
        suppressed_switch_requests=suppressed, added_switch_requests=len(changed)-suppressed,
        changed_fraction_of_eligible=len(changed)/len(eligible) if eligible else None)


def pattern(gates):
    changed = [g for g in gates if g["eligible"] and g["proposals"]["clean"] != g["proposals"]["delay2s_miss30"]]
    result = dict(mixed_changed=len(changed), delay_only_matches=0, misses_only_matches=0,
                  both_match=0, neither_matches=0, margin_matches=0)
    for gate in changed:
        p = gate["proposals"]
        delay, misses = p["delay2s"] == p["delay2s_miss30"], p["miss30"] == p["delay2s_miss30"]
        key = "both_match" if delay and misses else "delay_only_matches" if delay else "misses_only_matches" if misses else "neither_matches"
        result[key] += 1
        result["margin_matches"] += p["margin1"] == p["delay2s_miss30"]
    return result


def tables(gates, manifest, frozen):
    expected = [(j["seed"], j["initial_phase"], j["method"], tick)
                for j in manifest["planned_jobs"] for tick in range(0, j["steps"], 20)]
    if [(g["seed"], g["initial_phase"], g["method"], g["tick"]) for g in gates] != expected:
        raise ValueError("Audit gates are not the exact frozen job/cadence grid")
    families = {p["seed"]: p["family"] for p in frozen}
    for gate in gates:
        if gate["family"] != families[gate["seed"]] or set(gate["delivered"]) != {f.name for f in PRESETS}:
            raise ValueError("Changed gate family or sensor coverage")
        for fault in PRESETS:
            frame = gate["delivered"][fault.name]
            source_tick = gate["tick"]-fault.delay_ticks if gate["tick"] >= fault.delay_ticks else None
            delivery = Delivery(gate["tick"], source_tick, Counts.from_dict(frame["counts"]))
            if frame != delivery.to_dict():
                raise ValueError("Saved packet clock/shape does not reconstruct")
        computed = probe(Clock(**gate["clock"]), gate["delivered"])
        if any(gate[key] != value for key, value in computed.items()):
            raise ValueError("Saved packet policy probes do not reconstruct")
        method = method_for(gate["method"])
        key = "margin1" if method.margin else method.fault
        if gate["recorded_proposal"] != computed["proposals"][key]:
            raise ValueError("Actual-source proposal differs from its probe")
    summaries, contexts, patterns = [], [], []
    for end in plan()["endpoint_ticks"]:
        selected = [g for g in gates if g["tick"] < end]
        for name, candidate, reference in plan()["comparisons"]:
            for method in ("pressure_clean", "pressure_mixed", "pressure_margin1"):
                subset = [g for g in selected if g["method"] == method]
                summaries.append(dict(endpoint_s=end//10, method=method, comparison=name,
                                      **compare(subset, candidate, reference)))
            for job in manifest["planned_jobs"]:
                subset = [g for g in selected if (g["seed"], g["initial_phase"], g["method"]) ==
                          (job["seed"], job["initial_phase"], job["method"])]
                contexts.append(dict(endpoint_s=end//10, seed=job["seed"], family=families[job["seed"]],
                    initial_phase=job["initial_phase"], method=job["method"], comparison=name,
                    **compare(subset, candidate, reference)))
        for job in manifest["planned_jobs"]:
            subset = [g for g in selected if (g["seed"], g["initial_phase"], g["method"]) ==
                      (job["seed"], job["initial_phase"], job["method"])]
            patterns.append(dict(endpoint_s=end//10, seed=job["seed"], family=families[job["seed"]],
                initial_phase=job["initial_phase"], method=job["method"], **pattern(subset)))
    return dict(summary=summaries, contexts=contexts, patterns=patterns)


def input_paths(source):
    source = source.resolve()
    spec = plan()
    if (file_hash(source/"report.json") != spec["source_report_sha256"]
            or file_hash(source/"manifest.json") != spec["source_manifest_sha256"]):
        raise ValueError("Study differs from the pinned post-hoc audit plan")
    manifest = json.loads((source/"manifest.json").read_text())
    return dict(collection=source, mechanics=Path(manifest["mechanics"]["directory"]).resolve())


def coverage(gates, manifest):
    jobs = manifest["planned_jobs"]
    return dict(complete=True, source_episodes=len(jobs), replayed_source_ticks=sum(j["steps"] for j in jobs),
        scheduled_gates=len(gates), traffic_seeds=len({j["seed"] for j in jobs}),
        paired_start_contexts=len({(j["seed"], j["initial_phase"]) for j in jobs}),
        distinct_visited_method_bases=len({j["method"] for j in jobs}), raw_counterfactual_sensor_replay=True,
        native_traffic_runs=0, independent_kinematic_reruns=0, policy_promoted=False,
        publication_ready=False, post_hoc=True)


def csv_write(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def export(source, output):
    source, output = Path(source), Path(output)
    fresh_output(output)
    inputs = input_paths(source)
    if any(output.resolve().is_relative_to(path.resolve()) for path in inputs.values()):
        raise ValueError("Audit output must be outside frozen inputs")
    if subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCES], cwd=ROOT, text=True).strip():
        raise ValueError("Commit the audit queries before inspecting proposal results")
    before = {name: hashes(path) for name, path in inputs.items()}
    source_hashes = {name: file_hash(ROOT/name) for name in SOURCES}
    checked = verify_collection(source)
    if not checked["scientific_panel_complete"] or checked["runs"] != 36:
        raise ValueError("Requires the completed scientific panel")
    manifest = json.loads((source/"manifest.json").read_text())
    frozen = json.loads((source/"frozen_plans.json").read_text())
    records = {json.dumps(r["job"], sort_keys=True): r for path in source.glob("sessions/session_*/record_*.json")
               for r in [json.loads(path.read_text())]}
    families, gates, start = {p["seed"]: p["family"] for p in frozen}, [], time.monotonic()
    for index, job in enumerate(manifest["planned_jobs"]):
        row = records[json.dumps(job, sort_keys=True)]
        with gzip.open(source/row["trace"], "rt") as stream:
            gates.extend(audit_trace((json.loads(line) for line in stream), job, families[job["seed"]], job["steps"]))
        print(f"Audited saved trajectory {index+1}/36: {row['job_id']}", flush=True)
    result = tables(gates, manifest, frozen)
    elapsed = time.monotonic()-start
    if (any(hashes(path) != before[name] for name, path in inputs.items())
            or any(file_hash(ROOT/name) != value for name, value in source_hashes.items())):
        raise ValueError("Input or executable source changed during audit")
    output.mkdir(parents=True)
    with gzip.open(output/"gates.jsonl.gz", "wt") as stream:
        for gate in gates:
            stream.write(json.dumps(gate, allow_nan=False)+"\n")
    for name, rows in result.items(): csv_write(output/(name+".csv"), rows)
    with zipfile.ZipFile(output/"source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCES: archive.write(ROOT/name, name)
    report = dict(**coverage(gates, manifest), audit_plan=plan(), source_verification=checked,
        elapsed_audit_seconds=elapsed, csv_rows={name: len(rows) for name, rows in result.items()},
        summary=result["summary"])
    write(output/"report.json", report)
    write(output/"manifest.json", dict(complete=True, input_directories={k: str(v.resolve()) for k, v in inputs.items()},
        input_sha256=before, source_sha256=source_hashes,
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        output_sha256=hashes(output)))
    return dict(complete=True, source_episodes=36, scheduled_gates=len(gates), native_traffic_runs=0,
                publication_ready=False, csv_rows=report["csv_rows"])


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory/"manifest.json").read_text())
    if not manifest["complete"] or hashes(directory, ("manifest.json",)) != manifest["output_sha256"]:
        raise ValueError("Audit output coverage/hash mismatch")
    inputs = {k: Path(v) for k, v in manifest["input_directories"].items()}
    if (input_paths(inputs["collection"]) != inputs
            or any(hashes(path) != manifest["input_sha256"][k] for k, path in inputs.items())
            or set(manifest["source_sha256"]) != set(SOURCES)
            or any(file_hash(ROOT/n) != h for n, h in manifest["source_sha256"].items())):
        raise ValueError("Audit input/source evidence changed; use archived sources")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if (len(archive.namelist()) != len(SOURCES) or set(archive.namelist()) != set(SOURCES)
                or any(hashlib.sha256(archive.read(n)).hexdigest() != h for n, h in manifest["source_sha256"].items())):
            raise ValueError("Audit source archive does not reconstruct")
    with gzip.open(directory/"gates.jsonl.gz", "rt") as stream:
        gates = [json.loads(line) for line in stream]
    source = inputs["collection"]
    source_manifest = json.loads((source/"manifest.json").read_text())
    result = tables(gates, source_manifest, json.loads((source/"frozen_plans.json").read_text()))
    report = json.loads((directory/"report.json").read_text())
    receipt = report["source_verification"]
    expected_receipt = dict(verified=True, smoke=False, scientific_panel_complete=True,
        runs=len(source_manifest["planned_jobs"]),
        signal_samples=sum(j["steps"] for j in source_manifest["planned_jobs"]),
        completed_episode_checkpoints=True, independently_rerun_trajectories=0, publication_ready=False)
    if (report["audit_plan"] != plan() or report["summary"] != result["summary"]
            or report["csv_rows"] != {k: len(v) for k, v in result.items()}
            or any(report[k] != v for k, v in coverage(gates, source_manifest).items())
            or any(receipt.get(k) != v for k, v in expected_receipt.items())
            or type(report["elapsed_audit_seconds"]) not in (int, float)
            or not math.isfinite(report["elapsed_audit_seconds"]) or report["elapsed_audit_seconds"] < 0):
        raise ValueError("Audit summary/scope does not reconstruct")
    for name, rows in result.items():
        with (directory/(name+".csv")).open(newline="") as stream:
            if list(csv.DictReader(stream)) != [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows]:
                raise ValueError("Audit CSV does not reconstruct")
    return dict(verified=True, scheduled_gates=len(gates), saved_packet_probes_reconstructed=True,
        raw_counterfactual_sensor_replay=False, independently_rerun_trajectories=0, publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.verify and args.source: parser.error("--verify takes no source override")
    print(json.dumps(verify(args.verify) if args.verify else export(args.source or ROOT/plan()["source"], args.output), indent=2))


if __name__ == "__main__":
    main()
