# Frozen diagnostic: continued-training policy drift

Written before diagnostic execution. No optimization, model selection, final-test
access, calibration refitting or website promotion. Input batch:
results/research_training/temporal_v8_fc758xbz.

## Fixed design

Compare both control/temporal arms, all three training seeds, and initial versus
episode-90 checkpoints. Replay executed training scenario/fault/traffic seeds
from episodes **1, 16, 31, 46, 61, 76**, fixed before execution. Exploration off,
unchanged shield, fallback off. This is 72 rollouts and 36 paired comparisons,
not 72 independent replicates. These are seen training cases, not generalization
data. Require matched case configurations across arms and paired future arrivals.

Validate original batch artifacts first; preserve checkpoint/input/source/protocol
hashes in a new directory. Require exact planned cells and complete signal-audit
coverage. Never overwrite the batch or its selections.

## Measurements and interpretation

Record full-run waiting, average within-run p95, throughput, undiscounted training
reward, shield interventions and measured signal violations. At actual policy
decision gates, score both frozen networks on the SAME delivered input/mask
without advancing the shadow policy. Record masked action disagreements, chosen
Q margins and values on both initial/final state distributions. These states
are correlated; Q values are not calibrated realized-return measurements.

Report all arms/seeds, delay wins/losses/ties, and reward/delay direction
disagreements. Undiscounted rollout reward is not the exact discounted Bellman
objective; disagreement is diagnostic, not proof that the reward is wrong.
Summarize first/last-ten-episode logged errors, weights and losses; Q diagnostics
in the original logs represent the final minibatch, not every update.

If training and validation both regress, do not automatically call it overfitting.
If training improves while validation regresses, distribution transfer is a
plausible hypothesis, not a proven sole cause. No result here authorizes another
long training batch or establishes superiority.
