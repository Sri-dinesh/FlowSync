"""Dispatch strict saved-panel verification to its recorded Python runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULES = dict(sumo_history_v1="research.pilots.run_sumo_history_panel",
               sumo_switching_v1="research.pilots.run_sumo_switching_panel",
               sumo_service_ledger_panel_v1="research.pilots.run_sumo_service_ledger_panel")


def select_interpreter(recorded_version, preferred=None):
    if not isinstance(recorded_version,str) or not recorded_version:
        raise ValueError("Manifest has no recorded Python version")
    candidates = [Path(preferred)] if preferred else [Path(sys.executable),ROOT/"results/runtime/sumo_1_24_0/bin/python"]
    for candidate in candidates:
        if not candidate.is_file(): continue
        if candidate.resolve()==Path(sys.executable).resolve():
            version = sys.version
        else:
            try:
                result = subprocess.run([str(candidate),"-c","import sys; print(sys.version)"],
                    cwd=ROOT,capture_output=True,text=True,check=False)
            except OSError:
                continue
            if result.returncode: continue
            version = result.stdout.strip()
        if version==recorded_version: return candidate
    raise ValueError("No interpreter matches the recorded Python version. Supply --interpreter with the producer environment: "+recorded_version)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(directory, interpreter=None, output=None):
    directory = Path(directory).resolve()
    if output is not None:
        output = Path(output)
        if output.exists() or output.is_symlink(): raise FileExistsError("Preserve existing verification receipt")
        if any((p/"manifest.json").exists() or (p/"report.json").exists() for p in output.resolve().parents):
            raise ValueError("Receipt must be outside frozen evidence directories")
    manifest_path,report_path = directory/"manifest.json",directory/"report.json"
    before = {p.name:file_hash(p) for p in (manifest_path,report_path)}
    manifest = json.loads(manifest_path.read_text()); report = json.loads(report_path.read_text())
    version = manifest["protocol"]["version"]
    if version not in MODULES: raise ValueError("Unsupported frozen panel protocol")
    if report.get("complete") is not True: raise ValueError("Source collection is incomplete")
    selected = select_interpreter(manifest["runtime"]["python_version"],interpreter)
    command = [str(selected),"-m",MODULES[version],"--verify",str(directory)]
    result = subprocess.run(command,cwd=ROOT,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},
                            capture_output=True,text=True,check=False)
    if result.returncode:
        raise ValueError("Recorded-runtime verification failed:\n"+result.stderr.strip())
    try: proof = json.loads(result.stdout)
    except (ValueError,TypeError) as exc: raise ValueError("Verifier did not return a JSON receipt") from exc
    if not isinstance(proof,dict): raise ValueError("Verifier receipt must be a JSON object")
    expected = dict(verified=True,smoke=manifest["configuration"]["smoke"],
        scientific_panel_complete=report["scientific_panel_complete"],runs=len(manifest["planned_jobs"]),
        signal_samples=sum(j["steps"] for j in manifest["planned_jobs"]),sessions=len(report["sessions"]),
        completed_episode_checkpoints=True,independently_rerun_trajectories=0,publication_ready=False)
    if any(proof.get(k)!=v for k,v in expected.items()):
        raise ValueError("Verifier receipt does not match frozen coverage/scope")
    if any(file_hash(directory/name)!=value for name,value in before.items()):
        raise ValueError("Source manifest/report changed during verification")
    receipt = dict(**proof,verification_interpreter=str(selected.resolve()),
        verification_python_version=manifest["runtime"]["python_version"],source_python_matches=True,
        requesting_python_version=sys.version,launcher_sha256=file_hash(Path(__file__)),
        verification_module=MODULES[version],source_directory=str(directory),source_header_sha256=before,
        native_traffic_runs=0,scope="Strict original source/trace/summary verifier executed under the recorded Python version. No tolerance, report rewriting or new native traffic.")
    if output is not None:
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("x") as stream:
            json.dump(receipt,stream,indent=2,allow_nan=False); stream.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    parser.add_argument("--interpreter",type=Path)
    parser.add_argument("--output",type=Path,help="New receipt file outside all frozen inputs")
    args = parser.parse_args()
    try: result = verify(args.directory,args.interpreter,args.output)
    except (ValueError,OSError) as exc: parser.exit(1,str(exc)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__": main()
