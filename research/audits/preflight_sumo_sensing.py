"""Check full-study readiness without creating outputs or running traffic."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from research.experiments.sumo_sensing import PLAN, configuration, plans
from research.pilots.run_sumo_sensing_panel import ROOT, SOURCES, file_hash, runtime, verify


def preflight(mechanics, output):
    mechanics, output = Path(mechanics), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Choose a new full-study directory; preserve existing evidence")
    if output.resolve().is_relative_to(mechanics.resolve()):
        raise ValueError("Full-study output must be outside the mechanics evidence")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--", *SOURCES], cwd=ROOT, text=True
    ).strip():
        raise ValueError("Commit the executable protocol before collection")

    checked = verify(mechanics)
    if not checked["smoke"]:
        raise ValueError("Mechanics evidence must be a verified smoke")
    proof = json.loads((mechanics / "manifest.json").read_text())
    binaries, environment = runtime()
    if proof["runtime"] != environment:
        raise ValueError("Mechanics runtime differs; use the preserved SUMO interpreter")

    cfg = configuration()
    scheduled = plans()
    run_count = len(scheduled) * len(PLAN["controllers"]) * len(PLAN["presets"]) * cfg["repeats"]
    command = ["env", "PYTHONDONTWRITEBYTECODE=1", sys.executable,
               "-m", "research.pilots.run_sumo_sensing_panel"]
    return dict(
        ready_for_user_run=True,
        collection_started=False,
        traffic_trajectories_run=0,
        working_directory=str(ROOT),
        mechanics_directory=str(mechanics.resolve()),
        mechanics_report_sha256=file_hash(mechanics / "report.json"),
        mechanics_verification=checked,
        executable_sources_match_mechanics=True,
        executable_source_count=len(SOURCES),
        runtime_matches_mechanics=True,
        runtime=environment,
        binaries=binaries,
        output_directory=str(output.resolve()),
        planned_traffic_seeds=len(scheduled),
        planned_runs=run_count,
        planned_signal_samples=run_count * cfg["steps"],
        episode_seconds=cfg["steps"] * PLAN["dt_s"],
        cooperative_collection_cap_seconds=cfg["cap_seconds"],
        collection_command=shlex.join(command + ["--mechanics", str(mechanics.resolve()),
                                                "--output", str(output.resolve())]),
        verification_command=shlex.join(command + ["--verify", str(output.resolve())]),
        scope="Readiness for the frozen study only. Collection repeats its own source/runtime gates. "
              "No traffic results, controller promotion or publication readiness are established."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Proposed collection directory; preflight does not create it")
    args = parser.parse_args()
    print(json.dumps(preflight(args.mechanics, args.output), indent=2))


if __name__ == "__main__":
    main()
