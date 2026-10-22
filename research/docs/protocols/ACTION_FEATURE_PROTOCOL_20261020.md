# Observed action features: grouped fitting-data comparison

Fix this comparison before reading fitting outcomes or running folds.
Use only `fit.jsonl` from `broader_20261020T134122Z`. The role contains
traffic seeds 95001–95006, three parent policies, six training templates and
two sensing conditions. Calibration/probe files and validation/final-test
scenarios are excluded from this experiment.

Compare two predefined feature maps, with no parameter search:

- `compact`: existing eight candidate-minus-parent features.
- `full_state`: compact features plus the outer product of the four-action
  one-hot difference (candidate minus parent) with [1, the complete delivered
  v7 observation (36), min(phase age,80)/40]. Total 160 features.

The second map retains the individual movement counts, forecasts, signal
context, downstream counts and service timers that aggregation may discard.
It remains a linear action-conditional outcome model. Only delivered sensor
features, known phase/age, parent proposal and Q values enter the features.
The parent-minus-parent vector must be exactly zero.

For each parent and each of the six traffic seeds, exclude that entire seed,
including all scenarios and paired sensing faults. Fit on the other five
seeds, then predict the excluded one. Each parent has its own fits.
Within each fold, compute RMS scaling (floor .05) and weights using fitting
rows only. Equalize whole-traffic-seed contributions and normalize weights
to mean one. Ridge penalty 10; no intercept; target scales [40,1,40].
Record all 36 fits (3 parents x 6 folds x 2 feature maps), their excluded
seed, train seeds, normalization, coefficients and hashes.

Report all alternatives' prediction errors and the actual choices at each
labelled gate. Keep selection criteria fixed: predicted delay gain >1
vehicle-second, throughput gain >=0, endpoint wait saving >=-1 second;
largest predicted delay gain wins, breaking ties by lower action index.
Report first executed changes, realized qualified benefits and harm using
the existing branch criteria. Abstention has zero gain and is never a benefit.

Primary comparison is the mean of per-parent/per-excluded-seed MAEs, with
equal weight to each of the 18 cells. The continuation screen requires:

1. Full-state delay MAE at least 10% lower than compact.
2. No aggregate throughput or endpoint-wait MAE regression.
3. No parent's delay MAE regression over 2%.
4. Actual executed changes and qualified benefits for every parent.
5. At least as many qualified choices as compact, no greater harmful fraction
   among changed proposals, and no lower qualified fraction. If compact makes
   no changes, require zero harmful full-state choices.

These are engineering development criteria, not significance tests or traffic
performance claims. The two models are prespecified comparisons; these folds
cannot become a final test after inspecting the results. A failure stops this
candidate before rollout validation. A pass motivates a separately specified
full-episode validation on fresh development traffic against strong baselines.
Do not reopen or tune to the previously observed calibration/probe outcomes.
Save raw predictions, choices, fold models, input/source hashes and report.
