# Broader dataset verified; calibrated correction screen failed

Dataset: `results/action_rank_dataset/broader_20261020T134122Z`.
Fitted models, raw predictions and report:
`results/action_rank_calibration/broader_20261020`.
[Protocol fixed before reading role outcomes](ACTION_RANK_CALIBRATION_PROTOCOL_20261020.md).

## Collection verification

All 648 source trajectories completed in 1,453.45 seconds (24.22 minutes):
216 fitting, 360 calibration and 72 excluded training-probe sources.
There are 1,944 labelled gates and 5,707 action branches. The 3,060,400
labelled-source/branch signal samples have zero measured violations.
These are simulator checks, not evidence of real-world traffic safety.

Role-file hashes match the user's reported values. Collection input/parent
hashes, archived sources, exact role/parent/scenario/fault cells, deterministic
gate selection, complete branch action coverage, paired branch arrivals and
signal coverage were checked. The collector checked exact pre-scan/source
replay equality while running; separate pre-scan records were not saved, so
this subsequent verification does not independently replay all 648 sources.

## Fitting and calibration completed

Three separate eight-feature ridge outcome models were fitted on seeds
95001–95006 only, with whole-traffic-seed weighting. They have 447/451/451
non-parent fitting alternatives for parents 101/202/303. Coefficients were
saved and hashed before calibration outcomes were read.

Calibration uses only seeds 95101–95110: 671/683/682 non-parent alternatives
per parent. A joint worst-case residual is calculated for each traffic seed,
including all its scenarios, faults, actions and three target components.
The predeclared order statistic is the largest of these ten group scores.
Models were calibrated, saved and hashed before probe seeds 95201/95202 were
read. This fits small research correction models, **not new DQN weights**.

The resulting normalized margins are 8.425, 8.329 and 10.478. They subtract
approximately 337/333/419 vehicle-seconds from predicted delay savings and
8.42/8.33/10.48 vehicles from predicted throughput gains (with endpoint-wait
margins also scaled by 40). The broad bounds are intentionally conservative;
they are not tuned down after observing abstention.

## Reserved probe: no useful calibrated activity

Probe coverage includes 216 labelled decisions and 378 non-parent alternatives.

| Parent | Point-only executed changes | Qualified benefits | Harmful changes | Calibrated executed changes |
| --- | ---: | ---: | ---: | ---: |
| 101 | 5 | 3 | 2 | 0 |
| 202 | 7 | 4 | 2 | 0 |
| 303 | 1 | 0 | 1 | 0 |
| Total | 13 | 7 | 5 | 0 |

“Qualified” requires actual branch delay saving >1 vehicle-second, no throughput
loss and endpoint maximum-wait increase <=1 second. “Harmful” means delay loss
>1 vehicle-second, any throughput loss, or endpoint maximum-wait increase >1
second. One changed point-only decision is neither qualified nor harmful.
These are 40-second counterfactual branches, not whole-simulation gains.

The calibrated primary abstains at every probe decision. It has no observed
selected harm because it makes no changes, not because it has demonstrated a
useful safer policy.

Across all alternatives, componentwise lower-bound coverage is 100% for delay,
99.21% for throughput and 100% for endpoint wait. Joint alternative coverage is
99.21%, but the whole-seed bound fails for probe seed 95201 in parents 101 and
202. Only one of the two probe traffic seeds is fully covered across all
parents. Correlated action rows must not be used as independent seed-level
evidence or as a real-world confidence guarantee.

Point-prediction MAE is 29.443 vehicle-seconds, 1.678 vehicles and 8.404 seconds
in target order. These are prediction errors, not traffic-delay improvements.
They must not be compared directly with the earlier 51.494 vehicle-second
error as an improvement claim: probe traffic and gate sampling changed.

## Decision and next work

The predefined continuation screen fails on activity, qualified benefits and
whole-seed coverage. No full-rollout validation or final-test run was launched,
no controller default changed, and no checkpoint was uploaded/promoted.
Existing DQN/D3QN parents remain untouched.

Do not repeat this collection or launch another large DQN batch now. The
existing fitting data can support the next bounded model-development
experiment: test whether richer observed state/action features predict branch
outcomes better, using leave-one-traffic-seed-out comparisons **within fitting
data only**. The current eight aggregated features and linear model may be
limiting, but this experiment does not establish that as the sole cause.
Specify that experiment before fitting; do not select features, thresholds or
models using the already observed calibration/probe results. Any claimed
controller improvement still requires fresh full-episode development
validation against unchanged strong baselines, followed by an appropriate
final evaluation plan.

57 targeted tests passed. All saved point fits and calibrated payloads
reproduce exactly from their designated role files; margins were independently
recomputed; frozen model hashes, source archive, raw prediction rows and report
recomputation verified. `git diff --check` passed.
The requested superiority and research-readiness goals remain unachieved.
