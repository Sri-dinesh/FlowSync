"""Bounded independent-SUMO branch mechanics; no training/performance screen."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "research/docs/protocols/SUMO_BRANCH_FEASIBILITY_20261023.md"
DT = 0.1
DIRECTIONS = ("n", "s", "e", "w")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class Signal:
    phase: int = 0
    age: int = 0
    stage: str = "green"
    pending: int = 0

    def request(self, target):
        if target != self.phase and self.stage == "green" and self.age >= 80:
            self.pending, self.stage, self.age = target, "yellow", 0

    def advance(self):
        self.age += 1
        if self.stage == "yellow" and self.age == 30:
            self.stage, self.age = "red", 0
        elif self.stage == "red" and self.age == 10:
            self.phase, self.stage, self.age = self.pending, "green", 0

    def lamps(self, axes):
        return "".join(("G" if self.stage == "green" else "y")
                       if self.stage != "red" and axis == self.phase else "r" for axis in axes)


def schedule(seed, start, stop):
    rng = random.Random(seed)
    return [[tick, direction, f"a{seed}_{tick}_{direction}"]
            for tick in range(start, stop) for direction in DIRECTIONS if rng.random() < .02]


def network(output, binary):
    nodes = ET.Element("nodes")
    ET.SubElement(nodes, "node", id="c", x="0", y="0", type="traffic_light")
    edges, connections = ET.Element("edges"), ET.Element("connections")
    for direction, (x, y), opposite in zip(DIRECTIONS, ((0, 200), (0, -200), (200, 0), (-200, 0)), "snwe"):
        ET.SubElement(nodes, "node", id=direction, x=str(x), y=str(y), type="priority")
        for name, origin, destination in (("in", direction, "c"), ("out", "c", direction)):
            ET.SubElement(edges, "edge", id=f"{direction}_{name}", **{"from": origin, "to": destination},
                          numLanes="1", speed="13.89")
        ET.SubElement(connections, "connection", **{"from": f"{direction}_in", "to": f"{opposite}_out"})
    for name, element in (("nodes.nod.xml", nodes), ("edges.edg.xml", edges), ("connections.con.xml", connections)):
        ET.ElementTree(element).write(output/name)
    subprocess.run([binary, "-n", str(output/"nodes.nod.xml"), "-e", str(output/"edges.edg.xml"),
                    "-x", str(output/"connections.con.xml"), "-o", str(output/"network.net.xml"),
                    "--no-turnarounds", "true"], check=True, capture_output=True, timeout=30)
    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="car", carFollowModel="Krauss", sigma="0", speedFactor="1", speedDev="0",
                  length="5", minGap="2.5")
    for direction, opposite in zip(DIRECTIONS, "snwe"):
        ET.SubElement(routes, "route", id=direction, edges=f"{direction}_in {opposite}_out")
    ET.ElementTree(routes).write(output/"routes.rou.xml")


def observed(conn):
    return [[vid, conn.vehicle.getRoadID(vid), round(conn.vehicle.getLanePosition(vid), 6),
             round(conn.vehicle.getSpeed(vid), 6)] for vid in sorted(conn.vehicle.getIDList())]


def audit_signals(trace, axes):
    """Count executed lamp runs independently of the Python signal timer."""
    previous, run_ticks = None, 0
    for row in trace:
        lamps = row["lamps"]
        green_axes = {axes[i] for i, lamp in enumerate(lamps) if lamp in "Gg"}
        yellow_axes = {axes[i] for i, lamp in enumerate(lamps) if lamp in "yY"}
        if len(green_axes) > 1 or green_axes and yellow_axes:
            raise ValueError("Conflicting executed signal permissions")
        state = ("green", next(iter(green_axes))) if green_axes else (
            ("yellow", next(iter(yellow_axes))) if yellow_axes else ("red", None))
        if previous is not None and state != previous:
            before, after = previous[0], state[0]
            if (before, after) not in (("green", "yellow"), ("yellow", "red"), ("red", "green")):
                raise ValueError("Illegal executed clearance transition")
            if ((before == "green" and run_ticks < 80) or (before == "yellow" and run_ticks != 30)
                    or (before == "red" and run_ticks != 10)):
                raise ValueError("Executed signal timing violation")
            run_ticks = 0
        run_ticks += 1
        previous = state


def advance(conn, signal, axes, tick, arrivals, backlog, first_action=None):
    if tick % 20 == 0:
        queues = [sum(conn.edge.getLastStepHaltingNumber(f"{d}_in") for d in pair)
                  for pair in ("ns", "ew")]
        target = first_action if first_action is not None else (
            signal.phase if queues[0] == queues[1] else int(queues[1] > queues[0]))
        signal.request(target)
    lamps = signal.lamps(axes)
    if any(axes[i] != axes[j] and lamps[i] in "Gg" and lamps[j] in "Gg"
           for i in range(len(axes)) for j in range(i)):
        raise ValueError("Conflicting greens")
    conn.trafficlight.setRedYellowGreenState("c", lamps)
    backlog.extend(arrivals)
    inserted, retained, used = [], [], set()
    for due, direction, vid in backlog:
        positions = [conn.vehicle.getLanePosition(v) for v in conn.lane.getLastStepVehicleIDs(f"{direction}_in_0")]
        if direction not in used and (not positions or min(positions) >= 8.):
            conn.vehicle.add(vid, direction, typeID="car", depart="now", departPos="0", departSpeed="0")
            inserted.append(vid)
            used.add(direction)
        else:
            retained.append([due, direction, vid])
    conn.simulationStep()
    if (conn.simulation.getCollidingVehiclesNumber() or conn.simulation.getStartingTeleportNumber()
            or conn.simulation.getPendingVehicles()):
        raise ValueError("Collision, teleport or SUMO pending departure invalidates replay")
    vehicles = observed(conn)
    wait = round(DT*(sum(v[3] < .1 for v in vehicles) + len(retained)), 6)
    record = dict(tick=tick, lamps=lamps, fsm=asdict(signal), vehicles=vehicles, pending=[r.copy() for r in retained],
                  requested=arrivals, inserted=inserted, wait_vehicle_seconds=wait,
                  arrived=sorted(conn.simulation.getArrivedIDList()))
    signal.advance()
    return record, retained


def run(output, deadline_seconds=120):
    if output.exists():
        raise FileExistsError("Use a new output directory")
    if deadline_seconds <= 0 or deadline_seconds > 120:
        raise ValueError("Execution cap must be in (0, 120] seconds")
    import traci
    versions = {name: importlib.metadata.version(name) for name in ("eclipse-sumo", "traci", "sumolib")}
    if set(versions.values()) != {"1.24.0"}:
        raise ValueError("Requires the frozen SUMO/traci/sumolib 1.24.0 installation")
    binaries = {name: shutil.which(name, path=str(Path(sys.executable).parent)) for name in ("sumo", "netconvert")}
    if not all(binaries.values()):
        raise ValueError("SUMO binaries missing from the selected environment")
    output.mkdir(parents=True)
    start = time.monotonic()
    def budget():
        if time.monotonic()-start > deadline_seconds:
            raise TimeoutError("Feasibility execution cap exceeded")
    network(output, binaries["netconvert"])
    command = [binaries["sumo"], "-n", str(output/"network.net.xml"), "-r", str(output/"routes.rou.xml"),
               "--step-length", str(DT), "--seed", "108001", "--save-state.rng", "true",
               "--save-state.precision", "17", "--thread-rngs", "1", "--time-to-teleport", "-1",
               "--no-step-log", "true", "--duration-log.disable", "true", "--xml-validation", "never"]
    manifest = dict(versions=versions, command=command, scope="mechanics only; no performance conclusion",
                    branch_reconstruction="full source replay; snapshot reload failed earlier feasibility checks",
                    source_sha256=file_hash(__file__), protocol_sha256=file_hash(PROTOCOL),
                    future_seeds=[108101, 108102], trace_decimal_precision=6, final_test_access=False)
    conn = None
    try:
        traci.start(command, label="feasibility", verbose=False, stdout=subprocess.DEVNULL)
        conn = traci.getConnection("feasibility")
        axes = [int(links[0][0].split("_")[0] in "ew") for links in conn.trafficlight.getControlledLinks("c")]
        if sorted(axes) != [0, 0, 1, 1]:
            raise ValueError("Unexpected straight-movement signal mapping")
        signal, backlog = Signal(), []
        original = schedule(108001, 0, 1600)
        by_tick = {t: [a for a in original if a[0] == t] for t in range(1600)}
        source = []
        for tick in range(1200):
            budget()
            if tick >= 600 and tick % 20 == 0 and signal.stage == "green" and signal.age >= 80:
                gate = tick
                break
            row, backlog = advance(conn, signal, axes, tick, by_tick[tick], backlog)
            source.append(row)
        else:
            raise ValueError("No prespecified eligible gate")
        snapshot = output/"state.xml"
        conn.simulation.saveState(str(snapshot))
        initial_fsm, initial_backlog = asdict(signal), json.loads(json.dumps(backlog))
        initial_digest = digest(dict(vehicles=observed(conn), fsm=initial_fsm, backlog=initial_backlog))
        futures = {"original": [a for a in original if gate <= a[0] < gate+200],
                   **{str(seed): schedule(seed, gate, gate+200) for seed in (108101, 108102)}}
        manifest.update(gate_tick=gate, initial_digest=initial_digest, fsm=initial_fsm,
                        external_backlog=initial_backlog, schedules=futures, axes=axes)
        # Written before either original continuation or counterfactual outcomes.
        (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        prefix = []
        for tick in range(gate, gate+200):
            budget()
            row, backlog = advance(conn, signal, axes, tick, by_tick[tick], backlog)
            prefix.append(row)
        (output/"source.jsonl").write_text("".join(json.dumps(r)+"\n" for r in source+prefix))
        audit_signals(source+prefix, axes)
        outcomes = []
        for future, arrivals in futures.items():
            for action in ("continuation", "hold", "switch"):
                hashes = []
                for repeat in range(2):
                    # SUMO snapshots omit internal state: reconstruct by replaying
                    # every source tick instead, and validate the full history.
                    conn.load(command[1:])
                    signal, backlog = Signal(), []
                    replay = []
                    for tick in range(gate):
                        budget()
                        row, backlog = advance(conn, signal, axes, tick, by_tick[tick], backlog)
                        replay.append(row)
                    if replay != source:
                        raise ValueError("Full source replay does not reproduce")
                    if digest(dict(vehicles=observed(conn), fsm=asdict(signal), backlog=backlog)) != initial_digest:
                        raise ValueError("Reloaded starting state mismatch")
                    trace = []
                    for tick in range(gate, gate+200):
                        budget()
                        target = None if action == "continuation" else initial_fsm["phase"] ^ int(action == "switch")
                        row, backlog = advance(conn, signal, axes, tick,
                            [a for a in arrivals if a[0] == tick], backlog,
                            first_action=target if tick == gate else None)
                        trace.append(row)
                    with (output/f"trace_{future}_{action}_{repeat}.jsonl").open("x") as stream:
                        for row in trace:
                            stream.write(json.dumps(row, sort_keys=True)+"\n")
                    audit_signals(source+trace, axes)
                    if future == "original" and action == "continuation" and trace != prefix:
                        mismatch = next(i for i, (a, b) in enumerate(zip(trace, prefix)) if a != b)
                        fields = [k for k in trace[mismatch] if trace[mismatch][k] != prefix[mismatch][k]]
                        raise ValueError(f"Unbranched continuation mismatch at tick {gate+mismatch}: {fields}")
                    hashes.append(digest(trace))
                if hashes[0] != hashes[1]:
                    raise ValueError("Same-action/future repeat mismatch")
                outcomes.append(dict(future=future, action=action, trace_sha256=hashes[0],
                                     requested_arrivals_sha256=digest(arrivals)))
        result = dict(complete=True, mechanics_pass=True, branches=len(outcomes), repeated_rollouts=2*len(outcomes),
                      reconstruction="full source replay, not snapshot restore", full_source_replays=2*len(outcomes),
                      original_continuation_reproduced=True,
                      signal_samples=len(source)+len(prefix)+2*len(outcomes)*(gate+200),
                      branch_ticks=200, requested_arrival_pairing=True, trace_precision_decimals=6,
                      scientific_panel_complete=False, publication_ready=False, outcomes=outcomes)
    except Exception as exc:
        result = dict(complete=False, mechanics_pass=False, error=f"{type(exc).__name__}: {exc}",
                      scientific_panel_complete=False, publication_ready=False)
        raise
    finally:
        if conn is not None:
            conn.close()
        if "result" in locals():
            result["elapsed_seconds"] = time.monotonic()-start
            result["output_hashes"] = {p.name: file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
            (output/"report.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ("outcomes", "output_hashes")}, indent=2))


if __name__ == "__main__":
    main()
