# Action-ranking correction pilot — frozen before fitting/validation

Research-only candidate, not a replacement for the website controller.
Existing v5 parent policies 101/202/303 remain untouched. The failed replay
coverage screen is not reinterpreted as a success.

## Training and diagnostic split

Collect all-action 40-second labels using the existing branch mechanism, all six
training templates, clean/mixed sensing, and parent-specific source trajectories.
Use traffic seed 94001 for fitting; reuse the 18 already verified feasibility
runs where keys match, and collect the missing 18. Collect seed 94002 on all
36 parent/scenario/fault combinations as an excluded training-trajectory probe.
Keep at most three eligible branch points per source run, as before. All choices
are fixed here, not selected using future validation scores. No final-test use.

Fit each parent's correction separately. Targets are differences from the
parent-action branch: delay saved, throughput gained, endpoint maximum wait
saved. Include all valid alternatives (including harmful/tied examples), not
only favorable labels. Parent action is implicit zero gain. Do not combine
replicate labels into one model and claim three independent fits.

Use eight observable candidate-minus-parent features: phase queue mean,
downstream occupancy mean, phase-service timer, current-phase indicator,
current-phase indicator × normalized phase age, candidate demand × normalized
phase age when current, left-turn phase indicator, and clipped parent Q gap.
Queue/downstream/timer values use the delivered v7 encoding. No oracle state,
future information or branch outcomes enter inference features.

Fit an eight-feature, no-intercept ridge regression for three outcomes. Scale
features by training RMS (floor 0.05); target scales [40, 1, 40]; ridge penalty
10. Weight rows so each source trajectory contributes equally, then normalize
weights to mean one. No hyperparameter sweep. Fit 20 source-trajectory bootstrap
replicas with RNG seed 88000 + parent seed. These provide an uncalibrated
epistemic spread, not a confidence guarantee or camera-error probability.

Two prespecified variants use the same model:

- `mean`: use the point-fit predicted outcome differences.
- `uncertain`: use the bootstrap 10th percentile for each predicted gain.

Change the parent's proposal only if predicted delay saving >1 vehicle-second,
throughput gain >=0 and endpoint wait saving >=-1 second. Among qualifying
valid alternatives choose greatest predicted delay gain (lowest action index
on ties); otherwise retain parent. Invalid/non-finite inference retains parent.
Preserve the parent macro-action clock and the shield on every microtick.
The primary candidate is `uncertain`; `mean` is an ablation, not a posthoc swap.
Sensor-error fallback remains off to isolate the new correction/supervision.

## Evidence and validation

Record excluded training-probe action choices and their realized paired branch
outcomes. Do not use those results to change settings. Freeze fitted JSON files,
their hashes and all input/source/scenario provenance before validation.

Run complete validation episodes on all three existing validation templates,
new development traffic seeds 25001/25002, clean/mixed faults. Compare all three
parent replicates, both correction variants, Max-Pressure with the same shield,
unshielded Max-Pressure, Greedy, Fixed and Actuated. Each classical baseline runs
once per traffic cell (do not inflate its sample size by duplicating it).
Expected 168 validation runs: 108 learned/parent plus 60 classical.

Continuation requires the primary candidate to reduce aggregate delay >=2%
versus both parents and shielded Max-Pressure, no parent-seed delay regression
>1% versus its parent, no aggregate p95/throughput regression versus either,
complete signal auditing with zero measured violations, and actual nonzero
correction activity. These are development gates, not significance tests or
publication readiness. Report unshielded baselines and both candidate arms even
if the primary fails. No default promotion, full final-test rerun or deployment.

Collection and validation each have a 240-second cooperative execution budget;
fitting is a small linear solve. Preserve incomplete stages and never restart
or overwrite results automatically. The model uses training labels only; this
pilot does not establish real-world safety, novelty or universal superiority.
