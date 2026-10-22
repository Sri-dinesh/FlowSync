# Research workflow

Headless training, paired evaluation, synthetic perception faults, diagnostics
and evidence export for FlowSync's custom single-intersection simulator.

## Read first

- [Current research status](RESEARCH_STATUS.md): completed outcomes, failures and open requirements.
- [Evaluation audit](EVALUATION_AUDIT.md): why earlier checkpoint-free comparisons were invalid.
- [Documentation index](docs/README.md): dated protocols, findings, audits and manuscript drafts.
- [Application/research boundaries](../docs/architecture.md): shared components do not imply website parity.

Reliable superiority over Max-Pressure and useful added uncertainty/fallback
benefit remain unestablished. Completed failed recipes must not be repeated,
expanded or promoted just because their historical launcher is still present.

## Install and inspect

From the repository root, using Python 3.11 for a fresh environment:

```bash
python3.11 -m venv server/.venv
server/.venv/bin/python -m pip install -r research/requirements.txt -r server/requirements-dev.txt
server/.venv/bin/python research/train_policy.py --help
server/.venv/bin/python research/evaluate_replicates.py --help
```

Use an existing environment explicitly when reproducing its recorded artifacts.
Do not install over a frozen environment or mistake installation defaults for
the dependencies used in an earlier run. Most audit tools do not require
Supabase; API startup has separate private configuration requirements.

## Code layout

| Location | Responsibility |
| --- | --- |
| `*.py`, `run_*.sh` | Stable training/evaluation/audit entry points and helpers |
| `experiments/` | Shared execution engine, observed runtime and benchmark helpers |
| `noise/`, `observation/` | Synthetic sensor boundary and observation construction |
| `scenarios/`, `configs/`, `manifests/` | Scenario definitions and declared experiment inputs |
| `training/`, `uncertainty/`, `calibration/` | Domain randomization, lineage and fitted models |
| `analysis/`, `profiling/`, `cv/` | Analysis, profiling and camera-surrogate utilities |
| `docs/` | Grouped experiment documentation; original filenames retained |

The flat Python entry points are intentional compatibility interfaces. Moving
them would break recorded commands/imports. Shared implementation belongs in
the existing subpackages; new unrelated utilities should not accumulate at
the repository root.

## Reproducibility rules

1. Freeze the protocol, scenario/demand/fault configuration, source and compatible
   parent/checkpoint hashes before looking at outcomes.
2. Separate policy-training replicates from traffic seeds and development
   observations from final evaluation. Inspected final panels are consumed.
3. Keep all training replicates, the fixed endpoint, full checkpoint curve and
   unfavorable cases. Give classical controllers matched sensing/supervision.
4. Use delivered observations for proposals/masks/supervision; truth is reserved
   for metrics and training rewards. Preserve the physical signal FSM.
5. Write new output directories and preserve manifests, raw measurements,
   source archives, signal audits and hashes. Never overwrite old experiments.
6. Distinguish stopped delay per arrived vehicle, within-run percentiles, branch
   vehicle-seconds, prediction error and optimizer losses. They are different units.

Use `audit_training_results.py` and the matching `compare_*` tool to audit a
recorded batch; use `build_paper_evidence.py` for compatible provenance-checked
evaluation exports. Recent teacher diagnostics have their own
`export_teacher_evidence.py`. Export compatibility is experiment-specific.

## Artifact and historical-code policy

Recorded checkpoints/results are local, not bundled in a fresh clone. Consult
[the artifact policy](../results/README.md). A missing artifact is not permission
to substitute an untrained network. Archived source documents retain their old
paths inside the corresponding ZIP; current documentation is under `docs/`.

Older exploratory runners remain for code/test compatibility, but are not
independent confirmation or a replacement for checkpoint-explicit evaluation.
`scripts/reproduce_all.py` and hard-coded figure regeneration are retired.
Neither source organization nor passing tests establishes paper/deployment readiness.
