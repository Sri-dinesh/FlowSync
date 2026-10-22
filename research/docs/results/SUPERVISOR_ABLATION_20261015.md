# Validation-only supervisor diagnosis

Specified before executing this ablation, after inspecting the frozen domain
batch test. This is development evidence, not another independent final test.

Use all three existing domain-batch selected checkpoints, without retraining or
reselection. On all three validation templates, traffic seeds 21001–21005,
and the existing clean/mixed validation fault profiles, evaluate six variants:
plain D3QN, Max-Pressure, and the matched shield/fallback 2x2 factorial (neither,
shield only, fallback only, both). Keep the original fitted calibration and all
thresholds unchanged. Total: 540 runs. Never read the test scenarios in this
script or select parameters from this study's previously inspected test scores.

Check that the disabled wrapper exactly matches plain D3QN in traffic metrics;
record delay, within-run p95, throughput, starvation events, signal audit
violations, fallback durations and shield override reasons. Aggregate all three
training seeds and show clean/noisy strata separately. A lower mean delay is
not sufficient grounds for removing liveness or clearance constraints. These
ablations diagnose the current model, not the contribution of the changed
training recipe. Preserve all earlier test artifacts unchanged.

## Completed findings

All 540 runs completed (180 per training seed). Each learned row's checkpoint
hash matches its configuration. The disabled wrapper exactly matches plain
D3QN in delay, p95, throughput, starvation counts, signal violations and arrival
hash for all 90 paired cells. Thus, equality in this particular ablation is
expected and verified, not evidence that the switch is ineffective.

Each row below averages 90 simulations (three policy seeds, five traffic seeds,
three validation templates, two fault conditions). The Max-Pressure reference
is repeated identically across policy seeds; it is not 90 independent seeds.

| Variant | Mean delay (s) | Mean within-run p95 (s) | Mean vehicles passed | Starvation events |
| --- | ---: | ---: | ---: | ---: |
| Plain D3QN / both disabled | 10.578 | 39.279 | 84.589 | 195 |
| Shield only | 10.799 | 37.675 | 84.511 | 193 |
| Fallback only | 10.816 | 39.447 | 84.256 | 197 |
| Full UQ | 11.128 | 38.204 | 84.133 | 198 |
| Max-Pressure | 10.845 | 40.124 | 84.000 | 192 |

All measured simulated signal conflict/clearance counts are zero. This is not
real-world safety evidence. The existing starvation metric counts each repeated
45-second period of non-service while demand is present; it is not maximum
individual waiting time, nor proof of a hard fairness bound.

### Clean versus mixed faults

| Variant | Clean mean delay | Clean p95 | Mixed mean delay | Mixed p95 |
| --- | ---: | ---: | ---: | ---: |
| D3QN | 10.599 | 39.589 | 10.558 | 38.969 |
| Shield only | 10.823 | 36.846 | 10.776 | 38.504 |
| Fallback only | 10.592 | 39.372 | 11.040 | 39.521 |
| Full UQ | 10.808 | 36.630 | 11.447 | 39.778 |

Every recorded shield override in these runs is an anti-starvation override,
predominantly for phases 2 and 3 (85 overrides with shield only, 89 with full
UQ). The maximum-green ceiling did not drive this observed penalty. In mixed
faults, fallback-only spends 48,232 ticks in fallback across 45 runs; switching
to the classical backup worsens both aggregate mean delay and p95 relative to
the noise-trained D3QN. Clean fallback is rare (80 ticks across 45 runs).

## Interpretation and next development work

1. Preserve the current evidence; do not tune thresholds against the final test.
2. Do not remove the shield merely to lower mean delay: its anti-starvation
   interventions improve tail delay on these validation runs. Model the
   deployed shield in a future training/selection recipe so the learned policy
   can anticipate that constraint; this requires a separate matched experiment.
3. The fitted estimator predicts synthetic count-error events, not the relative
   benefit of the backup controller. A future supervisor must be evaluated on
   decision harm and recovery behavior, not only count-error AUROC. Both the
   RL policy and Max-Pressure currently receive the same corrupted sensor data.
4. No thresholds, default controller settings or trained weights were changed
   in response to these results. These are validation diagnostics, not a newly
   validated controller or a publication-ready novelty claim.

Artifacts:

- [Seed 101](../../../results/validation_comparison/domain_supervisor_20261015_seed101/summary.json)
- [Seed 202](../../../results/validation_comparison/domain_supervisor_20261015_seed202/summary.json)
- [Seed 303](../../../results/validation_comparison/domain_supervisor_20261015_seed303/summary.json)

Each directory retains configuration/source hashes, raw paired runs, and full
per-run experiment bundles with diagnostics and events.
