"""Bounded synthetic camera-contract and frozen-policy input-sufficiency audit."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import zipfile

import numpy as np
import torch

from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.realworld.models.schemas import BoundingBox, VehicleDetection
from server.app.realworld.pipeline.quadrant_counter import QuadrantCounter
from server.app.rl.observations import OBSERVED_VERSION, encode_policy_observation
from server.app.simulation.traffic_math import MOVEMENT_KEYS, compute_movement_pressures, compute_total_pressure, normalize_total_pressure
from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS

ROOT = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "4e1dbe5"
COUNTER_PATH = "server/app/realworld/pipeline/quadrant_counter.py"
BASELINE_COUNTER_HASH = "6ae867986a5379b74b7280d79cd07a91e9e5988dbf0ac9ff859a2ec59764fb57"
PARENTS = {
    101: ("checkpoint_warmup.pt", "1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725"),
    202: ("checkpoint_50.pt", "a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4"),
    303: ("checkpoint_100.pt", "e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052"),
}
SPECIFICATION = dict(
    role="synthetic engineering diagnostic; not traffic performance or real CCTV validation",
    approach_patterns=[[2, 2, 2, 2], [8, 8, 2, 2], [2, 2, 8, 8], [8, 2, 4, 2], [0, 0, 6, 6], [6, 6, 0, 0]],
    direction_order=["north", "south", "east", "west"], left_fractions=[0., .5, 1.], right_fraction=0.,
    current_phases=[0, 1, 2, 3], green_age_seconds=15., forecast_features=[0.]*8,
    outgoing_counts=[0]*4, phase_service_timers=[0.]*4,
    geometry_grid="19 by 19 bottom-centres, x/y=50,100,...,950 in a 1000 by 1000 frame",
    geometry_detection_confidence=.99,
    interpretation="Different proposals for two completions witness insufficiency of approach totals. "
                   "Agreement in the finite set is not a robustness certificate. These completions have no assigned probabilities. "
                   "Signal/history/downstream features are hypothetical fixed known values, not inferred from a camera. "
                   "No trajectories establish reachability, action benefit, throughput, safety or sim-to-real transfer.",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def movement_completions(totals):
    """Retain every distinct enumerated completion; zero approaches add no duplicates."""
    seen = set()
    for fractions in itertools.product(SPECIFICATION["left_fractions"], repeat=4):
        values = tuple(v for n, f in zip(totals, fractions) for v in (int(n*(1-f)), int(n*f), 0))
        if values not in seen:
            seen.add(values)
            yield dict(zip(MOVEMENT_KEYS, values))


def state(counts, phase):
    outgoing = dict(zip(SPECIFICATION["direction_order"], SPECIFICATION["outgoing_counts"]))
    observation = np.zeros(28, dtype=np.float32)
    observation[:12] = np.tanh(np.array([counts[m] for m in MOVEMENT_KEYS])/15.)
    observation[12+phase] = 1
    observation[16] = SPECIFICATION["green_age_seconds"]/40.
    observation[18] = normalize_total_pressure(compute_total_pressure(compute_movement_pressures(counts, outgoing)))
    mask = np.array([p == phase or any(counts[m] for m in PHASE_DEMAND_MOVEMENTS[p]) for p in range(4)])
    context = ControllerContext(timestep=0, current_phase=phase, time_in_phase=15., valid_action_mask=mask,
                                movement_queues=counts, outgoing_counts=outgoing,
                                phase_starvation_times=dict(enumerate(SPECIFICATION["phase_service_timers"])))
    return observation, context


def geometry_audit(baseline_source):
    namespace = {"__package__": "server.app.realworld.pipeline", "__name__": "frozen_quadrant_counter"}
    exec(compile(baseline_source, "frozen_quadrant_counter.py", "exec"), namespace)
    previous, current = namespace["QuadrantCounter"](), QuadrantCounter()
    rows = []
    for x, y in itertools.product(range(50, 1000, 50), repeat=2):
        detection = VehicleDetection(frame_id=len(rows), timestamp_ms=0, frame_width=1000, frame_height=1000,
            bboxes=[BoundingBox(x1=x-5, x2=x+5, y1=y-10, y2=y, confidence=.99, class_id=2, class_name="car")])
        a, b = previous.count(detection), current.count(detection)
        rows.append(dict(x=x, y=y, legacy_counts=a, corrected_counts=b,
                         legacy_assignments=sum(a.values()), corrected_assignments=sum(b.values())))
    return rows


def policy_audit(parent_root):
    inputs, groups, scores, parents = [], [], [], []
    pressure = MaxPressureController()
    for pattern, totals in enumerate(SPECIFICATION["approach_patterns"]):
        for phase in SPECIFICATION["current_phases"]:
            start = len(inputs)
            for counts in movement_completions(totals):
                observation, context = state(counts, phase)
                inputs.append(dict(input_id=len(inputs), group_id=len(groups), movement_counts=counts,
                    observation=encode_policy_observation(observation, context, OBSERVED_VERSION).tolist(),
                    valid_action_mask=context.valid_action_mask.tolist(),
                    max_pressure_action=pressure.act(observation, context)))
            groups.append(dict(group_id=len(groups), pattern=pattern, approach_totals=totals, phase=phase,
                               input_ids=list(range(start, len(inputs)))))
    tensor = torch.tensor([r["observation"] for r in inputs], dtype=torch.float32)
    masks = torch.tensor([r["valid_action_mask"] for r in inputs], dtype=torch.bool)
    summaries = []
    for seed, (filename, expected) in PARENTS.items():
        path = parent_root/f"seed_{seed}"/filename
        if sha(path) != expected:
            raise ValueError(f"Frozen parent {seed} hash mismatch")
        controller = D3QNController(checkpoint_path=str(path))
        metadata = controller.checkpoint_metadata
        if metadata["obs_version"] != OBSERVED_VERSION or metadata["reward_version"] != "v5_single_switch_delay":
            raise ValueError("Expected the frozen v7/v5 parents")
        with torch.inference_mode():
            q = controller.agent.online_net(tensor, masks).numpy()
        if q.shape != (len(inputs), 4) or not np.isfinite(q).all():
            raise ValueError("Invalid network output")
        masked = np.where(masks.numpy(), q, -np.inf).argmax(axis=1)
        unmasked = q.argmax(axis=1)
        seed_groups = []
        for group in groups:
            ids = group["input_ids"]
            actions = sorted(set(int(masked[i]) for i in ids))
            raw_actions = sorted(set(int(unmasked[i]) for i in ids))
            witness = next(([ids[0], i] for i in ids if masked[i] != masked[ids[0]]), None)
            # Exercise the actual controller, including its observation adapter, at every witness or anchor.
            for i in witness or [ids[0]]:
                observation, context = state(inputs[i]["movement_counts"], group["phase"])
                controller.reset()
                if controller.act(observation, context) != int(masked[i]):
                    raise ValueError("Batch proposal differs from controller inference")
                if not np.allclose(controller.get_diagnostics()["q_values"], q[i], rtol=1e-5, atol=1e-5):
                    raise ValueError("Batch Q values differ from controller inference")
            seed_groups.append(dict(group_id=group["group_id"], masked_actions=actions,
                unmasked_actions=raw_actions, witness_input_ids=witness,
                max_pressure_actions=sorted({inputs[i]["max_pressure_action"] for i in ids})))
        scores.extend(dict(seed=seed, input_id=r["input_id"], q_values=q[i].tolist(),
                           masked_action=int(masked[i]), unmasked_action=int(unmasked[i])) for i, r in enumerate(inputs))
        summaries.append(dict(seed=seed, groups=len(groups),
            masked_ambiguous_groups=sum(len(g["masked_actions"]) > 1 for g in seed_groups),
            unmasked_ambiguous_groups=sum(len(g["unmasked_actions"]) > 1 for g in seed_groups),
            group_results=seed_groups))
        if sha(path) != expected:
            raise ValueError("Checkpoint changed during audit")
        parents.append(dict(seed=seed, path=str(path.relative_to(ROOT)), sha256=expected, metadata=metadata))
    return inputs, groups, scores, summaries, parents


def run(output):
    if output.exists():
        raise FileExistsError("Choose a new audit output directory")
    parent_root = ROOT/"results/research_training/pilot_v5_kbW0lsY3"
    if output.resolve().is_relative_to(parent_root):
        raise ValueError("Audit must remain outside frozen parents")
    torch.set_num_threads(1)
    torch.manual_seed(0)
    baseline = subprocess.check_output(["git", "show", f"{BASELINE_REVISION}:{COUNTER_PATH}"], cwd=ROOT)
    if hashlib.sha256(baseline).hexdigest() != BASELINE_COUNTER_HASH:
        raise ValueError("Historical counter identity mismatch")
    output.mkdir(parents=True, exist_ok=False)
    (output/"specification.json").write_text(json.dumps(SPECIFICATION, indent=2)+"\n")
    # The specification is saved before reading any model outcome.
    geometry = geometry_audit(baseline)
    inputs, groups, scores, summaries, parents = policy_audit(parent_root)
    for name, rows in (("geometry", geometry), ("inputs", inputs), ("groups", groups), ("scores", scores)):
        (output/f"{name}.jsonl").write_text("".join(json.dumps(r, allow_nan=False)+"\n" for r in rows))
    (output/"legacy_quadrant_counter.py").write_bytes(baseline)
    source_files = [Path(__file__).resolve().relative_to(ROOT).as_posix(), COUNTER_PATH,
        "server/app/realworld/models/schemas.py", "server/app/realworld/models/config.py",
        "server/app/controllers/d3qn.py", "server/app/controllers/max_pressure.py", "server/app/controllers/base.py",
        "server/app/rl/observations.py", "server/app/rl/dqn_agent.py", "server/app/rl/dqn_network.py",
        "server/app/rl/hyperparams.py", "server/app/rl/replay_buffer.py",
        "server/app/simulation/traffic_math.py", "server/app/simulation/traffic_signal.py"]
    with zipfile.ZipFile(output/"source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in source_files:
            archive.write(ROOT/name, name)
    report = dict(complete=True, synthetic=True, traffic_rollouts=0, real_camera_frames=0, models_trained=0,
        publication_ready=False, policy_promoted=False, physical_actuation=False, parents=parents,
        numpy_version=np.__version__, torch_version=torch.__version__,
        legacy_counter_sha256=BASELINE_COUNTER_HASH, geometry_frames=len(geometry),
        legacy_assignment_histogram=dict(Counter(r["legacy_assignments"] for r in geometry)),
        corrected_assignment_histogram=dict(Counter(r["corrected_assignments"] for r in geometry)),
        hypothetical_states=len(inputs), aggregate_input_groups=len(groups), policy_evaluations=len(scores),
        max_pressure_ambiguous_groups=sum(len({inputs[i]["max_pressure_action"] for i in g["input_ids"]}) > 1 for g in groups),
        policies=summaries, source_sha256={name: sha(ROOT/name) for name in source_files},
        output_sha256={p.name: sha(p) for p in sorted(output.iterdir())})
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_output(args.verify), indent=2))
        return
    result = run(args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ("source_sha256", "output_sha256", "parents", "policies")}, indent=2))
    print(json.dumps([{k: v for k, v in row.items() if k != "group_results"} for row in result["policies"]], indent=2))


def verify_output(directory):
    """Recompute the finite diagnostic, including every frozen-model forward pass."""
    report = json.loads((directory/"report.json").read_text())
    required = {"specification.json", "geometry.jsonl", "inputs.jsonl", "groups.jsonl", "scores.jsonl",
                "legacy_quadrant_counter.py", "source_snapshot.zip"}
    if set(report["output_sha256"]) != required or not report["complete"]:
        raise ValueError("Incomplete audit output coverage")
    for name, expected in report["output_sha256"].items():
        if sha(directory/name) != expected:
            raise ValueError(f"Changed audit output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if set(archive.namelist()) != set(report["source_sha256"]):
            raise ValueError("Incomplete source coverage")
        for name, expected in report["source_sha256"].items():
            path = (ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or sha(path) != expected or hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("Source changed; use the archived implementation to reproduce this audit")
    if json.loads((directory/"specification.json").read_text()) != SPECIFICATION:
        raise ValueError("Changed finite diagnostic specification")
    baseline = (directory/"legacy_quadrant_counter.py").read_bytes()
    if hashlib.sha256(baseline).hexdigest() != BASELINE_COUNTER_HASH:
        raise ValueError("Changed historical counter")
    torch.set_num_threads(1)
    geometry = geometry_audit(baseline)
    inputs, groups, scores, summaries, parents = policy_audit(ROOT/"results/research_training/pilot_v5_kbW0lsY3")
    for name, rebuilt in (("geometry", geometry), ("inputs", inputs), ("groups", groups), ("scores", scores)):
        recorded = [json.loads(line) for line in (directory/f"{name}.jsonl").read_text().splitlines()]
        if rebuilt != recorded:
            raise ValueError(f"Recorded {name} do not reproduce exactly in this runtime")
    expected = dict(complete=True, synthetic=True, traffic_rollouts=0, real_camera_frames=0, models_trained=0,
        publication_ready=False, policy_promoted=False, physical_actuation=False, parents=parents,
        policies=summaries, legacy_counter_sha256=BASELINE_COUNTER_HASH, geometry_frames=len(geometry),
        legacy_assignment_histogram={str(k): v for k, v in Counter(r["legacy_assignments"] for r in geometry).items()},
        corrected_assignment_histogram={str(k): v for k, v in Counter(r["corrected_assignments"] for r in geometry).items()},
        hypothetical_states=len(inputs), aggregate_input_groups=len(groups), policy_evaluations=len(scores),
        max_pressure_ambiguous_groups=sum(len({inputs[i]["max_pressure_action"] for i in g["input_ids"]}) > 1 for g in groups))
    if any(report[key] != value for key, value in expected.items()):
        raise ValueError("Audit summaries or scope do not reconstruct")
    return dict(verified=True, geometry_cases=len(geometry), input_states=len(inputs),
                policy_evaluations=len(scores), real_camera_frames=0, traffic_rollouts=0,
                scope="Exact arithmetic and frozen-policy inference reproduction in the current runtime")


if __name__ == "__main__":
    main()
