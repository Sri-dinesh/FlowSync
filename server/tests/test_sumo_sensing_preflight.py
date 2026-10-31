"""Preflight must preserve evidence and cannot start a collection."""
from copy import deepcopy
import json
import shlex

import pytest

from research.audits import preflight_sumo_sensing as tool


@pytest.fixture
def ready(tmp_path, monkeypatch):
    mechanics = tmp_path / "mechanics evidence"
    mechanics.mkdir()
    environment = dict(python_version="fixture", versions={"sumo": "fixture"})
    (mechanics / "manifest.json").write_text(json.dumps(dict(runtime=environment)))
    (mechanics / "report.json").write_text('{"scope":"synthetic preflight fixture"}\n')
    monkeypatch.setattr(tool, "verify", lambda _: dict(verified=True, smoke=True))
    monkeypatch.setattr(tool, "runtime", lambda: ({"sumo": "fixture", "netconvert": "fixture"}, deepcopy(environment)))
    monkeypatch.setattr(tool.subprocess, "check_output", lambda *args, **kwargs: "")
    return mechanics, tmp_path / "full study"


def test_readiness_describes_frozen_budget_and_commands_without_writing(ready, monkeypatch):
    mechanics, output = ready
    before = {p.name: p.read_bytes() for p in mechanics.iterdir()}
    monkeypatch.setattr(tool, "runtime", lambda: ({}, json.loads((mechanics / "manifest.json").read_text())["runtime"]))
    report = tool.preflight(mechanics, output)
    assert report["ready_for_user_run"] and not report["collection_started"]
    assert report["traffic_trajectories_run"] == 0
    assert report["planned_traffic_seeds"] == 6 and report["planned_runs"] == 72
    assert report["planned_signal_samples"] == 129600 and report["episode_seconds"] == 180
    assert report["cooperative_collection_cap_seconds"] == 900
    collect = shlex.split(report["collection_command"])
    check = shlex.split(report["verification_command"])
    assert collect[collect.index("--mechanics") + 1] == str(mechanics.resolve())
    assert collect[collect.index("--output") + 1] == str(output.resolve())
    assert check[check.index("--verify") + 1] == str(output.resolve())
    assert "--output" not in check and "--smoke" not in collect
    assert not output.exists()
    assert before == {p.name: p.read_bytes() for p in mechanics.iterdir()}


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
def test_existing_output_is_preserved_before_reading_mechanics(ready, monkeypatch, kind):
    mechanics, output = ready
    if kind == "directory":
        output.mkdir()
    elif kind == "file":
        output.write_text("preserve")
    else:
        output.symlink_to(output.parent / "absent")
    monkeypatch.setattr(tool, "verify", lambda _: pytest.fail("must refuse before reading mechanics"))
    with pytest.raises(FileExistsError, match="preserve existing evidence"):
        tool.preflight(mechanics, output)
    if kind == "file":
        assert output.read_text() == "preserve"
    elif kind == "dangling_symlink":
        assert output.is_symlink()
    else:
        assert output.is_dir()


def test_output_cannot_be_nested_in_mechanics_evidence(ready):
    mechanics, _ = ready
    with pytest.raises(ValueError, match="outside the mechanics"):
        tool.preflight(mechanics, mechanics / "new")


def test_dirty_executable_protocol_refuses_before_verification(ready, monkeypatch):
    mechanics, output = ready
    monkeypatch.setattr(tool.subprocess, "check_output", lambda *args, **kwargs: " M frozen_source.py\n")
    monkeypatch.setattr(tool, "verify", lambda _: pytest.fail("dirty protocol must refuse first"))
    with pytest.raises(ValueError, match="Commit the executable protocol"):
        tool.preflight(mechanics, output)
    assert not output.exists()


def test_changed_runtime_cannot_reuse_old_smoke(ready, monkeypatch):
    mechanics, output = ready
    monkeypatch.setattr(tool, "runtime", lambda: ({}, {"different": "runtime"}))
    with pytest.raises(ValueError, match="runtime differs"):
        tool.preflight(mechanics, output)
    assert not output.exists()


def test_full_collection_cannot_replace_mechanics_smoke(ready, monkeypatch):
    mechanics, output = ready
    monkeypatch.setattr(tool, "verify", lambda _: dict(verified=True, smoke=False))
    with pytest.raises(ValueError, match="verified smoke"):
        tool.preflight(mechanics, output)


def test_failed_saved_evidence_verification_propagates(ready, monkeypatch):
    mechanics, output = ready
    def reject(_):
        raise ValueError("Historical replay requires the archived executable sources")
    monkeypatch.setattr(tool, "verify", reject)
    with pytest.raises(ValueError, match="archived executable sources"):
        tool.preflight(mechanics, output)
    assert not output.exists()
