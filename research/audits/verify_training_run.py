"""Verify a website training configuration/source bundle without running traffic."""
import argparse
import hashlib
import json
import pickle
from pathlib import Path
import zipfile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def verify(directory, checkpoint=None):
    root = Path(directory).resolve()
    manifest = json.loads((root/"manifest.json").read_bytes())
    if manifest.get("schema_version") != "website_training_manifest_v1":
        raise ValueError("Unsupported training manifest")
    raw = (root/"configuration.json").read_bytes()
    configuration = json.loads(raw)
    expected = manifest["configuration_sha256"]
    if digest(raw) != expected or digest(canonical(configuration)) != expected:
        raise ValueError("Training configuration hash differs")
    if configuration.get("schema_version") != "website_training_configuration_v1" or configuration["model_id"] != manifest["model_id"]:
        raise ValueError("Training configuration identity differs")
    archive = root/"source_snapshot.zip"
    if digest(archive.read_bytes()) != manifest["source_archive_sha256"]:
        raise ValueError("Source archive hash differs")
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(configuration["source_sha256"]) or len(bundle.namelist()) != len(set(bundle.namelist())):
            raise ValueError("Source archive inventory differs")
        for name,expected_source in configuration["source_sha256"].items():
            if digest(bundle.read(name)) != expected_source:
                raise ValueError(f"Source bytes differ: {name}")
    inventory = manifest.get("episode_sha256",{})
    actual = {str(path.relative_to(root)) for path in (root/"episodes").glob("*.json")}
    if actual != set(inventory):
        raise ValueError("Episode record inventory differs")
    records = {}
    for name,expected_record in inventory.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root/"episodes") or path.suffix != ".json":
            raise ValueError("Episode path leaves record directory")
        raw = path.read_bytes()
        if digest(raw) != expected_record:
            raise ValueError("Episode record hash differs")
        record = json.loads(raw)
        if record["configuration_sha256"] != expected or record["run_id"] != manifest["run_id"]:
            raise ValueError("Episode configuration identity differs")
        episode = record["episode"]
        if type(episode) is not int or episode <= 0 or episode in records or name != f"episodes/episode_{episode}.json":
            raise ValueError("Episode numbering differs")
        records[episode] = record
    checked = 0
    if checkpoint is not None:
        raw = Path(checkpoint).read_bytes()
        if not any(receipt["sha256"] == digest(raw) for receipt in manifest.get("checkpoint_receipts",{}).values()):
            raise ValueError("Checkpoint hash is not registered in this run")
        import io
        import torch
        state = torch.load(io.BytesIO(raw),map_location="cpu",weights_only=True)
        run = state["training_run"]
        if run["run_id"] != manifest["run_id"] or run["configuration_sha256"] != expected or digest(canonical(run["configuration"])) != expected:
            raise ValueError("Checkpoint training configuration differs")
        record = records[state["episode"]]
        body = {key:value for key,value in record.items() if key not in ("run_id","configuration_sha256")}
        if run["episode_configuration"] != body:
            raise ValueError("Checkpoint episode configuration differs")
        checked = 1
    return {"verified":True,"run_id":manifest["run_id"],"configuration_sha256":expected,
        "sources":len(configuration["source_sha256"]),"episode_records":len(records),"checkpoints_checked":checked,
        "configuration_unavailable_fields":configuration.get("unavailable_fields",[]),
        "independently_rerun_trajectories":0,
        "scope":"Saved configuration, source/episode hashes and optional checkpoint linkage; not control performance, deterministic replay or cloud validation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--checkpoint",type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.directory,args.checkpoint),indent=2))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,pickle.UnpicklingError,zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
