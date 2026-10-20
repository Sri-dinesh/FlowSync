# Action-ranking correction pilot: primary screen failed

Artifacts: `results/action_rank_pilot/pilot_20261020`.
[Predeclared protocol](ACTION_RANK_PILOT_PROTOCOL_20261020.md).
All 72 training-label source runs, three model fits and 168 separate validation
runs completed. Validation execution took 88.30 seconds. This was a genuine
learned correction and full-run comparison, not an oracle-branch performance
claim. Existing production policies/defaults remain unchanged.

## Complete validation results

Means over three validation templates, traffic seeds 25001/25002 and clean/mixed
sensing. Each learned arm includes all three parent replicates; each classical
baseline runs once per traffic cell, not once per parent. The primary candidate
was fixed in advance as the bootstrap-supervised `uncertain` variant.

| Controller | Average delay (s) | Average within-run p95 (s) | Passed vehicles |
| --- | ---: | ---: | ---: |
| Parent D3QN + shield | 12.813556 | 41.348611 | 86.194444 |
| Point-estimate ranking + shield (`mean`, ablation) | 12.725861 | 41.173472 | 86.166667 |
| Bootstrap-supervised ranking + shield (`uncertain`, primary) | 12.815194 | 41.365972 | 85.972222 |
| Max-Pressure + same shield | 12.978583 | 42.381667 | 87.083333 |
| Max-Pressure | 12.492500 | 46.014167 | 86.416667 |
| Greedy | 12.144750 | 44.785417 | 85.333333 |
| Fixed | 15.651500 | 39.932500 | 82.166667 |
| Actuated | 15.867917 | 63.667083 | 79.750000 |

The point-estimate ablation reduces mean delay by 0.087694 s (0.6844%) versus
parents, with small improvements for every parent replicate. It also lowers
average within-run p95, but aggregate throughput declines slightly. This is
below the predefined 2% improvement criterion, and it is not a substitute for
the primary candidate after results are observed. No significance or equivalence
claim follows from two traffic seeds and reused development templates.

The primary does not improve aggregate delay, p95 or throughput versus parents.
It does not improve delay by 2% versus shielded Max-Pressure, and throughput is
lower than that comparator too. The predefined continuation gate fails.
Greedy and unshielded Max-Pressure have lower mean delay than both new variants;
they also have higher p95 on this panel. Report that trade-off without changing
the primary metric posthoc or claiming universal superiority.

| Parent seed | Parent delay | Point-estimate delay | Primary delay |
| --- | ---: | ---: | ---: |
| 101 | 12.871667 | 12.863333 | 12.871667 |
| 202 | 12.683500 | 12.598250 | 12.694417 |
| 303 | 12.885500 | 12.716000 | 12.879500 |

Point-estimate corrections changed 38 proposals and 30 first executed actions;
the primary changed 10 proposals and eight first executed actions. Shielded
proposal changes that did not change execution are counted separately. The
primary was active, not accidentally a disabled/no-op controller.

## Training and excluded-trajectory evidence

Fitting uses traffic seed 94001 only, all six training templates and both fault
conditions. Each parent has its own eight-feature, three-output ridge model
and 20 source-trajectory bootstrap fits. Fit example counts are 61/68/68;
each uses 12 scenario/fault source groups. Fits remain parent-specific; shared
traffic/scenarios still make the replicate evidence correlated.

All models were frozen before examining predictions on excluded training
traffic seed 94002 or complete validation. On 104 excluded decision points per
variant, the point estimate changes three choices (one delay improvement above
one vehicle-second, two within the +/-1 tolerance, none worse beyond that
tolerance). The primary changes one choice, which meets the realized branch
delay/throughput/endpoint-wait criteria. These sparse, favorable branch checks
did not translate into a validated full-run primary gain. They are not an
independent final test or evidence of calibrated safety confidence.

## Verification and boundaries

- All 72 label-source and 168 validation cells present without duplicates.
- Training/probe seeds, validation seeds and parent identities remain separated.
- All three saved model payloads reproduce exactly when refitted from seed
  94001 labels only; excluded-probe predictions reproduce from the frozen models.
- Input/source/model hashes, archived sources and raw-report recomputation
  verified. Every learned validation row records its parent hash; correction
  rows also record the matching correction-model hash.
- Original parent checkpoint files are unchanged. No website/Supabase promotion.
- Full executed-signal audit coverage: 86,400 label-source samples, 246,800 branch
  samples, 201,600 validation samples; zero measured conflicts/clearance failures.
  These counts do not constitute real-world safety evidence.
- 103 targeted tests passed, including deterministic fitting, training-only
  input rejection, uncertainty abstention, masking, unchanged decision clocks,
  parent binding, and exact parent behavior when correction abstains.
  `git diff --check` passed.

The bootstrap is uncalibrated epistemic spread, not a confidence guarantee.
Scenario/fault trajectories share arrival streams within traffic seeds; their
bootstrap grouping must not be described as independent traffic-seed sampling.
Only one traffic seed fitted each model. Labels cover at most three spaced
decision gates after tick 200, whereas deployment of the experimental wrapper
considers every regular policy gate. Label coverage and policy-induced state
shift therefore remain plausible limitations, not established sole causes.
Forty-second outcome labels omit later effects; endpoint maximum wait is not a
full fairness guarantee. The models use sensor-only inputs, but the sensor is
synthetic, not a validated camera detector.

## Decision and remaining work

Keep the original parents; do not promote either correction or rerun the final
paper-test panel. The point-estimate result is a modest exploratory signal,
not a breakthrough, and the added uncertainty supervision has not demonstrated
an efficiency benefit. Preserve both results and the frozen failed protocol.

The next defensible development step is to test label coverage across additional
prespecified training traffic seeds and representative decision times, with
whole traffic trajectories excluded for calibration. Evaluate whether the
predictive spread actually tracks wrong corrections before choosing a new
supervision rule. Any new settings need a new protocol and a separate validation
panel; do not tune them on the 25001/25002 scores above. A larger experiment
should follow only after that data/uncertainty audit, not another arbitrary
900-episode RL run. Overall research-readiness remains unestablished.
