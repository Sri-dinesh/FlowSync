# Utility scripts

Run utilities from the repository root using the configured Python environment.
Inspect options before downloads, training or exports.

| Script | Purpose |
| --- | --- |
| `download_datasets.py` | Optional third-party detector datasets |
| `merge_datasets.py` | Dataset preparation |
| `train_yolo.py` | Optional detector training |
| `validate_model.py` | Detector evaluation |
| `export_model.py` | Detector export |
| `calibrate_flow.py` | Camera/flow calibration utilities |
| `start_server.ps1`, `start_server.bat` | Windows API startup helpers |
| `check_repository.py` | Maintained docs, configuration and hygiene checks |

`reproduce_all.py` is retired: its old quick/final suite was not the audited,
checkpoint-explicit reproduction workflow. Use [research](../research/README.md).
The retired command must not overwrite preserved historical outputs.
