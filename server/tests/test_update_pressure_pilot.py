"""Integrity and launcher tests; synthetic artifacts are not performance evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
import torch

from research.pilots.compare_update_pressure_pilot import ARMS, EXPECTED, OVERRIDES, compare, screen_against
from research.training.train_policy import fixed_episode_updates
from server.tests.test_temporal_pilot import paired_bundle, fake_agent

ROOT = Path(__file__).resolve().parents[2]


def test_target_copies_have_matching_episode_positions():
    positions = []
    for arm in ARMS:
        agent = fake_agent()
        config = OVERRIDES[arm]
        copies = []
        agent.sync_target_network = lambda: copies.append(agent.step_count/config["updates_per_episode"])
        for _ in range(90):
            fixed_episode_updates(agent, config["updates_per_episode"], config["target_update"],
                                  SimpleNamespace(check=lambda _: None))
        positions.append(copies)
    assert positions[0] == positions[1] == [6.25*n for n in range(1, 15)]


def test_less_bad_than_control_is_not_a_parent_improvement():
    pairs = [dict(parent=dict(delay=10., p95=40., throughput=90.),
                  control=dict(delay=12., p95=40., throughput=90.),
                  low_updates=dict(delay=11., p95=40., throughput=90.)) for _ in range(3)]
    assert all(screen_against(pairs, "control").values())
    assert not all(screen_against(pairs, "parent").values())


@pytest.mark.parametrize("worker_exit", [0, 7])
def test_launcher_matches_budget_and_stops_on_worker_failure(tmp_path, worker_exit):
    executable = tmp_path/"server/venv/bin/python"
    executable.parent.mkdir(parents=True)
    (tmp_path/"research/training").mkdir(parents=True)
    (tmp_path/"research/training/train_policy.py").touch()
    batch = tmp_path/"batch with spaces"
    batch.mkdir()
    for seed in (101, 202, 303):
        (batch/f"parent_{seed}.txt").write_text(f"/parent with spaces/{seed}.pt\n")
    executable.write_text(f'''#!/bin/sh
if [ "$1" = "research/pilots/prepare_update_pressure_pilot.py" ]; then
  printf '%s\\n' '{batch}'
  exit 0
fi
printf '%s\\n' "$@"
exit {worker_exit}
''')
    executable.chmod(0o700)
    result = subprocess.run(["bash", str(ROOT/"research/pilots/launchers/run_update_pressure_pilot.sh")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == int(worker_exit != 0)
    for arm in (["control"] if worker_exit else ARMS):
        for seed in (101, 202, 303):
            args = (batch/f"{arm}_seed_{seed}.log").read_text().splitlines()
            for key, value in (("--episodes", "90"), ("--max-wall-seconds", "360"),
                ("--seed", str(seed)), ("--checkpoint", f"/parent with spaces/{seed}.pt"),
                ("--observation-version", "v7_36dim_observed"),
                ("--updates-per-episode", str(OVERRIDES[arm]["updates_per_episode"])),
                ("--target-update", str(OVERRIDES[arm]["target_update"]))):
                assert args[args.index(key)+1] == value
            assert "--expand-v7-parent" not in args
            assert "--train-with-shield" in args
    if worker_exit:
        assert not list(batch.glob("low_updates_seed_*.log"))


@pytest.fixture
def pressure_bundle(paired_bundle):
    """Adapt the shared synthetic audit fixture to the new predeclared design."""
    for seed in (101, 202, 303):
        (paired_bundle/f"temporal_seed_{seed}").rename(paired_bundle/f"low_updates_seed_{seed}")
        weights = torch.load(paired_bundle/f"parent_{seed}.pt", weights_only=True)["online_net"]
        for arm, version in ARMS.items():
            path = paired_bundle/f"{arm}_seed_{seed}"
            manifest = json.loads((path/"manifest.json").read_text())
            manifest["arguments"].update(EXPECTED, **OVERRIDES[arm])
            manifest["arguments"].update(output=str(path), observation_version=version)
            manifest.update(parent_initialization="same_version", observation_schema=None)
            (path/"manifest.json").write_text(json.dumps(manifest))
            best = None
            for label in ("initial", "warmup", "30", "60", "90"):
                cp = path/f"checkpoint_{label}.pt"
                torch.save(dict(online_net=weights, total_train_steps=(int(label)*OVERRIDES[arm]["updates_per_episode"]
                    if label.isdigit() else 0), obs_version=version), cp)
                digest = hashlib.sha256(cp.read_bytes()).hexdigest()
                data = json.loads((path/"validation_initial.json").read_text())
                delay = 9.7 if label.isdigit() and arm == "low_updates" else 10.
                for row in data["rows"]:
                    row.update(checkpoint_hash=digest, delay=delay)
                data["score"] = delay
                (path/f"validation_{label}.json").write_text(json.dumps(data))
                if best is None or delay < best["score"]:
                    best = dict(path=str(cp), score=delay, sha256=digest, evaluation_controller="d3qn_shield")
            (path/"selection.json").write_text(json.dumps(best))
            (path/"summary.json").write_text(json.dumps(dict(best=best, training_seed=seed,
                stop_reason="completed", episodes_completed=90)))
            rows = [dict(episode=e, scenario="train_fixture", seed=seed*1000+e, fault={"name": "clean"},
                executed_scenario=dict(split="train"), epsilon=.1, demonstration_loss_weight=.5,
                online_updates=OVERRIDES[arm]["updates_per_episode"],
                total_updates=e*OVERRIDES[arm]["updates_per_episode"], loss=.1,
                q_stats=dict(unweighted_td_loss=1., pre_clip_gradient_norm=.1,
                             importance_weight_min=.1, importance_weight_max=1., td_error_mean=2.))
                for e in range(1, 91)]
            (path/"training.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            (path/"demonstrations.jsonl").write_text("\n".join(json.dumps(dict(episode=e,
                executed_scenario=dict(split="train"))) for e in range(24)))
    return paired_bundle


def test_full_comparison_includes_parents_and_all_seeds(pressure_bundle):
    report = compare(pressure_bundle)
    assert report["primary_endpoint_complete"]
    assert report["primary"]["checkpoint"] == "checkpoint_90.pt"
    assert report["primary"]["continue_to_expanded_validation"]
    assert len(report["primary"]["pairs"]) == 3
    assert not report["common_checkpoint_curve"][0]["continue_to_expanded_validation"]
    assert not report["publication_ready"] and not report["automatic_promotion"]


@pytest.mark.parametrize("mutation,match", [
    ("target_interval", "configuration"), ("scenario", "Unpaired training"),
    ("telemetry", "Invalid learning"), ("demo", "Unpaired demonstrations"),
    ("updates", "optimizer budget"), ("safety", "signal audit")])
def test_comparison_rejects_confounds(pressure_bundle, mutation, match):
    path = pressure_bundle/"low_updates_seed_202"
    if mutation == "target_interval":
        data = json.loads((path/"manifest.json").read_text())
        data["arguments"]["target_update"] = 200
        (path/"manifest.json").write_text(json.dumps(data))
    elif mutation == "safety":
        data = json.loads((path/"validation_90.json").read_text())
        data["rows"][0]["safety_samples"] = 0
        (path/"validation_90.json").write_text(json.dumps(data))
    else:
        filename = "demonstrations.jsonl" if mutation == "demo" else "training.jsonl"
        rows = [json.loads(line) for line in (path/filename).read_text().splitlines()]
        if mutation == "scenario":
            rows[0]["seed"] += 1
        elif mutation == "telemetry":
            rows[0]["q_stats"]["unweighted_td_loss"] = float("nan")
        elif mutation == "demo":
            rows[0]["episode"] = -1
        else:
            rows[0]["online_updates"] = 32
        (path/filename).write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match=match):
        compare(pressure_bundle)


@pytest.mark.parametrize("completed", [30, 90])
def test_truncated_pilot_does_not_pass_screen(pressure_bundle, completed):
    path = pressure_bundle/"low_updates_seed_303"
    summary = json.loads((path/"summary.json").read_text())
    summary.update(stop_reason="wall_clock_budget", episodes_completed=completed)
    (path/"summary.json").write_text(json.dumps(summary))
    if completed == 30:
        # Only remove synthetic test artifacts inside pytest's temporary directory.
        for label in (60, 90):
            (path/f"validation_{label}.json").unlink()
        rows = (path/"training.jsonl").read_text().splitlines()
        (path/"training.jsonl").write_text("\n".join(rows[:30]))
    report = compare(pressure_bundle)
    assert not report["primary_endpoint_complete"]
    assert not report["primary"]["continue_to_expanded_validation"]
