"""Frozen independent-SUMO action/future panel; no learned-policy training."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import importlib.metadata
import json
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import sys
import time
import zipfile

from research.audits.sumo_branch_feasibility import (
    DT, DIRECTIONS, Signal, advance, audit_signals, digest, file_hash, network, observed,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "research/docs/protocols/SUMO_FUTURE_PANEL_20261023.md"
FAMILIES = (("balanced", .2, .2, (109001, 109002)),
            ("ns_dominant", .3, .1, (109101, 109102)),
            ("ew_dominant", .1, .3, (109201, 109202)))


def future_seed(source, role, index, smoke):
    return int(digest(["sumo-futures-v1", smoke, source, role, index])[:12], 16)


def arrivals(seed, start, stop, ns_rate, ew_rate):
    rng = random.Random(seed)
    return [[t, d, f"a{seed}_{t}_{d}"] for t in range(start, stop) for d in DIRECTIONS
            if rng.random() < DT*(ns_rate if d in "ns" else ew_rate)]


def write_trace(path, rows):
    with gzip.open(path, "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True)+"\n")


def wait_by_vehicle(trace):
    waits = {}
    for row in trace:
        stopped = [v[0] for v in row["vehicles"] if v[3] < .1]
        stopped += [v[2] for v in row["pending"]]
        if len(stopped) != len(set(stopped)):
            raise ValueError("Vehicle counted both active and pending")
        for vid in stopped:
            waits[vid] = waits.get(vid, 0.)+DT
    return waits


def outcome(prefix, trace):
    waits = wait_by_vehicle(prefix+trace)
    present = [v[0] for v in trace[-1]["vehicles"]]+[v[2] for v in trace[-1]["pending"]]
    return dict(delay=round(sum(r["wait_vehicle_seconds"] for r in trace), 6),
                throughput=sum(len(r["arrived"]) for r in trace),
                endpoint_wait=round(max((waits.get(vid, 0.) for vid in present), default=0.), 6),
                ticks=len(trace), signal_violations=0)


def gain(base, alternative):
    return [round(base["delay"]-alternative["delay"], 6), alternative["throughput"]-base["throughput"],
            round(base["endpoint_wait"]-alternative["endpoint_wait"], 6)]


def qualified(values):
    return values[0] > 1 and values[1] >= 0 and values[2] >= -1


def harmful(values):
    return values[0] < -1 or values[1] < 0 or values[2] < -1


def choose(rows, baseline):
    alternative = 1-baseline
    values = [gain(r[str(baseline)], r[str(alternative)]) for r in rows]
    mean = [statistics.mean(v[i] for v in values) for i in range(3)]
    return alternative if qualified(mean) else baseline


def summarize(cases, rows, choices, smoke):
    source_scores, counts = [], {"positive": 0, "negative": 0, "mixed_gates": 0}
    for case in cases:
        selected = [r for r in rows if r["source"] == case["source"] and r["role"] == "check"]
        expected = 2 if smoke else 8
        if len(selected) != expected or len({r["index"] for r in selected}) != expected:
            raise ValueError("Incomplete/duplicate check futures")
        fixed = choices[str(case["source"])]
        base = case["baseline"]
        gains = [gain(r[str(base)], r[str(1-base)]) for r in selected]
        positive, negative = sum(g[0] > 1 for g in gains), sum(g[0] < -1 for g in gains)
        counts["positive"] += positive
        counts["negative"] += negative
        counts["mixed_gates"] += positive > 0 and negative > 0
        arms = {}
        for arm, action in fixed.items():
            values = [gain(r[str(base)], r[str(action)]) for r in selected]
            arms[arm] = dict(mean_gain=[statistics.mean(v[i] for v in values) for i in range(3)],
                             changed=action != base, harmful=sum(harmful(v) for v in values),
                             qualified=sum(qualified(v) for v in values), cases=len(values))
        source_scores.append(dict(source=case["source"], family=case["family"], positive_futures=positive,
                                  negative_futures=negative, arms=arms))
    return dict(source_scores=source_scores, sign_counts=counts,
                arms={arm: dict(mean_gain=[statistics.mean(s["arms"][arm]["mean_gain"][i] for s in source_scores)
                                          for i in range(3)],
                                changed_gates=sum(s["arms"][arm]["changed"] for s in source_scores),
                                harmful=sum(s["arms"][arm]["harmful"] for s in source_scores),
                                qualified=sum(s["arms"][arm]["qualified"] for s in source_scores))
                      for arm in ("baseline", "single", "mean8")})


def run(output, smoke=False):
    if output.exists():
        raise FileExistsError("Choose a new output directory")
    import traci
    versions = {n: importlib.metadata.version(n) for n in ("eclipse-sumo", "traci", "sumolib")}
    if set(versions.values()) != {"1.24.0"}:
        raise ValueError("Install the pinned optional SUMO requirements")
    binaries = {n: shutil.which(n, path=str(Path(sys.executable).parent)) for n in ("sumo", "netconvert")}
    if not all(binaries.values()):
        raise ValueError("SUMO binaries absent from this environment")
    output.mkdir(parents=True)
    start, cap = time.monotonic(), 180 if smoke else 1800
    def budget():
        if time.monotonic()-start > cap:
            raise TimeoutError("Frozen collection budget exceeded")
    network(output, binaries["netconvert"])
    command = [binaries["sumo"], "-n", str(output/"network.net.xml"), "-r", str(output/"routes.rou.xml"),
               "--step-length", str(DT), "--seed", "108001", "--time-to-teleport", "-1",
               "--no-step-log", "true", "--duration-log.disable", "true", "--xml-validation", "never"]
    families = (("balanced", .2, .2, (109901,)),) if smoke else FAMILIES
    cases, prefixes, rows, choices, conn = [], {}, [], {}, None
    horizon = 200 if smoke else 400
    sources = [Path(__file__), ROOT/"research/audits/sumo_branch_feasibility.py", PROTOCOL]
    manifest = dict(smoke=smoke, versions=versions, horizon_ticks=horizon, cap_seconds=cap,
                    families=families, planned_sources=1 if smoke else 6,
                    source_hashes={str(p.relative_to(ROOT)): file_hash(p) for p in sources},
                    command=command, reconstruction="full source replay", manuscript_policy_evaluated=False)
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for path in sources:
            archive.write(path, path.relative_to(ROOT))
    try:
        traci.start(command, label="sumo_panel", stdout=subprocess.DEVNULL)
        conn = traci.getConnection("sumo_panel")
        axes = [int(links[0][0].split("_")[0] in "ew") for links in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0, 0, 1, 1]:
            raise ValueError("Unexpected signal mapping")
        for family, ns, ew, seeds in families:
            for seed in seeds:
                conn.load(command[1:])
                signal, backlog, prefix = Signal(), [], []
                source_arrivals = arrivals(seed, 0, 1200, ns, ew)
                for tick in range(1200):
                    budget()
                    if tick >= 600 and tick % 20 == 0 and signal.stage == "green" and signal.age >= 80:
                        break
                    row, backlog = advance(conn, signal, axes, tick, [a for a in source_arrivals if a[0] == tick], backlog)
                    prefix.append(row)
                else:
                    raise ValueError("Planned source lacks eligible gate")
                queues = [sum(conn.edge.getLastStepHaltingNumber(f"{d}_in") for d in pair) for pair in ("ns", "ew")]
                baseline = signal.phase if queues[0] == queues[1] else int(queues[1] > queues[0])
                future_roles = [("single", -1)]+[("fit", i) for i in range(2 if smoke else 8)]
                future_roles += [("check", i) for i in range(8, 10 if smoke else 16)]
                futures = [dict(role=role, index=i, seed=future_seed(seed, role, i, smoke),
                    arrivals=arrivals(future_seed(seed, role, i, smoke), tick, tick+horizon, ns, ew)) for role, i in future_roles]
                case = dict(source=seed, family=family, gate=tick, baseline=baseline, current_phase=signal.phase,
                            source_arrivals=source_arrivals, source_trace_sha256=digest(prefix),
                            starting_digest=digest(dict(vehicles=observed(conn), fsm=asdict(signal), backlog=backlog)), futures=futures)
                cases.append(case)
                prefixes[seed] = prefix
                write_trace(output/f"source_{seed}.jsonl.gz", prefix)
        (output/"frozen_cases.json").write_text(json.dumps(cases, indent=2)+"\n")
        frozen_hash = file_hash(output/"frozen_cases.json")
        # All sources/gates/schedules are fixed before any branch outcomes.
        for role_group in (("single", "fit"), ("check",)):
            for case in cases:
                for future in (f for f in case["futures"] if f["role"] in role_group):
                    record = dict(source=case["source"], role=future["role"], index=future["index"],
                                  requested_arrivals_sha256=digest(future["arrivals"]))
                    for action in (0, 1):
                        conn.load(command[1:])
                        signal, backlog, prefix = Signal(), [], []
                        for tick in range(case["gate"]):
                            budget()
                            row, backlog = advance(conn, signal, axes, tick,
                                [a for a in case["source_arrivals"] if a[0] == tick], backlog)
                            prefix.append(row)
                        if digest(prefix) != case["source_trace_sha256"] or digest(dict(
                            vehicles=observed(conn), fsm=asdict(signal), backlog=backlog)) != case["starting_digest"]:
                            raise ValueError("Branch source history changed")
                        trace = []
                        for tick in range(case["gate"], case["gate"]+horizon):
                            budget()
                            row, backlog = advance(conn, signal, axes, tick,
                                [a for a in future["arrivals"] if a[0] == tick], backlog,
                                first_action=action if tick == case["gate"] else None)
                            trace.append(row)
                        audit_signals(prefix+trace, axes)
                        record[str(action)] = outcome(prefix, trace)
                        record[str(action)]["first_execution"] = trace[0]["fsm"]["pending"] if trace[0]["fsm"]["stage"] == "yellow" else trace[0]["fsm"]["phase"]
                        name = f"branch_{case['source']}_{future['role']}_{future['index']}_{action}.jsonl.gz"
                        write_trace(output/name, trace)
                    rows.append(record)
                    with (output/"outcomes.jsonl").open("a") as stream:
                        stream.write(json.dumps(record)+"\n")
                if role_group == ("single", "fit"):
                    selection = [r for r in rows if r["source"] == case["source"]]
                    choices[str(case["source"])] = dict(baseline=case["baseline"],
                        single=choose([r for r in selection if r["role"] == "single"], case["baseline"]),
                        mean8=choose([r for r in selection if r["role"] == "fit"], case["baseline"]))
            if role_group == ("single", "fit"):
                (output/"frozen_choices.json").write_text(json.dumps(choices, indent=2)+"\n")
                choice_hash = file_hash(output/"frozen_choices.json")
        expected = {(case["source"], f["role"], f["index"]) for case in cases for f in case["futures"]}
        keys = [(r["source"], r["role"], r["index"]) for r in rows]
        if len(keys) != len(set(keys)) or set(keys) != expected or file_hash(output/"frozen_cases.json") != frozen_hash or file_hash(output/"frozen_choices.json") != choice_hash:
            raise ValueError("Incomplete, duplicate or changed frozen evidence")
        result = dict(complete=True, scientific_panel_complete=not smoke, smoke=smoke, branches=2*len(rows),
                      sources=len(cases), publication_ready=False, **summarize(cases, rows, choices, smoke))
    except Exception as exc:
        result = dict(complete=False, scientific_panel_complete=False, smoke=smoke,
                      error=f"{type(exc).__name__}: {exc}", completed_future_pairs=len(rows), publication_ready=False)
        raise
    finally:
        if conn is not None:
            conn.close()
        if "result" in locals():
            result["elapsed_seconds"] = time.monotonic()-start
            result["output_hashes"] = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            (output/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    report = run(args.output, args.smoke)
    print(json.dumps({k: v for k, v in report.items() if k not in ("source_scores", "output_hashes")}, indent=2))


if __name__ == "__main__":
    main()
