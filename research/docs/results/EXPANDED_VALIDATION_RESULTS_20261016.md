# Expanded validation results — 2026-10-16

## Decision

**No clear improvement over the parent policies or matched-shield Max-Pressure.**
Keep the current defaults and checkpoints unchanged. Do not spend another batch
on identical training or describe these results as universal RL superiority.
These are useful, reproducible negative findings, not a publication-readiness
certificate. Simulation-only scope remains in force.

## Scope and evidence

Following the user-run margin-release pilot, the
[protocol](../protocols/EXPANDED_VALIDATION_PROTOCOL_20261016.md) froze the constant-arm
selections before this evaluation: seed 101 episode 120 and seeds 202/303 initial
checkpoints. The latter two have unchanged policy weights from their parents;
they are retained in all aggregate reporting. No post-evaluation selection was
performed. This is not an estimate of the causal effect of margin release.

The earlier paired pilot's common candidate grid showed only 0.028 s mean
selected-delay improvement for release, all from seed 101. At episode 90 release
was 5.33% worse than constant. This does not support adopting full margin release.

This expanded screen uses five additional traffic seeds (24001–24005), all
three existing validation templates and clean/mixed sensing conditions. It is
development validation, not an independent final test or unseen scenario-family
evaluation. Each of three parent/candidate pairs contributes 60 simulations;
five classical references contribute 150, for **330 complete runs**. All learned
policies have the same shield enabled and uncertainty fallback disabled. They
must not be labelled the full FlowSync-UQ method.

- [Machine-readable report](../../../results/expanded_validation/constant_20261016/report.json)
- [Archived postprocessor](../../../results/expanded_validation/constant_20261016/postprocessor.py)
- [Pilot comparison](../../../results/research_training/margin_release_6usc2j0j/comparison.json)

## Results

Means give each fixed scenario/fault/traffic-seed cell equal weight; learned
policies also average all three training replicates. Tail delay is the average
of within-run p95 values, **not** a pooled vehicle-level percentile.

| Controller | Runs | Mean delay (s) | Average within-run p95 (s) | Mean passed vehicles |
| --- | ---: | ---: | ---: | ---: |
| Candidate D3QN + shield | 90 | 11.497 | 39.951 | 89.078 |
| Parent D3QN + shield | 90 | 11.497 | 40.417 | 89.044 |
| Max-Pressure | 30 | 11.245 | 41.911 | 87.667 |
| Max-Pressure + shield | 30 | 11.436 | 40.014 | 89.467 |
| Greedy | 30 | 11.482 | 43.782 | 87.367 |
| Fixed | 30 | 14.663 | 39.634 | 85.467 |
| Actuated | 30 | 14.721 | 60.493 | 80.367 |

Descriptive crossed-bootstrap intervals use 5,000 draws over three training
replicates and five traffic seeds, with the six scenario/fault conditions fixed.
Positive saved seconds favor the candidate. These are unadjusted exploratory
intervals with few independent training replicates, not universal guarantees.

| Primary comparison | Mean delay saved (s), 95% interval | Within-run p95 saved (s), 95% interval |
| --- | --- | --- |
| Candidate vs parent | +0.00012 [-0.172, +0.146] | +0.466 [-0.046, +1.852] |
| Candidate vs Max-Pressure + shield | -0.061 [-0.450, +0.229] | +0.063 [-2.003, +2.278] |

Both primary mean and tail intervals cross zero. Neither superiority nor
equivalence is established. The candidate's 21.6% lower point-estimate mean
delay than Fixed is encouraging relative to that baseline, but is not evidence
of novelty or superiority to stronger controllers.

Seed 101's candidate averages 11.39877 s versus its parent's 11.39913 s: the
earlier selected mean-delay improvement did not carry over to these seeds.
Its average within-run p95 is 1.398 s lower. Seeds 202 and 303 are unchanged
(11.58393 s and 11.50817 s respectively). The aggregate tail improvement against
parents remains inconclusive. On clean observations the candidate slightly
improves mean delay over its parent; under mixed faults it slightly regresses.
Do not select only the favorable seed, sensing condition or secondary metric.

## Integrity and tests

Verified exact planned cells without missing/duplicate rows, finite metrics,
checkpoint/scenario hashes, archived source bytes and matching arrival traces
across all four evaluation panels. All panels share the same source archive
SHA-256 `2063dda0981091c76240126b2452141e7f385b7bf2df673374b3dea27b13e4d6`.
The actual separately developed postprocessor is preserved alongside the report,
with SHA-256 `d20dc3fad0c3c951b04fa4e3ad5e854359533877dfee95b29654418f95d8f9a1`.
The report records input hashes and provenance; simulation archives were not
rewritten to include later reporting code.

All **396,000 simulated steps** have signal-audit samples, with **zero measured
signal conflict/clearance violations**. This does not measure collision risk,
pedestrian safety or deployment reliability. Candidate policies had 85 shield
interventions, parents 87, and shielded Max-Pressure 24 over their respective
run counts; these raw totals have different denominators.

The targeted regression suite passed **185 tests** (including evaluation panel,
provenance, training, controller, simulation and statistics coverage). Passing
tests does not establish simulator realism or algorithmic superiority.

## Practical next decision

1. Preserve these results and the prior frozen final evaluation; no website
   promotion, further identical training or new final-test sweep is justified.
2. Start the paper's methods/results/limitations from verified evidence: learned
   performance relative to Fixed, matched strong baselines, sensing assumptions,
   shield efficiency/fairness trade-offs and the negative fallback/margin results.
   Do not claim full UQ adds an established benefit or that novelty is proven.
3. A new performance experiment needs a materially different, specified training
   hypothesis and a repeatable validation gain across training seeds before a
   fresh frozen test. More episodes alone are not supported by this evidence.
4. Independent simulator validation and a contribution/literature assessment
   remain prerequisites for a defensible paper claim. Real-camera or live-signal
   deployment remains outside the validated scope.

No additional training was launched for this screen. The requested goal of
outperforming every mode remains **unachieved**; there is no honest guaranteed
quick tuning change that these results establish.
