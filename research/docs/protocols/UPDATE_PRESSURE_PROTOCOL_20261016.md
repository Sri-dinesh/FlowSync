# Matched update-pressure pilot

Status: specified before execution; no performance outcome assumed.

## Question and frozen design

Does reducing learning-update pressure preserve or improve the existing policy,
after the temporal pilot and training-only drift audit found degradation?
Replay reuse is a hypothesis, not a confirmed optimizer bug.

Use all three existing v5 shield-selected parents (training seeds 101, 202, 303).
Freeze parent hashes, source archive, this protocol and launcher into a new
`results/research_training/update_pressure_*` directory before workers start.
Do not alter earlier results, checkpoints or final-test panels.

Both arms use the original `v7_36dim_observed` input and unchanged parent weights;
no temporal expansion. Both collect 24 identical demonstration episodes, then
90 online episodes of 1,200 ticks, with domain randomization and the same
training traffic seeds, scenario schedule, fault parameters and exploration
schedule. No imitation/pretraining updates. Learning rate 0.0001, demonstration
margin weight 0.5, shield enabled, fallback disabled, reward unchanged.

| Arm | Updates after each complete episode | Target copy every N updates |
| --- | ---: | ---: |
| control | 32 | 200 |
| low_updates | 4 | 25 |

Target copies occur at the same fractional episode-update positions (every
6.25 episodes, 14 copies over 90 episodes). This compensating setting preserves
the target-refresh cadence in collected episode time. It does not preserve
target-network age measured in optimizer steps. PER beta remains episode-based.
Replay samples, trajectories, and collected transition counts may differ as
policies learn: this is an online learning-procedure comparison, not a fixed
dataset causal isolation of the optimizer. Exogenous training inputs and
demonstrations must match; the comparator rejects mismatches.

Two sequential waves, three workers each; at most 360 seconds per worker,
plus atomic save/operation overhead. Expected several minutes on the previous
pilot machine, not a runtime guarantee. Do not automatically rerun a timed-out
or negative pilot. Process success alone does not mean the experiment completed.

## Evaluation and continuation decision

Validate initial, warmup, episodes 30, 60 and 90 on existing validation templates,
seeds 21001/21002 and unchanged clean/mixed faults. No final-test access or new
classical-baseline claims. Check source/checkpoint provenance, initial policy
equality, paired arrivals, finite losses/weights, per-arm update counts and
full executed-signal audit coverage.

Primary endpoint: **episode 90 across all six runs**, not each run's selected
best. The latest common earlier checkpoint may be reported descriptively if
budget limits prevent completion, but cannot pass the continuation screen.

For continuation to a separate validation panel, the low-update arm must:

- Reduce mean delay by at least 2% versus both control and initial parents.
- Have no training-seed mean delay regression over 1% versus either comparator.
- Have no aggregate p95 or throughput regression versus either comparator.
- Have zero measured signal violations in every completed candidate and full
  audit coverage; all six runs must complete the primary endpoint.

These are engineering gates, not significance tests or publication readiness.
Report all seeds and intermediate checkpoints; do not discard the low-demand
failure case or change these thresholds after seeing results. Preserve parent
models regardless of outcome. No automatic website promotion, retraining
escalation, test evaluation, or deployment.

New learning telemetry reports unweighted minibatch TD loss, pre-clipping
gradient norm and importance-weight bounds. These are changing-minibatch
diagnostics, not whole-episode losses or performance guarantees.

## User-run command

From the project root:

```bash
bash research/pilots/launchers/run_update_pressure_pilot.sh
```

Inspect the resulting `comparison.json`, each `summary.json` and logs. Status 0
means comparison available, not that the low-update arm won.
