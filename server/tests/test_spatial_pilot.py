"""Synthetic audit fixtures only; these tests are not measured traffic results."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import pytest
import torch

from research.compare_spatial_pilot import ARMS, EXPECTED, checks_against, compare
from server.tests.test_temporal_pilot import paired_bundle
from server.tests.test_update_pressure_pilot import pressure_bundle

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def spatial_bundle(pressure_bundle):
    for seed in (101, 202, 303):
        (pressure_bundle / f"low_updates_seed_{seed}").rename(pressure_bundle / f"spatial_seed_{seed}")
        weights = torch.load(pressure_bundle / f"parent_{seed}.pt", weights_only=True)["online_net"]
        for arm, version in ARMS.items():
            path = pressure_bundle / f"{arm}_seed_{seed}"
            manifest = json.loads((path / "manifest.json").read_text())
            manifest["arguments"].update(EXPECTED, output=str(path), observation_version=version)
            manifest.update(parent_initialization="zero_expand_v7_to_v9", observation_schema="spatial fixture")
            (path / "manifest.json").write_text(json.dumps(manifest))
            best = None
            for label in ("initial", "warmup", "30", "60", "90"):
                cp = path / f"checkpoint_{label}.pt"
                expanded = dict(weights, **{"feature_layer.0.weight": torch.cat((weights["feature_layer.0.weight"], torch.zeros(2, 12)), 1)})
                torch.save(dict(online_net=expanded, total_train_steps=int(label)*4 if label.isdigit() else 0, obs_version=version), cp)
                digest = hashlib.sha256(cp.read_bytes()).hexdigest()
                data = json.loads((path / f"validation_{label}.json").read_text())
                for row in data["rows"]:
                    row["checkpoint_hash"] = digest
                (path / f"validation_{label}.json").write_text(json.dumps(data))
                if best is None or data["score"] < best["score"]:
                    best = dict(path=str(cp), score=data["score"], sha256=digest, evaluation_controller="d3qn_shield")
            (path / "selection.json").write_text(json.dumps(best))
            summary = json.loads((path / "summary.json").read_text())
            summary["best"] = best
            (path / "summary.json").write_text(json.dumps(summary))
            rows = [json.loads(l) for l in (path / "training.jsonl").read_text().splitlines()]
            for row in rows:
                row.update(online_updates=4, total_updates=row["episode"] * 4)
            (path / "training.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    return pressure_bundle


def test_full_spatial_comparator_validates_48_columns_and_primary(spatial_bundle):
    result = compare(spatial_bundle)
    assert result["comparison_available"] and result["primary_endpoint_complete"]
    assert result["primary"]["continue_to_expanded_validation"]
    assert not result["common_checkpoint_curve"][0]["continue_to_expanded_validation"]
    assert len(result["primary"]["pairs"]) == 3
    assert not result["publication_ready"] and not result["automatic_promotion"]


@pytest.mark.parametrize("mutation,match", [("updates", "optimizer budget"), ("seed", "Unpaired training"),
    ("demo", "Unpaired demonstrations"), ("mask_schema", "Confounded evaluation"), ("safety", "signal audit")])
def test_spatial_comparator_rejects_confounds(spatial_bundle, mutation, match):
    path = spatial_bundle / "spatial_seed_202"
    if mutation == "safety":
        target = path / "validation_90.json"
        data = json.loads(target.read_text())
        data["rows"][0]["safety_samples"] = 0
        target.write_text(json.dumps(data))
    elif mutation == "mask_schema":
        target = path / "manifest.json"
        data = json.loads(target.read_text())
        data["observation_schema"] = "different"
        target.write_text(json.dumps(data))
    else:
        target = path / ("demonstrations.jsonl" if mutation == "demo" else "training.jsonl")
        rows = [json.loads(l) for l in target.read_text().splitlines()]
        rows[0][{"updates": "online_updates", "seed": "seed", "demo": "episode"}[mutation]] = -1
        target.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match=match):
        compare(spatial_bundle)


def test_budget_stop_cannot_pass_even_at_ninety_episodes(spatial_bundle):
    target = spatial_bundle / "spatial_seed_303/summary.json"
    data = json.loads(target.read_text())
    data["stop_reason"] = "wall_clock_budget"
    target.write_text(json.dumps(data))
    result = compare(spatial_bundle)
    assert not result["primary_endpoint_complete"]
    assert not result["primary"]["continue_to_expanded_validation"]


def test_improving_degraded_control_does_not_mean_parent_gain():
    pairs = [dict(parent=dict(delay=10., p95=30., throughput=50.), control=dict(delay=12., p95=30., throughput=50.),
                  spatial=dict(delay=11., p95=30., throughput=50.)) for _ in range(3)]
    assert all(checks_against(pairs, "control").values())
    assert not all(checks_against(pairs, "parent").values())


@pytest.mark.parametrize("exit_code", [0, 7])
def test_launcher_parameters_and_failure_propagation(tmp_path, exit_code):
    executable = tmp_path / "server/venv/bin/python"
    executable.parent.mkdir(parents=True)
    (tmp_path / "research").mkdir()
    (tmp_path / "research/train_policy.py").touch()
    batch = tmp_path / "batch with spaces"
    batch.mkdir()
    for seed in (101, 202, 303):
        (batch / f"parent_{seed}.txt").write_text(f"/parent path/{seed}.pt\n")
    executable.write_text(f'''#!/bin/sh
if [ "$1" = "research/prepare_spatial_pilot.py" ]; then
  printf '%s\\n' '{batch}'
  exit 0
fi
printf '%s\\n' "$@"
exit {exit_code}
''')
    executable.chmod(0o700)
    result = subprocess.run(["bash", str(ROOT / "research/run_spatial_pilot.sh")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == int(exit_code != 0)
    for arm in (["control"] if exit_code else ARMS):
        for seed in (101, 202, 303):
            args = (batch / f"{arm}_seed_{seed}.log").read_text().splitlines()
            for key, value in (("--observation-version", ARMS[arm]), ("--episodes", "90"), ("--updates-per-episode", "4"),
                ("--target-update", "25"), ("--max-wall-seconds", "600"), ("--checkpoint", f"/parent path/{seed}.pt")):
                assert args[args.index(key) + 1] == value
            assert "--expand-v7-parent" in args and "--train-with-shield" in args
    if exit_code:
        assert not list(batch.glob("spatial_seed_*.log"))


def test_prepare_freezes_referenced_sensor_protocol(tmp_path, monkeypatch):
    from research import prepare_margin_pilot
    parent_root = tmp_path / "parents"
    for seed in (101, 202, 303):
        folder = parent_root / f"seed_{seed}"
        folder.mkdir(parents=True)
        cp = folder / "parent.pt"
        cp.write_bytes(b"synthetic checkpoint fixture")
        (folder / "selection.json").write_text(json.dumps(dict(path=str(cp),
            sha256=hashlib.sha256(cp.read_bytes()).hexdigest(), evaluation_controller="d3qn_shield")))
    (tmp_path / "results/research_training").mkdir(parents=True)
    (tmp_path / "research").mkdir()
    for name in ("launch.sh", "protocol.md", "sensor.md"):
        (tmp_path / "research" / name).write_text(name)
    monkeypatch.setattr(prepare_margin_pilot, "ROOT", tmp_path)
    monkeypatch.setattr(prepare_margin_pilot, "PILOT", parent_root)
    output = prepare_margin_pilot.prepare(launcher="launch.sh", protocol="protocol.md", extra_sources=("sensor.md",))
    manifest = json.loads((output / "batch_manifest.json").read_text())
    assert "research/sensor.md" in manifest["source_hashes"]
    with zipfile.ZipFile(output / "source_snapshot.zip") as archive:
        assert archive.read("research/sensor.md") == b"sensor.md"
