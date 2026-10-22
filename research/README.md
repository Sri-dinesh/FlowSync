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
server/.venv/bin/python -m research --help
server/.venv/bin/python -m research train --help
server/.venv/bin/python -m research evaluate --help
```

Use an existing environment explicitly when reproducing its recorded artifacts.
Do not install over a frozen environment or mistake installation defaults for
the dependencies used in an earlier run. Most audit tools do not require
Supabase; API startup has separate private configuration requirements.

## Code layout

| Location | Responsibility |
| --- | --- |
| `training/` | Research trainer, parent initialization, demand randomization and lineage |
| `evaluation/` | Checkpoint-explicit evaluation, validation and control selection |
| `audits/` | Training, replay, observation, action and teacher diagnostics |
| `pilots/` | Bounded development pilots, preparation and matched comparators |
| `pilots/launchers/` | Historical user-run shell recipes; check completed outcomes before use |
| `datasets/` | Action-label collection code; generated data belongs in `results/` |
| `policies/` | Research correction models and observed-input baselines |
| `calibration/` | Calibration/fitting tools and digital-twin calibration helpers |
| `evidence/` | Provenance-checked tables, figures and evidence exports |
| `experiments/` | Shared execution engine, observed runtime, branching and shield adapter |
| `noise/`, `observation/` | Synthetic sensor boundary and observation construction |
| `scenarios/`, `manifests/` | Scenario definitions, shared loader and declared experiment inputs |
| `uncertainty/` | Runtime uncertainty estimation and fallback-benefit models |
| `analysis/` | Statistical summaries, feature comparisons and reporting |
| `profiling/`, `cv/` | Profiling and camera-surrogate utilities; optional vision dependencies may be needed |
| `legacy/` | Older exploratory runners, reference configuration and retired figure commands |
| `docs/` | Grouped experiment documentation; original filenames retained |

Run commands from the repository root. The main tools are available through
`python -m research`; other tools use their full package path, for example
`python -m research.audits.audit_teacher_alignment --help`. Package initializers
do not load models or optional vision dependencies.

The former flat scripts now live in the packages above. Live imports, shell
recipes and documented commands use their new locations. Commands copied from
an old saved source snapshot use that snapshot's layout; its archived paths and
hashes have not been rewritten. Exact live-source hash checks still reject a
different implementation, including one changed by reorganization.

## Common commands

These commands inspect usage or existing artifacts; none starts training:

```bash
server/.venv/bin/python -m research train --help
server/.venv/bin/python -m research validate --help
server/.venv/bin/python -m research export-paper --help
server/.venv/bin/python -m research compare-spatial \
  results/research_training/spatial_v9_k2bg79oc
```

Use `server/venv/bin/python` explicitly if reproducing the existing environment.
The saved spatial recipe failed its continuation screen; its launcher is
retained for provenance and must not be rerun as a proposed improvement.

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

Use `python -m research audit-training` and the matching `pilots.compare_*`
module to audit a recorded batch. `python -m research export-paper` produces
compatible provenance-checked evaluation exports; recent teacher diagnostics
use `python -m research export-teachers`. Export compatibility is
experiment-specific.

## Artifact and historical-code policy

Recorded checkpoints/results are local, not bundled in a fresh clone. Consult
[the artifact policy](../results/README.md). A missing artifact is not permission
to substitute an untrained network. Archived source documents retain their old
paths inside the corresponding ZIP; current documentation is under `docs/`.

Older exploratory runners are grouped in `legacy/` for inspection and tests, but are not
independent confirmation or a replacement for checkpoint-explicit evaluation.
`scripts/reproduce_all.py` and the figure commands in `legacy/` are retired.
Neither source organization nor passing tests establishes paper/deployment readiness.
