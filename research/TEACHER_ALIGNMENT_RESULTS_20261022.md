# Upstream teacher alignment and horizon sensitivity — failed

Protocols: [teacher prerequisite](SPATIAL_TEACHER_ALIGNMENT_PLAN_20261022.md),
[separate horizon diagnostic](TEACHER_HORIZON_PROTOCOL_20261022.md).

Artifacts:

- `results/teacher_alignment/pilot_20261022`: nine source replays, seven frozen
  gates, two eight-future sets, 224 distinct 20-second action branches; 39.68 s.
- `results/teacher_horizon/pilot_20261022`: the same sources/gates/future keys,
  224 branches extended to 60 seconds with exact 20-second prefixes; 110.90 s.
- `results/paper_evidence/teacher_diagnostics_20261022`: verified CSV, PNG/SVG,
  evidence summary and hashes, generated from raw measurements.

## Fixed teacher prerequisite

All nine recorded spatial-policy training configurations replay exactly,
including every gate's observation, mask, Q values, teacher proposal, source
delay/reward/throughput, shield counts and arrival hash. Seven gates satisfy
the frozen first-two-disagreements/remaining-horizon rule: five from parent
101, one from 202, one from 303. Sources with no eligible gate remain included.
All proposals and actual future RNG keys are saved/hashed before collection.

At these seven gates the policy and historical teacher both hold the current
phase, while the upstream teacher requests an immediate phase switch. The
policy/historical comparisons therefore duplicate the same action and are
not two independent baselines. All branches retain the same continuation
policy, delivered sensing, shield, macro-action schedule and physical FSM.

| 20-second future set | Paired gate/future cases | Mean delay saved by upstream choice (vehicle-seconds) | Mean throughput gained | Mean endpoint max accumulated wait saved (s) | Joint non-harmful cases |
| --- | ---: | ---: | ---: | ---: | ---: |
| First | 56 | -6.623214 | -1.071429 | 2.791071 | 24 |
| Separate check | 56 | -5.339286 | -0.946429 | 3.016071 | 21 |

The candidate worsens mean delay and throughput, while reducing the endpoint
maximum accumulated wait. Under the prespecified joint condition, 35/56 check
cases are harmful; this is not the same as 35 strictly increased-delay cases.
Only two of seven gates are jointly non-harmful in at least six of eight check
futures and strictly beneficial in at least one. Parent 303 has no such gate.
The full continuation screen fails. `continue_to_learning_pilot` is false.
No threshold, gate selection or training recipe was revised to make it pass.

The candidate adds an average 0.357143 physical switches in the check set.
Undiscounted training reward also worsens by 0.659179 on average, and reward
and delay-gain directions disagree in only 2/56 check cases. Thus this panel
does not establish a reward-direction defect. Earlier switching plus clearance
cost is a plausible mechanism; switch counts alone do not isolate that cause.

All 55,600 recorded signal samples have zero measured violations. This is
simulated-lamp coverage, not collision safety. Input/output/frozen-choice and
archived-source hashes verify, the saved summary recomputes exactly, and an
independent raw-outcome aggregation matches the check-set means.

## Horizon extension: a favorable first mean does not persist

A second protocol was frozen AFTER seeing the failed 20-second prerequisite.
It tests a different explanatory question: does a longer evaluation recover
the switching cost? It does not replace the failed screen or revive its teacher.
The primary extended endpoint is 60 seconds, with no best-horizon selection.

Every 20-second prefix reproduces exactly inside its extended trajectory,
including reward components, switch count, arrivals and endpoint wait. All nine
source trajectories also reproduce exactly. The extension has 145,200 signal
samples and zero measured violations. These overlap earlier trajectories and
must not be added as independent safety/performance samples.

| Future set | 20-second delay saved (vehicle-seconds) | 60-second delay saved (vehicle-seconds) | 60-second throughput gain |
| --- | ---: | ---: | ---: |
| First | -6.623214 | 4.430357 | -0.196429 |
| Separate check | -5.339286 | -5.137500 | -0.428571 |
| Both, descriptive | -5.981250 | -0.353571 | -0.312500 |

The first set's 60-second mean becomes positive, but its throughput still falls.
The separate set remains negative for delay and throughput; all three policy
replicate means are negative there (-3.6400, -6.7375, -11.0250 vehicle-seconds).
Aggregating both sets also gives no delay benefit. A longer horizon does not
rescue this fixed upstream-teacher substitution. The original failed screen
is preserved and `continue_to_training` remains false.

These are seven correlated seen training states, with unequal gate coverage
across three policy replicates, and multiple futures per state. The 56 cases
per panel are not 56 independent intersections or training runs. At extension
time both future sets had already been inspected at 20 seconds; the extension
is exploratory, not a new confirmatory sample. No confidence interval,
significance, full-run improvement or generalization claim follows.

## Decision

**Stop the immediate upstream-teacher alignment recipe.** Do not launch the
conditional 90-episode teacher-training plan, loosen its screen, select only
the two favorable gates or cite the first future set's positive 60-second mean
as success. The existing v9 pilot also remains failed and unpromoted.

The new scientific finding is a controlled example of horizon and future-set
sensitivity: fixed observable states and fixed choices can yield a positive
mean in one arrival-stream set and a negative mean in another. This supports
the distinction between simulator hindsight and a useful learned controller.
It does not yet establish a novel paper contribution or a superior controller.

The [source-checked novelty triage](RESEARCH_NOVELTY_TRIAGE_20261022.md) identifies
close precedents for spatial pressure, learned switching curves and
counterfactual control. A further improvement must be attributed to a specific
new mechanism and survive matched strong baselines and independent simulator
evaluation; familiar ingredients alone will not satisfy that requirement.

## Verification and writing assets

The current targeted suite passes 82 tests covering teacher partitions/screens,
source/probe preservation, independent prefix replay, spatial policies/pilot,
upstream observations and averaged-label helpers. Existing dependency warnings
remain; this is not a full frontend/repository test result. `git diff --check`
passes. The evidence export verifies both raw summaries, all stored input/
output/source-archive hashes and independent raw means before drawing the figure.

Use [the draft addendum](PAPER_ADDENDUM_OBSERVATION_AND_TEACHERS_20261022.md)
for review alongside the dated manuscript scaffold. Neither draft is submission
ready. No optimizer steps, model edits, final-test rollouts, Supabase uploads,
default-policy replacements, commits or pushes occurred.
