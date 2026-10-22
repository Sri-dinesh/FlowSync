# Action-ranking uncertainty: prediction bounds are not calibrated

Artifacts: `results/action_rank_uncertainty/audit_20261020`.
[Frozen audit protocol](../protocols/ACTION_RANK_UNCERTAINTY_PROTOCOL_20261020.md).
No models were fitted or changed; no validation/final-test results were read.

The audit uses all 226 non-parent alternatives at 104 labelled gates from 36
excluded training-probe source trajectories (traffic seed 94002). The earlier
fit seed 94001 is excluded. Branches have identical arrivals, complete action
coverage and complete 400-tick signal audits.

| Prediction target | Mean absolute prediction error | Mean bootstrap standard deviation | Actual gain at least bootstrap lower bound |
| --- | ---: | ---: | ---: |
| Delay saved (vehicle-seconds over the branch) | 51.494 | 7.270 | 54.4% |
| Throughput gain (vehicles) | 1.688 | 0.491 | 46.5% |
| Endpoint maximum-wait saving (seconds) | 9.311 | 2.948 | 60.6% |

All three bounds hold simultaneously for 24.8% of alternatives. Equal weighting
of parent/scenario/traffic clusters, with paired faults kept together, gives
similar per-target coverage: 55.7%, 46.8%, 60.5%. These rows share traffic and
are not 226 independent observations; there is just one excluded traffic seed.
The bootstrap's 10th percentile was explicitly uncalibrated, so these are
descriptive coverage rates, not a violation of an established 90% guarantee.

Spread/error Pearson associations are 0.304 for delay, 0.202 for throughput,
and 0.010 for endpoint wait. They do not demonstrate an adequately calibrated
prediction-error model. Small bootstrap spread cannot be treated as reliable
evidence that an individual proposed correction is beneficial. The ensemble
describes coefficient variation and does not include all prediction residuals.

The original selection gates remain very conservative: the mean arm changes
three labelled decisions, of which one strictly meets all realized branch
benefit criteria; the uncertainty arm changes one, which qualifies. No selected
probe action loses throughput or exceeds the specified delay/wait harm
tolerance. This very small selected sample does **not** establish that the
selected actions are unsafe, or that uncalibrated bounds alone caused the
previous full-run performance failure.

Only 104 of 583 recorded parent decision gates have branch labels (17.8%),
at ticks 201–781. The original three-gate sampling rule and single fit traffic
seed limit data coverage. The experimental correction runs at every gate.
This audit measures a limitation; it does not prove that more data alone will
produce superior control.

## Implemented next step, not yet a completed experiment

`collect_action_rank_dataset.py` collects a broader role-separated dataset
under the [new protocol](../protocols/ACTION_RANK_DATA_PROTOCOL_20261020.md):

- Six independent fitting traffic seeds.
- Ten separate calibration traffic seeds.
- Two further excluded training-probe traffic seeds.
- All three parents, six training templates and both sensing conditions.
- Three outcome-blind sampled eligible gates per source, instead of the first
  three spaced gates after tick 200.
- Separate role files, immutable checkpoint/source provenance, paired branches,
  per-tick signal checks and exact unbranched/branched source equality.

Total: 648 source trajectories, with two source passes each. Still no
validation/test access, fitting, automatic promotion or real-world claim.
The last 400 ticks remain ineligible because a complete branch horizon is
required, and states still follow the parent rather than the corrected policy.
The future fitting/calibration method must be fixed before inspecting these
role-specific outcomes; calibration must cluster by whole traffic seed, not
treat paired faults as independent samples.

Run from the project root:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u \
  research/collect_action_rank_dataset.py \
  results/research_training/update_pressure_5qyi9cmv \
  --output "results/action_rank_dataset/broader_$(date -u +%Y%m%dT%H%M%SZ)" \
  --max-wall-seconds 3300
```

The cooperative budget is 55 minutes, not a promise of completion time.
Inspect `report.json`: only `full_dataset_complete: true` establishes the full
dataset completed. Budget stops retain partial role files and exit nonzero;
do not fit from an incomplete dataset or overwrite previous outputs.

## Verification

50 targeted tests passed, including the unchanged original branch sampling
path, deterministic outcome-blind sampling, role separation, explicit gate
validation, source-trajectory equality, paired branches, incomplete/unsafe
evidence rejection, and synthetic overconfident-but-wrong ensemble detection.

A real parent-101 smoke completed at
`results/action_rank_dataset/smoke_20261020`: one fitting source, sampled ticks
213/741/781, ten branches, 5,200 labelled-source/branch signal samples and zero
measured violations. It explicitly reports `full_dataset_complete: false`
and `model_trained: false`. It is mechanics evidence only.

Audit metrics independently recomputed from raw prediction rows; input,
checkpoint, archived-source and smoke output hashes verified.
`git diff --check` passed. Original models and website defaults remain unchanged.
The requested strong-baseline superiority/research-readiness is not achieved.
