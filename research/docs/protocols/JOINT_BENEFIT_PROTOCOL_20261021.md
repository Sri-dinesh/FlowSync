# Joint-benefit classification versus separate outcome regression

Prespecify before fitting this comparison. The completed averaged-label pilot
failed on activity and gain. This is a new development hypothesis, not a
retrospective rescue of that result. Do not change its reported outcome.

Use ONLY fitting rows from `averaged_label_model/pilot_20261021T095353Z`:
four source seeds 96301–96304, three parents, six training templates and two
gates per source, clean sensing. The already inspected probe rows/scores must
not enter this comparison. The pilot report may supply the fitting-file hash
only, never a model/threshold selection criterion.

For each parent, leave one entire source traffic seed out, including all
its scenarios and gates. Fit on the other three. Compare exactly two fixed
methods on these identical folds, without a hyperparameter search:

- `regression`: existing eight observed candidate-minus-parent features,
  separate three-target ridge regression, penalty 10, target scales [40,1,40],
  no intercept, and unchanged gain-based selection thresholds.
- `joint`: the SAME eight observed features plus a logistic intercept.
  Binary target: the eight-future MEAN gains jointly satisfy delay >1,
  throughput >=0 and endpoint-wait saving >=-1. Use equal whole-traffic-seed
  base weights, then equal total weight for positive/negative classes; normalize
  to mean one. L2 penalty 10 on the eight coefficients, not the intercept.
  Fit using deterministic damped Newton updates, maximum 100 iterations,
  gradient tolerance 1e-7. Nonconvergence is an execution failure, not a usable
  candidate. A single-class training fold uses its constant label explicitly.

For both methods, RMS feature scaling (floor .05) uses training rows only and
equal whole-traffic-seed base weights, BEFORE joint-class reweighting.
Joint selection: score >0.5, maximum score, lower action on ties, otherwise
retain parent. Class weighting means this score is NOT a calibrated probability
or uncertainty bound. This method replaces the prediction/choice formulation,
not the physical shield or outcome criteria. No old thresholds are relaxed.

There are 12 held-out folds and 24 fitted/saved models (two per fold).
Predict held-out observations without using their outcomes for fitting or
normalization. Score frozen choices on all eight recorded paired futures for
the held-out gates, then return to parent continuation as in the collected
labels. Report all sources and retained-parent cases. Primary mean: first
average within source, then equally across the 72 source rows. Also report
per-parent outcomes, executed corrections, qualified/harmful case counts and
joint-label confusion counts. In-sample accuracy cannot establish success.

Continuation requires positive joint delay gain vs unchanged parent and
greater delay gain than regression; aggregate throughput and endpoint-wait
gains >=0; no higher harmful fraction among changed cases than regression
(if regression never changes, require zero joint harm); and nonnegative delay
gain, executed activity and a qualified beneficial case for every parent.
All 12 folds must complete. An always-abstaining candidate cannot pass.

This is an engineering screen on training data already used for development,
not an independent final test or significance claim. Even a pass requires
separately frozen full-fit models, NEW excluded-source evaluation and then
full-episode comparisons against strong baselines. No old probe is recycled
as fresh evidence, no checkpoint is promoted and no full-run improvement is
claimed from this comparison. A failure stops this candidate without more
data collection. Preserve all fold models, raw predictions, scores and hashes.
