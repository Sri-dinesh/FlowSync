# Broader action-outcome dataset — fixed before collection

This is training-data collection, not a new performance claim or another
900-episode DQN run. Keep the original three parent checkpoints unchanged.
No validation/test scenarios, model fitting, threshold selection, final-test
evaluation, upload or controller promotion.

## Separate roles

Use all six existing training templates, all parents 101/202/303, and clean /
validation_mixed faults (the latter is a fault-profile name, not a data split).
Keep complete traffic seeds separated across these files:

- Fit: 95001–95006 (216 source trajectories).
- Calibration: 95101–95110 (360 source trajectories).
- Excluded training probe: 95201–95202 (72 source trajectories).

Total 648 source trajectories. Never count the six scenarios, two paired faults
or three parents sharing a seed as independent traffic-seed replicates.
Future bootstrap/residual calibration must group **all scenarios and faults
within a traffic seed**, separately for each parent. Do not use calibration
labels for feature selection or fitting coefficients; do not use probe labels
to select uncertainty thresholds. Ten calibration seeds remain a small sample,
not a real-world confidence guarantee. Specify the fitting/calibration method
separately before inspecting those role-specific outcomes.

## Representative eligible decision gates

Run the frozen parent once without forks to enumerate decision gates. Eligible
gates have at least two valid proposals and a complete remaining 400-tick
counterfactual horizon. Select up to three using deterministic hash priorities
over parent/scenario/traffic seed/fault/step; outcomes are not selection inputs.
Repeat the exact source episode and fork every valid action at those steps.
Verify source results and all non-branch decision records equal the first pass.

Unlike the previous first-three-spaced-after-200 rule, this covers early and
later eligible decisions without selecting for apparent benefit. It still
excludes the final 400 ticks, and source states still follow the parent rather
than the future corrected policy. Do not claim this resolves every
distribution-shift problem. Branches preserve the macro-action hold, physical
FSM and per-tick shield and then resume the same parent.

Check complete 400-tick signal audits, finite nonnegative branch outcomes,
all valid actions exactly once and common arrivals. Preserve raw labels,
role assignments, input/source hashes and source archive. A pre-scan equality
failure stops collection. No source checkpoint is modified.

## Runtime and completion

Full collection has a 3,300-second cooperative limit by default. Preserve
partial files and mark incomplete with nonzero exit; never report a budget
stop as success or silently fit from partial data. A separate `--smoke` mode
runs one parent, one training scenario, one fit seed and clean sensing only;
it must explicitly report that the full dataset is not complete.

After complete collection, fit/calibrate on their respective roles using a
new frozen protocol, then inspect the excluded training probe. Only a justified
candidate proceeds to fresh development validation with unchanged strong
baselines. The existing final-test panel remains frozen.
