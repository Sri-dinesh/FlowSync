import copy
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from research.analysis.sumo_classical_metrics import percentile95, summarize, validate_trace
from research.audits.sumo_branch_feasibility import Signal, digest, file_hash
from research.audits.verify_sumo_classical_panel import verify
from research.experiments.sumo_classical_runtime import SOURCE_FILES, configuration, plans
from research.policies.sumo_classical import CONTROLLERS, Clock, choose_action, observe

AXES = [0, 1, 0, 1]
ROOT = Path(__file__).resolve().parents[2]


def trace_rows(schedule, steps, controller="halted", inventory=None):
    """Synthetic saved-trace contract fixture, not a SUMO traffic simulation."""
    signal, previous, active, rows = Signal(), [], {}, []
    for tick in range(steps):
        requests = [a for a in schedule if a[0] == tick]
        row = dict(tick=tick, requested=requests)
        if tick % 20 == 0:
            packet = observe(previous)
            proposal = choose_action(controller, packet, Clock(signal.phase, signal.stage, signal.age))
            row["decision"] = dict(packet=packet.to_dict(), before_fsm=asdict(signal), proposal=proposal)
            signal.request(proposal)
        if inventory is None:
            inserted, pending, arrived = [a[2] for a in requests], [], []
            active.update({a[2]: [a[2], a[1]+"_in", 100., 1.] for a in requests})
            vehicles = list(active.values())
        else:
            inserted, pending, arrived, vehicles = inventory(tick)
        row.update(fsm=asdict(signal), lamps=signal.lamps(AXES), inserted=inserted, pending=pending,
                   arrived=arrived, vehicles=vehicles,
                   wait_vehicle_seconds=round((sum(v[3] < .1 for v in vehicles)+len(pending))/10, 6))
        rows.append(row)
        previous = vehicles
        signal.advance()
    return rows


def waiting_fixture():
    schedule = [[0, "n", "a"], [1, "n", "b"], [2, "e", "c"]]
    def inventory(tick):
        return (["a"] if tick == 0 else ["c"] if tick == 2 else ["b"] if tick == 6 else [],
                [[1, "n", "b"]] if 1 <= tick < 6 else [],
                ["a"] if tick == 5 else ["c"] if tick == 10 else [],
                ([["a", "n_in", 0., 0.]] if tick < 5 else [])
                + ([["b", "n_in", 0., 0.]] if tick >= 6 else [])
                + ([["c", "e_in", 10., 1.]] if 2 <= tick < 10 else []))
    return schedule, trace_rows(schedule, 41, inventory=inventory)


def test_waiting_counts_completed_unfinished_and_external_queue():
    schedule, trace = waiting_fixture()
    metrics = validate_trace(trace, schedule, "halted", AXES, 41)
    assert metrics["requested_vehicles"] == 3 and metrics["completed_trips"] == 2
    assert metrics["final_active"] == 1
    assert metrics["total_stopped_wait_vehicle_seconds"] == 4.5
    assert metrics["mean_stopped_wait_per_requested_vehicle_s"] == 1.5
    assert metrics["p95_accumulated_wait_s"] == 3.65
    assert metrics["endpoint_max_active_pending_wait_s"] == 4.
    assert percentile95([0, .5, 4.]) == 3.65


@pytest.mark.parametrize("mutation", ["packet", "proposal", "off_cadence", "fsm", "lamps", "wait", "fifo",
                                     "duplicate_active", "duplicate_trip", "missing_tick", "nan_last_step"])
def test_saved_trace_rejects_inconsistent_measurements(mutation):
    schedule, trace = waiting_fixture()
    if mutation == "packet":
        trace[0]["decision"]["packet"]["incoming"][0] = 1
    elif mutation == "proposal":
        trace[20]["decision"]["proposal"] = 1
    elif mutation == "off_cadence":
        trace[1]["decision"] = trace[0]["decision"]
    elif mutation in ("fsm", "lamps"):
        if mutation == "fsm":
            trace[1]["fsm"]["age"] = 99
        else:
            trace[1]["lamps"] = "GGGG"
    elif mutation == "wait":
        trace[1]["wait_vehicle_seconds"] = 0.
    elif mutation == "fifo":
        trace[1]["pending"] = []
    elif mutation == "duplicate_active":
        trace[2]["vehicles"].append(trace[2]["vehicles"][0])
    elif mutation == "duplicate_trip":
        trace[6]["arrived"] = ["a"]
    elif mutation == "missing_tick":
        trace.pop()
    else:
        trace[-1]["vehicles"][0][3] = float("nan")
    with pytest.raises(ValueError):
        validate_trace(trace, schedule, "halted", AXES, 41)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+"\n")


