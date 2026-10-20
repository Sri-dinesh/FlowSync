#!/usr/bin/env python3
"""Read-only paired comparison on common completed validation checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_training_results import audit_run, read_json, require


def common_comparison(control_curve, release_curve):
    common = {r["checkpoint"] for r in control_curve} & {r["checkpoint"] for r in release_curve}
    require("checkpoint_initial.pt" in common, "Paired initial validation missing")
    require(any(name not in ("checkpoint_initial.pt", "checkpoint_warmup.pt") for name in common),
            "No common completed online validation; no assessable release experiment")
    chosen = [min((r for r in curve if r["checkpoint"] in common), key=lambda r: r["delay"])
              for curve in (control_curve, release_curve)]
    initial = [next(r for r in curve if r["checkpoint"] == "checkpoint_initial.pt")
               for curve in (control_curve, release_curve)]
    require(all(initial[0][k] == initial[1][k] for k in ("delay", "p95", "throughput")),
            "Paired initial metrics differ")
    return dict(common_candidates=sorted(common), initial_delay=initial[0]["delay"],
                constant=chosen[0], release=chosen[1],
                delay_saved_by_release=chosen[0]["delay"]-chosen[1]["delay"],
                delay_saved_vs_parent=initial[0]["delay"]-chosen[1]["delay"])


def compare(directory):
    batch = read_json(directory/"batch_manifest.json")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        require(all(hashlib.sha256(archive.read(k)).hexdigest() == v for k, v in batch["source_hashes"].items()),
                "Batch source archive hash mismatch")
    pairs = []
    for seed in (101, 202, 303):
        paths = [directory/f"{arm}_seed_{seed}" for arm in ("constant", "release")]
        audits = [audit_run(path) for path in paths]
        manifests = [read_json(path/"manifest.json") for path in paths]
        for manifest in manifests:
            require(manifest["parent_sha256"] == batch["parents"][str(seed)]["sha256"], "Parent hash mismatch")
            require(all(batch["source_hashes"].get(k) == v for k, v in manifest["source_hashes"].items()),
                    "Training sources differ from frozen batch")
        ignored = {"output", "demo_loss_final_weight", "demo_loss_decay_episodes"}
        require({k: v for k, v in manifests[0]["arguments"].items() if k not in ignored}
                == {k: v for k, v in manifests[1]["arguments"].items() if k not in ignored},
                "Confounded paired training arguments")
        require(manifests[0]["arguments"]["demo_loss_final_weight"] is None
                and manifests[0]["arguments"]["demo_loss_weight"] == .5
                and manifests[0]["arguments"]["demo_loss_decay_episodes"] == 0
                and manifests[1]["arguments"]["demo_loss_final_weight"] == 0
                and manifests[1]["arguments"]["demo_loss_decay_episodes"] == 60, "Unexpected paired schedules")
        pair = common_comparison(*(a["validation_curve"] for a in audits))
        arrivals = {}
        for path in paths:
            for checkpoint in pair["common_candidates"]:
                label = checkpoint.removeprefix("checkpoint_").removesuffix(".pt")
                data = read_json(path/f"validation_{label}.json")
                for row in data["rows"]:
                    key = (row["scenario"], row["seed"])
                    require(arrivals.setdefault(key, row["arrivals_hash"]) == row["arrivals_hash"],
                            "Cross-arm arrivals differ")
        pair.update(training_seed=seed, episodes_completed=[a["episodes_completed"] for a in audits],
                    stop_reasons=[a["stop_reason"] for a in audits])
        pairs.append(pair)
    return dict(pairs=pairs,
                mean_delay_constant=statistics.mean(p["constant"]["delay"] for p in pairs),
                mean_delay_release=statistics.mean(p["release"]["delay"] for p in pairs),
                mean_p95_constant=statistics.mean(p["constant"]["p95"] for p in pairs),
                mean_p95_release=statistics.mean(p["release"]["p95"] for p in pairs),
                mean_delay_saved_by_release=statistics.mean(p["delay_saved_by_release"] for p in pairs),
                mean_delay_saved_vs_parent=statistics.mean(p["delay_saved_vs_parent"] for p in pairs),
                publication_ready=False, scope="Development validation only; no automatic promotion or superiority claim")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    try:
        report = compare(args.batch)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps(dict(comparison_available=False, error=str(exc), publication_ready=False)))
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
