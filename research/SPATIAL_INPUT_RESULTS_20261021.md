# Spatial-input implementation, mechanics smoke and failed learning pilot

Contracts: [sensor/initialization](SPATIAL_INPUT_EXPERIMENT_PLAN_20261021.md),
[matched learning pilot](SPATIAL_PILOT_PROTOCOL_20261021.md).
Smoke: `results/research_training/spatial_smoke_20261021`.

## Implemented

- Opt-in v9 spatial and zero-spatial-control encodings, both 48 inputs; existing
  36 v7 features, masks, shield and reward remain unchanged.
- Conditional partitioned count corruption, joint frame latency/drop and lane
  swaps. Upstream observations never bypass missed detections or stale frames.
  False-positive/jitter spatial assignment and saturation assumptions are
  explicitly documented. No calibrated confidence claim is made.
- Shared training/evaluation adapter with strict missing-packet rejection.
  Checkpoint versions determine the required sensor path. Zero-expansion
  preserves parent weights; neither old checkpoints nor old results change.
- Explicit upstream-only Max-Pressure baseline, including matched shield
  evaluation. It reads only the delivered packet, never simulator truth.
- Frozen two-arm/three-parent launcher and audited episode-90 comparison.
  Control and original-parent improvements are both required; incomplete
  runs and best-seed substitution cannot pass.

Historical aggregate observation/fault behavior was independently compared
with the committed pre-change injector: 1,300 frames across all 13 presets
match exactly, including outgoing counts, arrival reports, age/drop flags and
diagnostics. The new RNG does not move the old aggregate draws.

Verification: the broader targeted regression suite passed 217 tests. After
adding a source-archive coverage test, all 11 spatial-pilot tests passed
(including that new test). Shell syntax and `git diff --check` also pass.
Existing dependency deprecation warnings remain.

## Smoke outcome — mechanics, not superiority

Both arms used parent 101, training seed 97301, the same 24 randomized
demonstration scenarios and one online episode. Each collected 317 replay
transitions and performed four updates. Collection logs are byte-identical.
Weights changed and remained finite. Added input columns stay exactly zero
in the control; spatial columns reach maximum absolute weight 0.00040116.

The 84 training-scenario evaluation runs (seed 97302; clean and mixed faults)
completed in a total smoke runtime of 263.40 seconds. All 100,800 recorded
signal samples have zero measured conflict/clearance violations. Initial
expanded models reproduce the parent's recorded delay, p95 and throughput
in every cell. Parent hash, source snapshot, all output hashes, paired arrival
hashes and independently recomputed means verify.

| Policy | Mean delay (s) | Mean within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: |
| Original parent / either initial expanded model | 7.6738 | 25.6746 | 42.25 |
| Control after four updates | 7.7011 | 24.5946 | 42.75 |
| Spatial after four updates | 7.7011 | 24.5946 | 42.75 |
| Historical Max-Pressure + shield | 8.0283 | 26.0842 | 42.92 |
| Upstream Max-Pressure + shield | 7.8158 | 24.5888 | 43.75 |

There is **no learned spatial improvement in this smoke**. Both trained arms
have identical recorded performance and slightly greater mean delay than the
parent. Their weights differ; equal metrics are not evidence that one model
was silently reused. Baseline rankings on one training seed are not fresh
comparative evidence or publication-readiness claims. No model is promoted.

## Completed learning screen — failed (verified 2026-10-22)

Artifact: `results/research_training/spatial_v9_k2bg79oc/comparison.json`.
Independent recomputation matches the saved report exactly. All six runs finish
90 online episodes, 24 demos and 360 optimizer updates with no budget stops.
The fixed episode-90 endpoint retains all three training replicates and the
original parents; selection of a better earlier checkpoint cannot replace it.

| Configuration | Mean delay (s) | Mean within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: |
| Original parents | 10.841389 | 37.035417 | 89.472222 |
| Retrained zero-spatial control | 10.783722 | 39.115139 | 89.972222 |
| Spatial-input learner | 10.840583 | 37.775694 | 89.694444 |

Spatial delay is 0.5273% worse than control and 0.00743% better than parents,
effectively unchanged at this descriptive scale. Against control, seed 101
improves 1.904%, seed 202 worsens 0.857%, and seed 303 worsens 2.706%.
The >=2% aggregate gain against both references fails, as do the per-seed
regression guard, p95 versus parents and throughput versus control. All
evaluated completed candidates have zero measured signal violations.

`comparison_available` and `primary_endpoint_complete` are true;
`primary.continue_to_expanded_validation`, `publication_ready` and
`automatic_promotion` are false. Comparator/process status zero means the
execution and audit succeeded, not that the controller improved. Reused
development scenarios/seeds do not establish independent generalization.

**Stop this recipe: do not rerun, expand or promote it.** The next step is a
bounded training-only audit of input use and action choice, not more episodes.
No final-test access or website/Supabase model promotion occurred.

Remaining: reliable multi-seed learning benefit, useful
uncertainty/fallback supervision, independent comparative evaluation, and
simulator validity evidence. Real-world readiness is not established.
