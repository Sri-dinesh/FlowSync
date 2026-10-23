# Draft addendum: observation specificity, action use and simulator hindsight

Simulation-only development evidence for the manuscript scaffold. This is
new dated text, not a revision to the frozen 2,800-run evaluation sample or
its statistical estimates. Novelty and external simulator validation remain open.

## Research questions

We distinguish three questions: whether more geometrically specific observed
demand improves a learned policy; whether the trained network uses those
inputs to change decisions; and whether alternative teacher choices improve
outcomes under separate stochastic futures. A failure at one stage should not
be attributed to another without an intervention that isolates the mechanism.

## Matched spatial-input ablation

The historical movement count includes vehicles that have crossed the stop
line but remain in the simulated scene. An additional twelve-component packet
counts vehicles at or before the stop line, under the same documented backlog
visibility assumption. The fault adapter jointly partitions detections and
preserves packet latency/drop behavior. Both arms share the 48-input network,
parent checkpoints, training budgets and sensor pipeline. The control zeros
only the new inputs. Both retain the original delivered-demand mask, additional
shield and physical signal FSM. New input weights initially equal zero, so
initial policy outputs match their parents.

All six runs complete 90 online episodes and 360 optimizer updates. At the fixed
endpoint, spatial mean stopped waiting per arrived vehicle is 10.840583 s,
versus 10.783722 s for control and 10.841389 s for unchanged parents. The
spatial arm fails its prespecified continuation screen. These development
cells were reused and do not constitute independent confirmation.

A training-only audit evaluates natural versus zero spatial inputs at the
same delivered states. Spatial input columns become nonzero and Q values
change, but the episode-90 proposals do not change at any of 320 inspected
policy gates. On spatial-policy states, mean maximum absolute Q change is
0.863911, while the mean range of the Q changes across valid actions is
0.099808 and the mean action margin is 2.170554. The input effect is therefore
largely shared across action values in this panel. This is a descriptive
comparison of means, not a pointwise bound or proof of universal irrelevance.
The lack of proposal changes cannot be explained by shield suppression.
Different arm checkpoints still differ in their shared weights and replay;
zeroing inputs at inference does not undo their effect during learning.

## Frozen teacher proposals under separate futures

We replay nine recorded randomized training configurations under the final
spatial policies. Before collecting new outcomes, we select the first two
eligible historical/upstream Max-Pressure disagreements per source, retaining
sources with no eligible gate. Seven gates qualify: five, one and one for
training replicates 101, 202 and 303. At every selected gate the policy agrees
with the historical teacher in holding the current phase; the upstream teacher
requests a switch. Policy/historical branch outcomes are duplicates.

At each gate, two sets of eight disjoint future arrival RNG keys are frozen.
Branches preserve the observed history, pending traffic, signal state,
perception state, shield and decision schedule. Only the first held proposal
changes; subsequent decisions use the same natural continuation policy.
Source trajectories reproduce exactly after branching. The first and separate
check sets have 56 paired gate/future cases each, which remain correlated
within states and training replicates.

At 20 seconds, the upstream substitution adds 6.623214 vehicle-seconds of
stopped delay in the first set and 5.339286 in the check set. Throughput falls
by 1.071429 and 0.946429 vehicles per branch, respectively, while endpoint
maximum accumulated waiting decreases. Only two of seven gates satisfy the
prespecified six-of-eight joint non-harm condition with a strict benefit.
The teacher-alignment continuation screen fails.

## Fixed-prefix horizon diagnostic

After freezing a separate explanatory protocol, we extend the same branches
to 60 seconds. Every original 20-second prefix reproduces exactly, including
component rewards, switch counts, arrivals and endpoint waiting. We do not
replace the failed teacher-training screen or select the best horizon.

| Arrival-stream set | Delay saved at 20 s (vehicle-seconds) | Delay saved at 60 s (vehicle-seconds) | Throughput gained at 60 s |
| --- | ---: | ---: | ---: |
| First | -6.623214 | 4.430357 | -0.196429 |
| Separate check | -5.339286 | -5.137500 | -0.428571 |

The apparent longer-horizon gain in the first set does not persist in the
separate set; even the favorable set loses throughput. All three training
replicates have negative mean delay savings in the separate set at 60 seconds.
Pooling sets gives -0.353571 vehicle-seconds of saved delay and a throughput
loss, rather than a reliable benefit. The extension uses future streams
already inspected at 20 seconds and is exploratory. It is not a fresh final test.

## Interpretation and limits

More specific geometry can change numerical predictions without changing
actions. Similarly, a favorable action estimate in one set of simulator futures
need not persist in another, even at fixed observed starting states and fixed
choices. The teacher substitutions also expose an efficiency/endpoint-wait
trade-off. These observations motivate distinguishing perceptual fidelity,
action-value sensitivity, future-stable action advantage and realized full-run
controller improvement as separate empirical questions.

This study does not establish a novel algorithm, a calibrated conditional
benefit bound, superiority over strong controllers, or real-world readiness.
Spatial pressure representations already appear in
[Advanced-MP/Advanced-XLight](https://arxiv.org/abs/2112.10107); learned switching
curves already appear in [Wang et al.](https://www.sciencedirect.com/science/article/pii/S0968090X22001139);
and counterfactual traffic control is studied by
[CFLight](https://arxiv.org/abs/2512.09368). The candidate contribution here is
an empirical evaluation/target-stability analysis, whose novelty and value
still require comparison against the wider literature and replication in an
independent simulator. Zero measured simulated-lamp violations do not certify
collision or deployment safety.

Evidence authority: the spatial-input, input-use, teacher-alignment and horizon
protocols/results; preserved raw artifacts and archived sources. Generated
CSV/PNG/SVG and their hashes are in
`results/paper_evidence/teacher_diagnostics_20261022`. No development samples
are pooled into the manuscript's earlier frozen evaluation or its intervals.
