# Shield and fallback intervention audit

Development-only diagnosis, not a new final test or a parameter-selection sweep.
Existing test results and their source snapshots are preserved unchanged.

## Method and integrity

Use all three selected v5 pilot checkpoints, the unchanged fitted calibration,
the three validation templates, traffic seeds 21001/21002, and the existing
clean/mixed validation fault profiles. All 36 rollouts completed. The manifest
records checkpoint/scenario/calibration/source hashes; `source_snapshot.zip`
preserves the exact source used before subsequent audit-counter corrections.

At each shield override or fallback entry, log the observed phase timer and
offline actual accumulated stopped waits for upstream vehicles/backlog. Ground
truth is used only by the auditor, never passed into controller observations.
Vehicles already beyond the stop line are excluded from this upstream-wait audit.

Fork the first two eligible events of each kind per rollout into two identical
simulation/perception/controller states. Both branches receive identical future
arrivals and the same fault model. Run each branch for 200 ticks (20 simulated
seconds). A shield comparison omits **only that tick's override**, retaining
future shield decisions and the mandatory physical FSM. A fallback comparison
disables fallback for the entire branch horizon but keeps the shield enabled.
These are different interventions; do not conflate their effects.

Use total incremental waiting, in **vehicle-seconds**, over the branch horizon.
This is not per-vehicle mean delay or the full-run selection metric. Also record
throughput and the largest remaining upstream accumulated wait at the endpoint.
All 65 paired comparisons had matching arrival hashes and 200 signal-audit
samples per branch, with zero observed conflict/clearance violations. Unit tests
verify that forks do not mutate the source trajectory or its policy state.

Events are deliberately the first eligible events, not a random representative
sample. Some states repeat across policy seeds. These observations are correlated;
do not report the counts as independent trials, p-values or proof of long-run benefit.

## Findings

### Shield: genuine fairness/efficiency tension

There were 41 overrides, all anti-starvation for left-turn phases (21 phase 2,
20 phase 3). Of 38 horizon-eligible comparisons, keeping the override reduced
incremental total delay once and increased it 37 times. The mean increase was
86.36 vehicle-seconds over 20 seconds, with 6.26 fewer vehicles passing.

However, keeping the override reduced the endpoint largest upstream wait in
22 comparisons, increased it in seven, and left it unchanged in nine. The mean
reduction was 8.79 seconds. Omitting an override is therefore **not** uniformly
better: lowering aggregate delay can leave the least-served vehicles waiting.
Endpoint maxima also depend on which vehicles remain; they are not a pooled
completed-trip percentile or a guarantee that every individual improved.

The targeted phase's largest actual accumulated wait at override ranged from
42.2 to 73.9 seconds (mean 53.33). Nine overrides occurred below 45 actual seconds.
This does not prove incorrect rule execution: the configured rule uses a phase
service proxy, not an individual waiting deadline.

### Fallback: perception-error probability is not benefit probability

There were 30 fallback entries, all under mixed validation faults and none
triggered by the hard stale-frame threshold. Mean uncertainty at entry was
0.75719. Of 27 horizon-eligible comparisons, keeping fallback improved total
delay seven times, worsened it 14 times and had no effect six times. Mean total
delay increased by 6.59 vehicle-seconds; throughput decreased by 1.04 vehicles.

The audit does not establish a new threshold. It demonstrates why a model
predicting count error is not enough to justify switching controllers: the
backup consumes the same corrupted sensor stream, and high predicted count
error does not establish its advantage over the learned policy.

## Confirmed implementation/measurement issues

1. The observed phase-service timer resets on green or a zero observed count.
   It does not track individual vehicles, verify a discharge, or remember a
   missed vehicle's wait. It also includes approaching demand. Tests now
   explicitly demonstrate green and missed-count resets while a true vehicle
   still has 60 seconds of accumulated wait. Semantics are exposed in research
   telemetry; no hidden ground-truth wait feature was added to the controller.
2. During yellow/all-red, the shield returned `was_overridden=True` for a changed
   request but did not increment its aggregate override counters. This audit
   accounting defect is corrected and regression-tested. The executed action
   is unchanged; it is **not** an explanation for the observed efficiency gap.
3. Documentation no longer calls this rule-based component a formal guarantee
   of real-world safety or a bound on individual vehicle wait.

No checkpoint, threshold, action-selection rule, physical clearance or minimum
green protection was changed by this audit. The stop-line constant was lifted
to module scope for a shared diagnostic reference without changing its value.

## Next development decision

- Do not retrain the same RL recipe simply for more episodes or remove fairness
  protections to manufacture a lower mean delay.
- A fairness-aware policy needs a stated objective: phase-service fairness and
  an individual vehicle-wait bound are not interchangeable. Actual individual
  waits require observable tracking or an explicitly uncertain estimate; the
  current count-only surrogate cannot supply a proven bound.
- Train any benefit-aware fallback gate using **training-only** paired rollout
  labels and observable features, with a predeclared horizon and fairness cost.
  Assess it on separate validation cases before a new frozen test. These 36
  validation runs must not become gate-training data.
- Keep the physical signal FSM intact and preserve a separate hard fault path.
  Short-horizon benefit prediction alone is not a safe real-world supervisor.

Artifacts: `results/intervention_audit/validation_20261016/manifest.json`,
`runs.jsonl`, and `source_snapshot.zip`. The completed frozen evaluation at
`results/replicate_evaluation/matched_shield_v5_20261015` remains unchanged.
