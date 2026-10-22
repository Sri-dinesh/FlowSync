import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from research.training.train_policy import demonstration_weight
from research.pilots import prepare_margin_pilot
from research.pilots.compare_margin_pilot import common_comparison

ROOT = Path(__file__).resolve().parents[2]


def test_schedule_preserves_default_and_warmup_then_releases():
    assert [demonstration_weight(.5, None, 0, e) for e in (0, 1, 60, 120)] == [.5]*4
    assert [demonstration_weight(.5, 0., 60, e) for e in (0, 30, 60, 120)] == [.5, .25, 0., 0.]
    assert demonstration_weight(.5, .1, 60, 30) == pytest.approx(.3)


def test_common_comparison_does_not_reward_extra_validation_candidates():
    def candidate(label, delay):
        return dict(checkpoint=f"checkpoint_{label}.pt", delay=delay, p95=30., throughput=80.)
    control = [candidate("initial", 10.), candidate("30", 9.)]
    release = [candidate("initial", 10.), candidate("30", 9.5), candidate("60", 8.)]
    result = common_comparison(control, release)
    assert result["delay_saved_by_release"] == -.5
    assert result["release"]["checkpoint"] == "checkpoint_30.pt"
    with pytest.raises(ValueError, match="No common"):
        common_comparison(control[:1], release)
    release[0]["delay"] = 11.
    with pytest.raises(ValueError, match="initial metrics differ"):
        common_comparison(control, release)


@pytest.mark.parametrize("initial,final,decay,episode", [(-1, None, 0, 0), (.5, None, 5, 0),
    (.5, 0., 0, 0), (.5, -1., 10, 0), (.5, float("nan"), 10, 0), (.5, 0., -1, 0), (.5, 0., 10, -1)])
def test_reject_invalid_schedule(initial, final, decay, episode):
    with pytest.raises(ValueError):
        demonstration_weight(initial, final, decay, episode)


@pytest.mark.parametrize("corrupt", [False, True])
def test_preparation_checks_all_parent_hashes_before_creating_batch(tmp_path, monkeypatch, corrupt):
    pilot = tmp_path/"results/research_training/pilot_v5_kbW0lsY3"
    for seed in (101, 202, 303):
        directory = pilot/f"seed_{seed}"
        directory.mkdir(parents=True)
        checkpoint = directory/"parent.pt"
        checkpoint.write_bytes(f"parent-{seed}".encode())
        choice = dict(path=str(checkpoint), sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                      evaluation_controller="d3qn_shield")
        (directory/"selection.json").write_text(json.dumps(choice))
    if corrupt:
        checkpoint.write_bytes(b"changed")
    monkeypatch.setattr(prepare_margin_pilot, "ROOT", tmp_path)
    monkeypatch.setattr(prepare_margin_pilot, "PILOT", pilot)
    if corrupt:
        with pytest.raises(ValueError, match="parent changed"):
            prepare_margin_pilot.prepare()
        assert not list(pilot.parent.glob("margin_release_*"))
    else:
        (tmp_path/"research").mkdir()
        launchers = tmp_path/"research/pilots/launchers"
        launchers.mkdir(parents=True)
        (launchers/"run_margin_release_pilot.sh").write_text("fixture")
        (tmp_path/"research/MARGIN_RELEASE_PROTOCOL_20261016.md").write_text("fixture")
        output = prepare_margin_pilot.prepare()
        manifest = json.loads((output/"batch_manifest.json").read_text())
        assert set(manifest["parents"]) == {"101", "202", "303"}
        assert (output/"source_snapshot.zip").is_file()
        assert (output/"parent_101.txt").read_text().strip().endswith("seed_101/parent.pt")


@pytest.mark.parametrize("worker_exit", [0, 7])
def test_launcher_runs_paired_waves_with_distinct_parents(tmp_path, worker_exit):
    executable = tmp_path/"server/venv/bin/python"
    executable.parent.mkdir(parents=True)
    research = tmp_path/"research/training"
    research.mkdir(parents=True)
    (research/"train_policy.py").touch()
    batch = tmp_path/"batch with spaces"
    batch.mkdir()
    for seed in (101, 202, 303):
        (batch/f"parent_{seed}.txt").write_text(f"/checkpoint with spaces/seed_{seed}.pt\n")
    executable.write_text(f'''#!/bin/sh
if [ "$1" = "research/pilots/prepare_margin_pilot.py" ]; then
  printf '%s\\n' '{batch}'
  exit 0
fi
printf '%s\\n' "$@"
exit {worker_exit}
''')
    executable.chmod(0o700)
    result = subprocess.run(["bash", str(ROOT/"research/pilots/launchers/run_margin_release_pilot.sh")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == int(worker_exit != 0)
    for arm in (["constant", "release"] if not worker_exit else ["constant"]):
        for seed in (101, 202, 303):
            args = (batch/f"{arm}_seed_{seed}.log").read_text().splitlines()
            for flag, value in (("--checkpoint", f"/checkpoint with spaces/seed_{seed}.pt"),
                                ("--seed", str(seed)), ("--episodes", "120"),
                                ("--demo-episodes", "24"), ("--episode-steps", "1200"),
                                ("--max-wall-seconds", "300"), ("--demo-loss-weight", "0.5")):
                assert args[args.index(flag)+1] == value
            assert "--train-with-shield" in args
            assert "--skip-initial-baselines" in args
            if arm == "release":
                assert args[args.index("--demo-loss-final-weight")+1] == "0"
                assert args[args.index("--demo-loss-decay-episodes")+1] == "60"
            else:
                assert "--demo-loss-final-weight" not in args
    if worker_exit:
        assert not list(batch.glob("release_*.log"))