@pytest.fixture(scope="module")
def saved_panel(tmp_path_factory):
    output = tmp_path_factory.mktemp("synthetic_sumo_contract")
    cfg, frozen, rows = configuration(True), plans(True), []
    write_json(output/"manifest.json", dict(configuration=cfg, controllers=list(CONTROLLERS),
        versions=dict.fromkeys(("eclipse-sumo", "traci", "sumolib"), "1.24.0"), planned_cases=1, planned_runs=6,
        source_hashes={name: file_hash(ROOT/name) for name in SOURCE_FILES}))
    write_json(output/"frozen_plans.json", frozen)
    with zipfile.ZipFile(output/"source_snapshot.zip", "w") as archive:
        for name in SOURCE_FILES:
            archive.write(ROOT/name, name)
    for name in ("sumo_command.json", "nodes.nod.xml", "edges.edg.xml", "connections.con.xml", "routes.rou.xml"):
        (output/name).write_text("synthetic test only")
    (output/"network.net.xml").write_text('<net>'+''.join(
        f'<connection tl="c" linkIndex="{i}" from="{d}_in"/>' for i, d in enumerate("nesw"))+'</net>')
    for plan in frozen:
        for controller in CONTROLLERS:
            trace = trace_rows(plan["schedule"], cfg["steps"], controller)
            for repeat in range(cfg["repeats"]):
                name = f"trace_{plan['seed']}_{controller}_r{repeat}.jsonl.gz"
                with gzip.open(output/name, "wt") as stream:
                    stream.writelines(json.dumps(row)+"\n" for row in trace)
                rows.append(dict(seed=plan["seed"], family=plan["family"], controller=controller, repeat=repeat,
                    metrics=validate_trace(trace, plan["schedule"], controller, AXES, cfg["steps"]), trace=name,
                    semantic_trace_sha256=digest(trace), requested_arrival_sha256=digest(plan["schedule"])))
    (output/"runs.jsonl").write_text(''.join(json.dumps(row)+"\n" for row in rows))
    write_json(output/"report.json", dict(complete=True, comparison_complete=False, smoke=True,
        repeat_mechanics_verified=True, models_trained=0, policy_promoted=False, cases=1, runs=6,
        signal_samples=4800, **summarize(rows, frozen),
        output_hashes={p.name: file_hash(p) for p in output.iterdir()}))
    return output


def test_saved_panel_reconstructs_without_sumo_installation(saved_panel):
    result = verify(saved_panel)
    assert result["verified"] and result["smoke"] and not result["comparison_complete"]
    assert result["runs"] == 6 and result["signal_samples"] == 4800
    assert result["independently_rerun_trajectories"] == 0


@pytest.mark.parametrize("mutation", ["incomplete", "relabel_smoke", "summary", "duplicate_run", "unhashed_output",
                                     "source_omission", "trace_packet_with_updated_hashes"])
def test_verifier_rejects_partial_or_relabelled_evidence(saved_panel, tmp_path, mutation):
    output = tmp_path/"panel"
    shutil.copytree(saved_panel, output)
    report = json.loads((output/"report.json").read_text())
    if mutation == "incomplete":
        report["complete"] = False
    elif mutation == "relabel_smoke":
        report["comparison_complete"] = True
    elif mutation == "summary":
        report["controllers"]["fixed"]["completed_trips"] += 1
    elif mutation == "duplicate_run":
        with (output/"runs.jsonl").open("a") as stream:
            stream.write((output/"runs.jsonl").read_text().splitlines()[0]+"\n")
        report["output_hashes"]["runs.jsonl"] = file_hash(output/"runs.jsonl")
    elif mutation == "unhashed_output":
        del report["output_hashes"]["runs.jsonl"]
    elif mutation == "source_omission":
        manifest = json.loads((output/"manifest.json").read_text())
        manifest["source_hashes"].pop(next(iter(manifest["source_hashes"])))
        write_json(output/"manifest.json", manifest)
        report["output_hashes"]["manifest.json"] = file_hash(output/"manifest.json")
    else:
        rows = [json.loads(line) for line in (output/"runs.jsonl").read_text().splitlines()]
        target = output/rows[0]["trace"]
        with gzip.open(target, "rt") as stream:
            trace = [json.loads(line) for line in stream]
        trace[0]["decision"]["packet"]["incoming"][0] += 1
        with gzip.open(target, "wt") as stream:
            stream.writelines(json.dumps(row)+"\n" for row in trace)
        rows[0]["semantic_trace_sha256"] = digest(trace)
        (output/"runs.jsonl").write_text(''.join(json.dumps(row)+"\n" for row in rows))
        for name in (target.name, "runs.jsonl"):
            report["output_hashes"][name] = file_hash(output/name)
    write_json(output/"report.json", report)
    with pytest.raises(ValueError):
        verify(output)


def test_summaries_keep_repeats_out_of_primary_and_reject_missing_cases(saved_panel):
    rows = [json.loads(line) for line in (saved_panel/"runs.jsonl").read_text().splitlines()]
    result = summarize(rows, plans(True))
    changed = copy.deepcopy(rows)
    for row in changed:
        if row["repeat"] == 1:
            row["metrics"]["completed_trips"] += 1000
    assert summarize(changed, plans(True)) == result
    with pytest.raises(ValueError, match="Incomplete/duplicate"):
        summarize(rows[1:], plans(True))
