"""Validate frozen parents and create a new, provenance-recorded pilot directory."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT/"results/research_training/pilot_v5_kbW0lsY3"


def document_path(name):
    """Resolve grouped research docs, retaining custom fixture/launcher paths."""
    original = ROOT / "research" / name
    if original.is_file():
        return original
    matches = list((ROOT / "research/docs").rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one research document named {name}")
    return matches[0]


def prepare(prefix="margin_release_", launcher="run_margin_release_pilot.sh",
            protocol="MARGIN_RELEASE_PROTOCOL_20261016.md", extra_sources=()):
    parents = {}
    for seed in (101, 202, 303):
        selection = PILOT/f"seed_{seed}/selection.json"
        choice = json.loads(selection.read_text())
        checkpoint = Path(choice["path"]).resolve()
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != choice["sha256"]:
            raise ValueError(f"Selected parent changed for seed {seed}")
        if choice.get("evaluation_controller") != "d3qn_shield":
            raise ValueError("Expected shield-selected v5 parents")
        parents[seed] = dict(path=str(checkpoint), sha256=choice["sha256"],
                             selection_sha256=hashlib.sha256(selection.read_bytes()).hexdigest())
    output = Path(tempfile.mkdtemp(prefix=prefix, dir=ROOT/"results/research_training"))
    sources = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    sources += [ROOT/"research"/launcher, document_path(protocol)]
    sources += [document_path(name) for name in extra_sources]
    sources += sorted((ROOT/"research/scenarios").glob("train/*.yaml"))
    sources += sorted((ROOT/"research/scenarios").glob("validation/*.yaml"))
    manifest = dict(parents=parents, source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in sources}, publication_ready=False)
    (output/"batch_manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            archive.write(source, str(source.relative_to(ROOT)))
    for seed, parent in parents.items():
        (output/f"parent_{seed}.txt").write_text(parent["path"]+"\n")
    return output


if __name__ == "__main__":
    print(prepare())
