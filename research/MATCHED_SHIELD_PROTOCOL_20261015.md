# Frozen v5 pilot evaluation — matched shield controls

Specified before execution. Simulation only. No more policy training, selection,
shield tuning or uncertainty-threshold changes are part of this evaluation.

## Frozen policy inputs

Use all three existing selections in
`results/research_training/pilot_v5_kbW0lsY3/seed_{101,202,303}/selection.json`:

| Training seed | Checkpoint | SHA-256 |
| --- | --- | --- |
| 101 | warmup | `1cd49647546e2f68763524d5a26028ea4c3dfc8d0ec9e713d0a3a1119884a725` |
| 202 | 50 | `a91e038dbe9cdb1d2ce35a36ff40a1fa245bc4cbc8480fe9b74f22d5082d7dc4` |
| 303 | 100 | `e0b830b43d6023f859bae07e2e7b45f5b46393adebb20a1bd0ec951d62d1e052` |

The ten-minute runs completed 223/223/219 online episodes respectively, after
200 demonstrations, 2,000 imitation updates and 500 TD warmup updates each.
Selection used shield-on/fallback-off mean validation delay. Only these selected
checkpoints are evaluated; do not replace them using the outcomes here. The
warmup selection is not evidence that online RL helped that training replicate.

## Crossed design

- Traffic seeds 81001–81020, not present in the earlier evaluation manifests.
- Seven existing test scenario templates with their original durations, clean.
- Three additional conditions on balanced traffic: miss_30, latency_1000ms,
  combined_severe. Ten fixed scenario/condition cells in total.
- Baselines: Fixed, Actuated, Greedy, Max-Pressure, and Max-Pressure with the
  same `SafetyShield.filter_context` used by shielded D3QN.
- For each of the three trained checkpoints: bare D3QN, shielded D3QN with
  fallback disabled, and full FlowSync-UQ. Same checkpoint, not separately
  selected or retrained for each intervention.
- Full UQ uses the unchanged fitted calibration at
  `results/uncertainty_calibration/pilot_20261014/calibration.json`, SHA-256
  `272d10a0968dc9be7a295f1f8baf7b53497da34a37b28ec76aa6fc635404e521`.
- 14 controller/replicate labels × 10 conditions × 20 traffic seeds = 2,800
  simulations. Classical baselines are run once per cell, not counted as
  independent training replicates.
- All controllers get the same causal sensing/fault model and paired arrival
  streams. Baseline decision rules and the RL decision hold are unchanged.
  Physical minimum-green/clearance FSM remains enabled for all methods;
  no hidden environment watchdog. Shielded comparisons share the same
  max-green/anti-starvation/demand guards.

## Outcomes and attribution

Primary comparison: shielded D3QN versus shielded Max-Pressure, mean waiting
delay across all ten condition cells (equal condition weights), all training
replicates and all traffic seeds. Also report the seven-clean subset and
comparison against unshielded Max-Pressure. Report every controller and loss.

Secondary outcomes: average within-run p95 delay, throughput, starvation events,
shield interventions, fallback steps and actual executed-signal audit coverage
and violations. Within-run p95 averages are not a pooled vehicle percentile.
The 7.9% lower validation p95 motivated this check but is not independent
evidence. Compare shield effects on both D3QN and Max-Pressure; compare full UQ
with the same shield-only D3QN to isolate fallback's effect.

Use crossed training-replicate/paired-traffic-seed bootstrap (5,000 draws) for
mean and specified p95 contrasts. Intervals are descriptive, not multiplicity
adjusted; three training replicates are a limitation. A classical-versus-classical
contrast has no independent training variation; its identical replicate axis
must not be described as three trained baseline models.

Store checkpoint, selection, scenario, calibration, source and protocol hashes,
the exact job plan, raw runs and source snapshot. Verify all planned cells,
paired arrivals and every-tick safety coverage before interpreting the report.

## Limits and stop rule

These are new traffic seeds on previously inspected scenario families, not
unseen scenario classes or an independent simulator. All data are synthetic;
finite-horizon waiting delay is not a real traffic travel-time guarantee. The
calibration was fitted with a different policy and predicts count error, not
the benefit of handing control to Max-Pressure on the same faulty sensor input.
Do not refit calibration from these outcomes.

Freeze and report the full result even if all improvements disappear. Do not
reuse these seeds for tuning or selectively extend a winning subset. Any later
development remains a separate validation-only experiment. No universal
superiority, collision safety, real-world readiness or publication readiness
is established merely by a successful run or a favorable mean.
