"""Test pilot budgets and shell orchestration without launching long training."""
import json
import hashlib
from pathlib import Path
import subprocess
from types import SimpleNamespace
import zipfile

import pytest
import torch

from research.compare_temporal_pilot import ARMS, EXPECTED, SEEDS, compare, common_online_labels, continuation_screen
from research.train_policy import BudgetExceeded, fixed_episode_updates, HP

ROOT = Path(__file__).resolve().parents[2]


def test_comparison_uses_latest_common_episode_not_best_or_longest_run():
    curves = [[{"checkpoint": f"checkpoint_{s}.pt"} for s in ("initial", "warmup", "30", "60", "90")]
              for _ in range(6)]
    curves[-1].pop()
    assert common_online_labels(curves) == ["checkpoint_30.pt", "checkpoint_60.pt"]
    curves[-1] = curves[-1][:2]
    with pytest.raises(ValueError, match="No common"):
        common_online_labels(curves)


def test_screen_needs_all_criteria_not_just_one_good_seed():
    pairs = [dict(control=dict(delay=10., p95=40., throughput=90., signal_violations=0),
                  temporal=dict(delay=9.7, p95=39., throughput=90., signal_violations=0)) for _ in range(3)]
    assert continuation_screen(pairs)["continue_to_expanded_validation"]
    pairs[0]["temporal"]["delay"] = 10.2
    pairs[1]["temporal"]["delay"] = 8.
    screen = continuation_screen(pairs)
    assert screen["checks"]["mean_delay_improves_two_percent"]
    assert not screen["continue_to_expanded_validation"]
    pairs[0]["temporal"]["delay"] = 9.7
    pairs[0]["temporal"]["signal_violations"] = 1
    assert not continuation_screen(pairs)["continue_to_expanded_validation"]


def fake_agent(size=HP.BATCH_SIZE):
    class Replay:
        def __len__(self):
            return size

        def sample(self, batch_size):
            assert batch_size == HP.BATCH_SIZE
            return "batch"

    agent = SimpleNamespace(replay_buffer=Replay(), step_count=0, syncs=0)

    def step(batch):
        assert batch == "batch"
        agent.step_count += 1
        return .25, {}

    def sync():
        agent.syncs += 1

    agent.train_step, agent.sync_target_network = step, sync
    return agent


def test_fixed_optimizer_budget_and_target_schedule():
    agent = fake_agent()
    stages = []
    budget = SimpleNamespace(check=stages.append)
    assert fixed_episode_updates(agent, 5, 2, budget) == .25
    assert agent.step_count == 5 and agent.syncs == 2
    assert stages == ["online_updates"] * 5
    with pytest.raises(ValueError, match="Insufficient replay"):
        fixed_episode_updates(fake_agent(0), 5, 2, budget)


def test_fixed_updates_honor_budget_and_reject_nonfinite_loss():
    agent = fake_agent()

    def check(stage):
        if agent.step_count == 2:
            raise BudgetExceeded(stage)

    with pytest.raises(BudgetExceeded, match="online_updates"):
        fixed_episode_updates(agent, 5, 2, SimpleNamespace(check=check))
    assert agent.step_count == 2
    agent.train_step = lambda _: (float("nan"), {})
    with pytest.raises(ValueError, match="Non-finite"):
        fixed_episode_updates(agent, 1, 2, SimpleNamespace(check=lambda _: None))


