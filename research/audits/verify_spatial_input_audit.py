#!/usr/bin/env python3
"""Verify spatial diagnosis hashes, saved network probes and report; no rollouts."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audits.audit_spatial_inputs import ARMS, SEEDS, STAGES, summarize, weight_report
from research.audits.audit_training_drift import score_actions
from research.training.train_policy import file_hash
from research.policies.spatial_baselines import UpstreamMaxPressureController
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.observations import SPATIAL_KEY
from server.app.simulation.traffic_math import MOVEMENT_KEYS


def verify(directory):
    manifest = json.loads((directory/"manifest.json").read_text())
    report = json.loads((directory/"report.json").read_text())
    for path, digest in manifest["input_hashes"].items():
        if file_hash(Path(path)) != digest:
            raise ValueError(f"Input hash mismatch: {path}")
    for name, digest in report["output_hashes"].items():
        if file_hash(directory/name) != digest:
            raise ValueError(f"Output hash mismatch: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        for name, digest in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Archived source hash mismatch: {name}")
    rows = [json.loads(line) for line in (directory/"sources.jsonl").read_text().splitlines()]
    recomputed = summarize(rows)
    if any(report[k] != v for k,v in recomputed.items()):
        raise ValueError("Saved summary does not reproduce from raw records")
    batch, models = Path(manifest["batch"]), {}
    for seed in SEEDS:
        models[seed] = {f"{arm}_{stage}": D3QNController(checkpoint_path=str(
            batch/f"{arm}_seed_{seed}"/f"checkpoint_{stage}.pt")) for arm in ARMS for stage in STAGES}
    weights = {str(seed): weight_report(models[seed]) for seed in SEEDS}
    if weights != json.loads((directory/"weights.json").read_text()):
        raise ValueError("Saved weight analysis does not reproduce")
    network_scores = 0
    for row in rows:
        cases = manifest["cases"][f"control_{row['training_seed']}"]
        case = next(c for c in cases if c["role"] == row["role"] and c["index"] == row["index"])
        arm = row["acting"] if row["acting"] != "teacher" else "spatial"
        checkpoint = batch/f"{arm}_seed_{row['training_seed']}"/"checkpoint_90.pt"
        if row["seed"] != case["seed"] or row["checkpoint_hash"] != file_hash(checkpoint):
            raise ValueError("Raw source case/checkpoint mismatch")
        if row["role"] == "demo" and not row["demo_replay_verified"]:
            raise ValueError("Unverified demonstration")
        for event in row["events"]:
            mask = np.asarray(event["mask"], dtype=bool)
            natural = np.asarray(event["observation"], dtype=np.float32)
            for name, model in models[row["training_seed"]].items():
                encoded = natural.copy()
                if name.startswith("control_"):
                    encoded[36:] = 0
                for mode in ("natural", "zero_spatial"):
                    if mode == "zero_spatial":
                        encoded[36:] = 0
                    score = score_actions(model.agent.online_net, encoded, mask)
                    if any(event["probes"][name][mode][k] != v for k,v in score.items()):
                        raise ValueError("Saved network score does not reproduce")
                    network_scores += 1
            counts = np.rint(15*np.arctanh(np.clip(natural[:12], 0, .999999))).astype(int)
            outgoing = np.rint(15*np.arctanh(np.clip(natural[28:32], 0, .999999))).astype(int)
            context = ControllerContext(event["step"], current_phase=event["phase"],
                can_switch_phase=True, is_decision_step=True, valid_action_mask=mask,
                movement_queues=dict(zip(MOVEMENT_KEYS, counts.tolist())),
                outgoing_counts=dict(zip(("north", "south", "east", "west"), outgoing.tolist())),
                extra_telemetry={SPATIAL_KEY: natural[36:].tolist()})
            for name, teacher in (("historical_mp", MaxPressureController()), ("upstream_mp", UpstreamMaxPressureController())):
                if teacher.act(natural[:28], context) != event["teacher_proposals"][name]:
                    raise ValueError("Saved teacher proposal does not reproduce")
            if "branches" in event:
                if len({b["outcome"]["arrival_trace_hash"] for b in event["branches"].values()}) != 1:
                    raise ValueError("Branch arrivals differ")
    per_seed = []
    for seed in SEEDS:
        for acting in ("control", "spatial", "teacher"):
            events = [e for row in rows if row["training_seed"] == seed and row["acting"] == acting for e in row["events"]]
            final = [e["probes"]["spatial_90"] for e in events]
            per_seed.append(dict(training_seed=seed, state_distribution=acting, gates=len(events),
                spatial_zero_changes=sum(p["natural"]["action"] != p["zero_spatial"]["action"] for p in final),
                spatial_initial_to_final_action_changes=sum(e["probes"]["spatial_initial"]["natural"]["action"] != p["natural"]["action"] for e,p in zip(events,final)),
                cross_arm_final_action_differences=sum(e["probes"]["control_90"]["natural"]["action"] != p["natural"]["action"] for e,p in zip(events,final)),
                teacher_proposal_differences=sum(e["teacher_proposals"]["historical_mp"] != e["teacher_proposals"]["upstream_mp"] for e in events),
                source_proposal_overrides=sum(e["proposal"] != e["execution"] for e in events)))
    return dict(verified=True, complete=report["complete"], sources=len(rows),
                reproduced_network_scores=network_scores, per_seed=per_seed,
                independently_rerun_source_trajectories=0,
                scope="Exact hashes, raw-summary/weight/Q refits and teacher proposal recomputation; no new traffic samples",
                input_manifest_sha256=file_hash(directory/"manifest.json"),
                input_report_sha256=file_hash(directory/"report.json"),
                verification_source_sha256=file_hash(Path(__file__)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    result = verify(args.directory)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps(result, indent=2))
