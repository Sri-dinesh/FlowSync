"""Load a scenario by manifest ID or explicit YAML path."""
import json
from pathlib import Path

from research.scenarios.scenario_schema import ScenarioConfig

SCENARIOS = Path(__file__).resolve().parent


def load_scenario(identifier: str) -> ScenarioConfig:
    path = Path(identifier)
    if path.is_file():
        return ScenarioConfig.load(path)

    manifest_path = SCENARIOS / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if identifier in manifest.get("scenarios", {}):
            scenario_path = SCENARIOS.parent / manifest["scenarios"][identifier]["file"]
            if scenario_path.is_file():
                return ScenarioConfig.load(scenario_path)

    for split in ("train", "validation", "test"):
        candidate = SCENARIOS / split / f"{identifier}.yaml"
        if candidate.is_file():
            return ScenarioConfig.load(candidate)

    raise FileNotFoundError(f"Could not locate scenario '{identifier}'.")
