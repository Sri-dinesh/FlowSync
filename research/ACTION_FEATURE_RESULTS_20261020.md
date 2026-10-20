# Richer observed features: grouped comparison did not pass

Output: `results/action_feature_comparison/grouped_20261020`.
Protocol: [prespecified comparison](ACTION_FEATURE_PROTOCOL_20261020.md).
Runner: `research/compare_action_features.py`.

## What was evaluated

Only the fitting role of `broader_20261020T134122Z` was read for outcomes.
For each of three unchanged parent policies, each of six traffic seeds was
excluded in turn, including all its scenarios and sensing conditions.
Both feature maps use the same labels, folds, ridge penalty, target scales,
selection thresholds and train-only normalization. No hyperparameter search.

All 36 fits completed. There are 1,349 non-parent alternatives and 648
labelled decisions per feature map. Raw predictions, decisions, coefficients,
fold membership, source snapshot and provenance hashes are saved.
These are cross-validated prediction/branch-choice results within fitting
data, not new full-simulation performance measurements.

## Results

Errors are equally averaged over the 18 parent/traffic-seed cells.

| Measure | Compact (8 features) | Full state (160 features) |
| --- | ---: | ---: |
| Delay-saving MAE, vehicle-seconds | 33.342 | 35.851 |
| Throughput-gain MAE, vehicles | 1.554 | 1.724 |
| Endpoint-wait-saving MAE, seconds | 9.204 | 12.183 |
| Changed proposals | 47 | 121 |
| Changed first executed actions | 42 | 114 |
| Qualified beneficial choices | 24 | 50 |
| Harmful choices | 18 | 64 |
| Harmful fraction of changed proposals | 38.30% | 52.89% |
| Qualified fraction of changed proposals | 51.06% | 41.32% |

Delay-prediction error increases by 7.53%, with regression in every parent.
More beneficial choices in absolute count do not establish an improvement:
the full-state model intervenes much more often and has a worse harmful
fraction. Choice labels use paired 40-second branches following the original
parent afterward; they are not long-run performance of the corrected policy.

The prespecified continuation screen fails. No calibration/probe outcomes,
validation scenarios or final-test outcomes were accessed by this comparison.
No DQN checkpoint, live controller, database or uploaded model was modified.

## Interpretation and next step

Simply expanding this linear model's input from eight aggregated features
to action-conditioned full observations did not fix excluded-seed prediction.
This does not establish that the extra observations are useless, that linear
models can never work, or that there is a simulator bug. Limited independent
traffic data, model form and uncertainty in future arrivals remain possible
explanations, not confirmed causes.

Do not promote this model, relax the screen retrospectively, or launch a
large training batch based on these results. Before another candidate, the
next bounded diagnostic should examine label predictability on fitting data:
compare fixed-observation action effects across independent future-arrival
realizations, preserving within-realization pairing between actions. This
would distinguish reliable action advantages from favorable random futures.
It requires an explicit engine/RNG branching protocol and verification before
collecting new labels; it has not been implemented or run here.

For the manuscript, retain the audited simulation evaluation and these
negative development results. They do not support a superiority claim for
FlowSync-UQ or real-world deployment readiness. Research writing can proceed
on the verified methods and limitations while the main performance
contribution remains unresolved.

## Verification

51 targeted tests passed. All 36 fold fits reproduce exactly; archived source, input and saved-model
hashes verify. Per-cell and aggregate errors were independently recomputed
from all 2,698 saved prediction rows. Regression tests cover exclusion of
held-out seeds from normalization and fitting, rejection of other data roles,
observable-only features, action-selection constraints and failure of an
always-abstaining candidate to pass the continuation screen.
