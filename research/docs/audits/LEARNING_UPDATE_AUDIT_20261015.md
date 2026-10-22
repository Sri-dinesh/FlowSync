# Learning-update audit

## Negative experimental result

The user completed `results/research_training/shield_mW0ZwjUP`: all three runs
finished 900 episodes and full warmup in about 27–28 minutes. Matched shield-only
validation means were 10.8631/10.8202/10.9508 s versus the control selections'
10.7702/10.7728/10.8106 s. Aggregate mean delay increased from 10.7845 to
10.8781 s (about 0.87%). Aggregate within-run p95 increased from 38.1901 to
38.3433 s, throughput from 84.5667 to 84.9667 vehicles, and starvation events
from 191 to 192. These are selection/validation results, not independent tests.

Selected checkpoints: episode 100, warmup, episode 100. Selected hashes,
selection minima, 30 matched validation cells per seed, and complete episode
counts were checked. Do not promote this recipe as an efficiency improvement.

## Confirmed defects

### Repeated switch charge

The v4 reward detects a switch using a `time_in_phase < 0.15` yellow condition
and also a physical phase-ID change. One transition produces three charges:
at yellow entry (tick 0), the following yellow tick (tick 1), and new green entry
(tick 50). The v5 research reward uses a GREEN-to-YELLOW edge and charges exactly
once. Blocked requests incur no charge. Regression tests establish unchanged
physical traffic trajectories across these reward versions.

The research runtime explicitly selects `v5_single_switch_delay`; research
checkpoints and manifests record it. Old v4 files and source archives remain
untouched. The default website environment/trainer still use legacy v4 for
compatibility: this is a research-path correction, **not** a website migration.
Website checkpoint compatibility/resume behavior needs separate integration
work before promoting new models there.

### Incomplete macro-action bootstrapping

Research collection previously stored the final pending action at the episode
cutoff even when its two-second hold or clearance/minimum-green interval had
not completed. It bootstrapped as though this were a new decision state. The
decision-value network is trained at decision gates, not these intermediate
states, so that target is not the same semi-MDP transition used elsewhere.

The corrected research collector stores only completed decision-to-decision
transitions, including one ending exactly on the horizon. It drops and counts
the final incomplete transition instead of inventing a terminal value or
bootstrapping an intermediate state. All physical steps and reported traffic
metrics still cover the original horizon. This discards some boundary experience;
it does not solve finite-horizon learning. The separate legacy website collector
has not been migrated by this change.

## Checks that did not reveal the suspected defect

- Numerical Double-DQN tests verify masked online action selection, target-network
  evaluation, variable-duration discounts and terminal masking.
- The domain batch contains about 33k total transitions per run; the shield
  batch about 32k–33k. Both are below the 100k replay capacity. Demonstration
  eviction by buffer wraparound did not cause these runs' degradation.
- Growing negative Q values alone do not prove divergence when accumulated
  rewards are predominantly negative. Weighted loss and raw TD error differ.
- Six no-learning rollouts of the old seed-202 policy on training templates
  (300-second horizons, traffic seeds 71001–71006, clean observations) found v5
  switch components around -0.57 to -0.76 versus delay components around -46 to
  -352. The switch defect is real but small relative to the main reward in this
  diagnostic; it is not established as the explanation for the controller deficit.

## Instrumentation and verification

Episode logs now include reward component totals and dropped partial-transition
ticks. Training diagnostics add sampled demonstration fraction, importance-weight
mean, mean bootstrap discount, target-Q mean, and weighted demonstration loss.
Historical logs cannot reconstruct sampling fractions or prove that zero margin
loss means demonstrations were absent.

103 targeted regression tests passed, including reward edge-counting, cutoff/gate
semantics and numerical TD-target checks. The short integration run at
`results/research_training/learning_audit_smoke_20261015` completed in 29 seconds,
with two TD warmup updates and 44 online updates, finite weights and verified v5
checkpoint metadata. This is not evidence of traffic superiority.

No long batch, threshold search or new final test was launched. Any next pilot
must retain validation-only selection, identify the new reward/replay semantics,
preserve old negative results and precede a separately frozen final evaluation.
Existing final-test traffic-delay results remain valid for their frozen policies;
total reward values across v4/v5 are not directly comparable.

## Full-curve artifact cross-check

The read-only `research/audits/audit_training_results.py` independently recomputed all
33 completed candidate scores in the old shield batch, verified checkpoint-file
hashes and paired arrivals, and confirmed the saved selections. It also checked
the three v5 integration-smoke candidates. No new training or final tests ran.

| Training seed | Warmup delay | Selected delay | Episode-900 delay |
| --- | ---: | ---: | ---: |
| 101 | 10.918733 | 10.863133 | 10.865333 |
| 202 | 10.820233 | 10.820233 | 11.001400 |
| 303 | 10.950900 | 10.950833 | 10.992567 |

Seconds, same validation design; not independent final-test evidence. Online
learning improves the best recorded delay over warmup by only 0.0556 s, 0 s,
and 0.000067 s respectively. Most of the improvement over random initialization
is already present after demonstration imitation and TD warmup. This supports
inspecting the online-learning trajectory in the v5 pilot rather than assuming
more episodes will improve the policy. It does not isolate imitation from TD
warmup or establish a causal explanation for the plateau.
