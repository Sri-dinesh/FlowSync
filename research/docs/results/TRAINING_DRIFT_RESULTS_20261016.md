# Continued-training diagnostic results

## Decision

Keep the parent policies; do not promote the temporal pilot or launch its
expanded evaluation. The pilot failed its predefined screen, and a subsequent
training-only diagnostic found regression on sampled training traffic as well.
This is not explained solely by a validation-domain mismatch. It does not prove
a specific optimizer defect or that every additional update is harmful.

## Completed temporal pilot

Input: `results/research_training/temporal_v8_fc758xbz`. All six runs completed
90 episodes, 24 demonstrations and 2,880 optimizer updates. The comparison was
independently reproduced, checking initial weights, matched configurations,
update counts, checkpoint/source hashes, paired arrivals and signal coverage.
All three temporal selections retained their initial checkpoint. Each control
worker took about 117 seconds; temporal workers about 121–122 seconds.

| Validation result, all three seeds | Mean delay (s) | Average within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: |
| Initial parents | 10.841 | — | — |
| Control, episode 90 | 11.070 | 39.251 | 89.750 |
| Temporal, episode 90 | 11.217 | 39.474 | 89.528 |

Temporal delay is 1.33% worse than control at the predefined latest common
checkpoint. The episode-60 temporal advantage is only 0.049 s and also fails
the continuation screen; it is not substituted as the primary endpoint after
seeing episode 90. All 360 candidate-validation runs have 432,000 audited signal
samples and zero measured conflict/clearance violations. These remain development
results, not independent final tests or proof of road safety.

## Training-only diagnosis

The [pre-execution protocol](../protocols/TRAINING_DRIFT_PROTOCOL_20261016.md) fixed six recorded
episodes (1, 16, 31, 46, 61, 76) from each training replicate. Both arms' initial
and final checkpoints were evaluated on the actual recorded scenario, seed and
fault configuration, with exploration off, shield on and fallback off. No
optimizer ran. This is **72 rollouts / 36 matched pairs**, on already seen
training data; it must not be added to the final-test sample size.

| Training replay arm | Initial delay (s) | Final delay (s) | Change |
| --- | ---: | ---: | ---: |
| Control | 9.838 | 10.051 | +0.213 s |
| Temporal | 9.838 | 10.222 | +0.384 s |

The aggregate regression is **not uniform**. Control improves eight cases and
worsens ten. Temporal improves nine, worsens six and ties three (0.001 s
tolerance). Training seed 202 improves in both arms on average. A single large
low-demand regression strongly influences both aggregate means; keep it and all
other cases rather than removing the outlier to obtain a win.

For seed 101's recorded episode 61, the same 23 arrivals yield 4.061 s initial
delay, 9.643 s final control delay and 11.922 s final temporal delay. Both final
policies also earn worse total reward. Shadow probes show repeated cases where
the updated policy keeps the current green while its initial policy would
switch. The temporal rollout has **zero shield overrides**, so that particular
regression is not caused by the shield blocking a good policy proposal.
These observations identify a policy failure pattern, not the causal learning
mechanism or proof that every changed action is wrong.

Across all sampled cases, total undiscounted reward also worsens in aggregate
(control -1.417, temporal -1.393). Reward-versus-delay direction disagreements
occur in four of 36 pairs. This does not support replacing the reward on the
assumption that it uniformly rewards worse delay. Undiscounted reward is not
the exact discounted Bellman objective, and a small sample cannot rule out
reward/state limitations elsewhere.

On initial-policy states, the final control proposes a different masked action
at 51/234 decision gates, and temporal at 48/234. Thus changed weights are
changing decisions, not merely checkpoint metadata. On final-policy states the
disagreement counts are 88/285 and 87/277 respectively. These are correlated
state observations, not independent statistical trials.

## Loss logs: a confirmed interpretation/observability problem

The following values average the logged last minibatch of each episode across
all three training seeds. They are not whole-episode or fixed-dataset losses.

| Arm/window | PER-weighted TD loss | Mean absolute TD error | Mean importance weight |
| --- | ---: | ---: | ---: |
| Control, first 10 episodes | 3.243 | 11.401 | 0.375 |
| Control, last 10 episodes | 0.929 | 16.689 | 0.114 |
| Temporal, first 10 episodes | 3.021 | 11.088 | 0.365 |
| Temporal, last 10 episodes | 0.859 | 17.511 | 0.104 |

A declining weighted loss does not demonstrate declining prediction error:
replay distributions, targets and weights all change. Growing negative Q values
alone also do not establish divergence with predominantly negative rewards.
Demonstrations are still sampled; late weighted imitation loss is small, and
the previous margin-release experiment did not establish a remedy.

Added logging only: `unweighted_td_loss`, `pre_clip_gradient_norm`, and minimum/
maximum importance weights. Existing loss, gradient clipping, optimizer step,
priorities and action selection are unchanged. Numerical regression tests show
identical raw error can produce a tenfold weighted-loss difference while the
new unweighted metric stays fixed; the expected SGD parameter update is retained.
Even the new unweighted metric is on a changing minibatch, not a generalization
score. Historical logs cannot retroactively recover all these new quantities.

## Integrity and limits

All 72 planned cells, source archive and checkpoint/input hashes verified;
the saved report reproduces from raw rows. All 86,400 simulated steps have
signal-audit coverage, with zero measured conflicts/clearance violations.
Probe tests verify identical executed trajectories/rewards with and without
shadow evaluation, and unchanged policy weights. The diagnostic archive predates
the logging-only instrumentation above and remains untouched.

Verification: 74 targeted regression tests passed; `git diff --check` passed.

Artifacts: [full report](../../../results/training_drift/temporal_v8_20261016/report.json),
[raw runs and probes](../../../results/training_drift/temporal_v8_20261016/runs.jsonl),
[frozen manifest](../../../results/training_drift/temporal_v8_20261016/manifest.json).

## Next bounded hypothesis, not a proven fix

Investigate update pressure before adding more input features. Each pilot run
made 2,880 updates but collected only about 1,050–1,230 new online transitions;
32 minibatches of 128 per episode imply substantial replay reuse. This is not
inherently a bug and does not prove causation. A matched low-versus-current-update
pilot would isolate that factor, retain all parent seeds, input representation,
demonstrations, shield and data budget, and align target-network refresh cadence
in environment-time terms rather than inadvertently changing two factors.

Specify and test that experiment before issuing a user-run command. Do not
silently change PER, reward, shield, learning rate and update budget together.
No further long training, final-test sweep or model promotion was performed here.

Follow-up: the [update-pressure protocol](../protocols/UPDATE_PRESSURE_PROTOCOL_20261016.md)
now specifies the matched 4-versus-32-update pilot and its user-run launcher.
Preparation is not evidence that the hypothesis improves performance.