@pytest.mark.parametrize("worker_exit", [0, 7])
def test_launcher_passes_matched_flags_and_stops_after_failed_wave(tmp_path, worker_exit):
    executable = tmp_path / "server/venv/bin/python"
    executable.parent.mkdir(parents=True)
    research = tmp_path / "research"
    research.mkdir()
    (research / "train_policy.py").touch()
    batch = tmp_path / "batch with spaces"
    batch.mkdir()
    for seed in (101, 202, 303):
        (batch / f"parent_{seed}.txt").write_text(f"/parent with spaces/{seed}.pt\n")
    executable.write_text(f'''#!/bin/sh
if [ "$1" = "research/prepare_temporal_pilot.py" ]; then
  printf '%s\\n' '{batch}'
  exit 0
fi
printf '%s\\n' "$@"
exit {worker_exit}
''')
    executable.chmod(0o700)
    result = subprocess.run(["bash", str(ROOT / "research/run_temporal_pilot.sh")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == int(worker_exit != 0)
    arms = ["control", "temporal"] if not worker_exit else ["control"]
    for arm in arms:
        for seed in (101, 202, 303):
            args = (batch / f"{arm}_seed_{seed}.log").read_text().splitlines()
            for key, value in (("--episodes", "90"), ("--updates-per-episode", "32"),
                               ("--max-wall-seconds", "360"), ("--seed", str(seed)),
                               ("--checkpoint", f"/parent with spaces/{seed}.pt"),
                               ("--observation-version", "v8_64dim_temporal" if arm == "temporal" else "v8_64dim_zero_history")):
                assert args[args.index(key)+1] == value
            assert "--expand-v7-parent" in args and "--train-with-shield" in args
            assert "--demo-loss-final-weight" not in args
    if worker_exit:
        assert not list(batch.glob("temporal_seed_*.log"))


@pytest.fixture
def paired_bundle(tmp_path):
    """Synthetic artifact fixture, not performance evidence or a real network."""
    source = b"# fixture"
    sources = {"fixture.py": hashlib.sha256(source).hexdigest()}
    with zipfile.ZipFile(tmp_path / "source_snapshot.zip", "w") as archive:
        archive.writestr("fixture.py", source)
    parents = {}
    for seed in SEEDS:
        weights = {"feature_layer.0.weight": torch.ones(2, 36), "fixture.bias": torch.zeros(2)}
        parent = tmp_path / f"parent_{seed}.pt"
        torch.save(dict(online_net=weights), parent)
        parents[str(seed)] = dict(path=str(parent), sha256=hashlib.sha256(parent.read_bytes()).hexdigest())
        for arm, version in ARMS.items():
            path = tmp_path / f"{arm}_seed_{seed}"
            path.mkdir()
            args = dict(EXPECTED, output=str(path), seed=seed, checkpoint=str(parent), observation_version=version)
            manifest = dict(arguments=args, parent_sha256=parents[str(seed)]["sha256"], source_hashes=sources,
                test_access=False, selection_controller="d3qn_shield", training_scenarios={"train_fixture": "fixture"},
                validation_scenarios={"val_fixture": "fixture"}, validation_seeds=[21001, 21002],
                validation_faults=[dict(name="clean")], reward_version="fixture", shield_enabled=True,
                fallback_enabled=False, online_update_schedule="fixed_after_complete_episode",
                parent_initialization="zero_expand_v7_to_v8", observation_schema="fixture")
            (path / "manifest.json").write_text(json.dumps(manifest))
            best = None
            for label in ("initial", "warmup", "30"):
                cp = path / f"checkpoint_{label}.pt"
                expanded = dict(weights, **{"feature_layer.0.weight": torch.cat((weights["feature_layer.0.weight"], torch.zeros(2, 28)), dim=1)})
                torch.save(dict(online_net=expanded, total_train_steps=960 if label == "30" else 0,
                                obs_version=version), cp)
                digest = hashlib.sha256(cp.read_bytes()).hexdigest()
                delay = 9.7 if arm == "temporal" and label == "30" else 10.
                rows = [dict(controller="d3qn_shield", scenario="val_fixture", seed=s, fault="clean",
                    delay=delay, p95=40., throughput=90., conflicts=0, clearance_violations=0,
                    starvations=0, checkpoint_hash=digest, arrivals_hash=f"traffic_{s}",
                    safety_samples=100, expected_safety_samples=100) for s in (21001, 21002)]
                (path / f"validation_{label}.json").write_text(json.dumps(dict(complete=True,
                    selection_controller="d3qn_shield", score=delay, rows=rows)))
                if best is None or delay < best["score"]:
                    best = dict(path=str(cp), score=delay, sha256=digest, evaluation_controller="d3qn_shield")
            (path / "selection.json").write_text(json.dumps(best))
            (path / "summary.json").write_text(json.dumps(dict(best=best, training_seed=seed,
                stop_reason="wall_clock_budget", episodes_completed=30)))
            (path / "training.jsonl").write_text("\n".join(json.dumps(dict(episode=e, online_updates=32,
                total_updates=32*e, loss=.1)) for e in range(1, 31)))
    (tmp_path / "batch_manifest.json").write_text(json.dumps(dict(parents=parents, source_hashes=sources)))
    return tmp_path


def test_compare_audits_all_six_runs_and_reports_prespecified_checkpoint(paired_bundle):
    report = compare(paired_bundle)
    assert report["comparison_available"] and not report["publication_ready"]
    assert len(report["completed_runs"]) == 6
    assert report["primary"]["checkpoint"] == "checkpoint_30.pt"
    assert report["primary"]["continue_to_expanded_validation"]
    assert len(report["primary"]["pairs"]) == 3


def test_compare_rejects_unequal_updates(paired_bundle):
    path = paired_bundle / "temporal_seed_202/training.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[5]["online_updates"] = 33
    path.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match="optimizer budget"):
        compare(paired_bundle)


def test_compare_rejects_missing_signal_coverage(paired_bundle):
    path = paired_bundle / "temporal_seed_303/validation_30.json"
    data = json.loads(path.read_text())
    data["rows"][0]["safety_samples"] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="signal audit"):
        compare(paired_bundle)
