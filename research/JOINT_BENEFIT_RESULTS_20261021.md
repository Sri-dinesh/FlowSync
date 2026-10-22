# Joint-benefit fitting-data comparison: failed continuation

Protocol: [JOINT_BENEFIT_PROTOCOL_20261021.md](JOINT_BENEFIT_PROTOCOL_20261021.md).
Implementation: `research/compare_joint_benefit.py`.
Output: `results/joint_benefit_comparison/grouped_20261021`.

## Question and separation

The full averaged-label regressor abstains on all excluded probes. This
follow-up asks whether directly learning the joint benefit label can improve
decisions using the same eight observable features. It is not a threshold
rescue of the previous result. No probe, calibration, validation or final-test
outcomes enter this comparison.

Only the pinned fitting file was used: four source seeds 96301–96304, three
parents and six training scenarios, two gates each. Each parent has four
leave-one-entire-traffic-seed-out folds; all scenarios and gates belonging to
the held-out seed are excluded from fitting and normalization. Exactly 24
models were saved, with no hyperparameter search. The class-balanced logistic
score is not a calibrated probability or uncertainty bound.

## Results

All 12 folds/72 sources completed. Each arm has 1,152 paired gate/future
cases. Gains are first averaged within source, then equally across sources.
Positive delay gain means vehicle-seconds saved, not seconds per vehicle.

| Method | Changed gates / 144 | Mean delay gain (vehicle-s) | Harmful / changed future cases |
| --- | ---: | ---: | ---: |
| Unchanged parent | 0 | 0 | Not applicable |
| Three-target regression | 6 | +1.1648 | 8/48 (16.67%) |
| Joint classifier | 77 | -1.0667 | 353/616 (57.31%) |

The classifier's aggregate throughput gain is +0.4540 vehicles and endpoint
wait saving +0.0446 seconds. These gains do not override its negative delay
gain or increased harm. Per-parent mean delay gains are +1.0109, -5.3557 and
+1.1448 vehicle-seconds for parents 101, 202 and 303 respectively. Parent 303
also has negative endpoint-wait gain (-0.0977 seconds).

Of 36 alternatives with qualified eight-future mean outcomes, regression
detects three with three false positives; joint classification detects 20
with 93 false positives. Increased recall/activity is not improved control.
The classifier changes 616 proposed-action cases but only 576 first executed
actions; regression changes 48 proposals and 40 first executed actions.
Proposal and execution differences are therefore reported separately.

`continue_to_fresh_source_pilot: false`. Positive delay gain, superiority to
regression, no-higher-harm and every-parent benefit checks fail. No full-fit
candidate was promoted, no new data collection was launched, and no parent
DQN checkpoint or production controller changed.

## Verification and limitations

All file/archive hashes verified. All 24 models refit exactly; all 72 saved
source predictions reproduce. Independent arithmetic from recorded branch
outcomes reproduces all 3,456 arm/future decision records and equal-source
mean gains. Every logistic fit converged; maximum gradient magnitude is
8.05e-8, below the prespecified 1e-7 tolerance.

86 targeted tests pass, including nine new checks for grouped exclusion,
train-only scaling, deterministic convergence, unpenalized intercept,
single-class handling, strict selection thresholds and abstention rejection.
Existing dependency deprecation warnings remain; no test failures occurred.

This screen reuses already collected training futures. It adds no new traffic
simulations or safety observations, and is not an independent statistical
test. A single changed action followed by parent continuation is not a
full-episode learned controller. The modest regression result here does not
erase the separate full-fit model's failed excluded-probe result.

Stop this candidate without more collection or threshold changes. The
observed limitation is now documented: on this small fitting panel, changing
to class-balanced joint classification increases false positives and harm.
It does not prove that all classifiers, representations or RL approaches
must fail. A new policy hypothesis requires a separate development protocol
and fresh evaluation before any stronger claim.
