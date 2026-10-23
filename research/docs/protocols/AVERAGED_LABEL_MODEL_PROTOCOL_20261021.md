# Observed-input model pilot with averaged versus single-future labels

Fix this protocol before collecting any new pilot outcomes. The passed frozen
choice experiment supports testing label averaging; it did not learn a policy.
This pilot learns a predictor from observable inputs at new training states.

## Fixed data and budget

Use the same three v7 parent checkpoints (101/202/303), six training scenario
templates, 1200 steps and clean sensing only. Fit source seeds: 96301–96304.
Excluded probe source seeds: 96401–96402. All are new to this experiment.
No calibration, validation or final-test scenario/outcome access. The earlier
probe/calibration files remain excluded. Clean sensing is a deliberate limit;
no robustness claim follows.

At each source, first run an unbranched parent trajectory. Select two eligible
gates using smallest SHA256 priorities of ["averaged-label-pilot-v1", parent,
scenario, source seed, step], then sort by time. Eligibility: >=2 valid actions
and >=400 remaining steps. Selection cannot inspect action outcomes. Require
two gates; do not skip a source that lacks them. Exact source replay is checked
after branching, including its original single-future action branches.

At each fitting gate collect the original action branches and eight new future
streams (replicate IDs 0–7). Source seed MUST be included in future-seed
derivation; do not reuse the old diagnostic's fixed source seed 95001. Pair
actions within each future and preserve current queues/backlog, perception,
shield, physical FSM and subsequent frozen parent policy.

Full size: 72 fitting sources / 144 gates, then 36 probe sources / 72 gates.
Total 108 sources. Expect approximately 45–65 minutes from the earlier panel;
use a cooperative 5400-second (90-minute) budget. Save completed sources on a
budget stop, mark incomplete, and do not fit on a truncated fitting panel.
No automatic long job is launched by setup; the user runs the full command.

## Fixed model comparison

Fit two separate eight-feature ridge models for each parent: six JSON models.
Input map is the existing compact observed action-minus-parent features. Do
not add simulator truth, future arrivals, scenario IDs or traffic seeds to
features. Targets are paired delay saving, throughput gain and endpoint-wait
saving, with scales [40,1,40]. `single` uses the original branch target;
`mean8` uses the mean of the eight new-future paired targets, excluding the
original. Both arms have identical states, normalization, group weighting,
features and ridge penalty 10; no hyperparameter search or bootstrap bounds.

Use fitting-only RMS scaling with floor .05 and equal whole-traffic-seed
weight, normalized to mean one. Save coefficients, scales, parent hashes and
fit membership. Freeze every model before any probe source is simulated.
These research JSON models do not replace DQN weights or production defaults.

## Excluded-source scoring

For each probe source, obtain its unbranched observations and selected gates.
Predict each valid action's gains from observed features only. Select using
unchanged constraints: delay saving >1, throughput gain >=0, endpoint-wait
saving >=-1; maximum delay gain, lower action on ties; otherwise keep parent.
Record and flush all probe choices/predictions before that source's action
branches are simulated. Probe outcomes cannot refit, recalibrate or alter any
model or choice. Preserve model and prediction hashes.

Evaluate parent, single-trained and mean8-trained choices on eight new future
streams per probe gate, IDs 8–15. Collect all valid actions to score both
choices and prediction errors. Preserve paired arrivals and audit every signal
sample. Report prediction MAE against eight-future mean targets descriptively;
do not use it to tune models.

Primary scoring: mean gains over two gates x eight futures within each source,
then equal average across 36 sources. Report all arms, retained-parent cases,
per-parent/source gains, correction activity and harmful/qualified cases.
For a development continuation require complete non-smoke data; positive
mean8 delay gain versus parent AND higher delay gain than single; nonnegative
aggregate throughput and endpoint-wait gains; no higher harmful fraction among
changed cases than single (if single abstains everywhere, require zero mean8
harm); and nonnegative delay gain, executed activity and qualified benefit
for every parent. No alternative result can replace the primary after seeing it.

## Mechanics smoke and interpretation

Smoke uses parent 101, train_ew_asymmetric_01 only, fit source seeds
96901/96902, probe seed 96903, two gates each. It uses future IDs 100–107
for fit and 108–115 for probe, and cannot pass the continuation screen.
It checks actual fitting, pre-probe model freezing, prediction persistence,
source replay and scoring. The full sources/futures remain untouched.

Even a full pass only motivates an independently specified full-episode
validation of the observed-input model against unchanged strong baselines.
The probe uses 40-second interventions followed by parent continuation, not
continuous use of the learned correction. No significance, UQ calibration,
full-run superiority, real-world safety or publication-ready claim follows.
