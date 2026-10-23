# Frozen evaluation of domain-randomized training

Specified before executing this evaluation. Simulation-only; no deployment or
publication-readiness claim follows automatically from these results.

## Frozen inputs

- Training batch: `results/research_training/domain_rCXu3gDe`.
- Include all three independent training seeds: 101, 202, 303.
- Use each run's existing validation-selected checkpoint: warmup, episode 700,
  warmup respectively. Do not select a different checkpoint after this test.
- Traffic seeds: 61001–61020. Reject overlap with the previous main and
  long-horizon evaluation manifests (51001–51020 and 52001–52003).
- Seven existing test scenario templates, all clean; additionally balanced
  traffic under miss_30, latency_1000ms and combined_severe.
- Four classical controllers: Fixed, Actuated, Greedy and Max-Pressure.
- Evaluate D3QN and FlowSync-UQ for every training replicate: 2,000 runs total.
- Preserve the previously fitted uncertainty calibration at
  `results/uncertainty_calibration/pilot_20261014/calibration.json` unchanged.
  This was fitted with a different policy; transfer is a limitation, not a
  calibration claim for the new models. Do not refit using these test outcomes.
- The evaluator freezes checkpoint/calibration/scenario/source hashes and this
  protocol. All methods receive paired arrivals and the same sensor-fault model.

## Analysis and interpretation

Primary outcome: average finite-horizon vehicle waiting delay over the seven
clean scenarios, aggregated across all three training replicates and 20 traffic
seeds. Primary comparison: D3QN versus Max-Pressure. Report all other baseline
comparisons, all ten condition cells, and UQ versus its own underlying D3QN.
Report within-run p95 delay, throughput and measured signal audit violations.
Use the existing crossed training-seed/traffic-seed bootstrap, 5,000 draws, with
descriptive 95% intervals. Do not present these as multiplicity-adjusted tests.

These traffic seeds are fresh, but scenario families were inspected previously.
This is a fresh-seed generalization check on a known benchmark, not an unseen
scenario study. Validation means from the new batch cannot be compared directly
to old test means. Do not hide losses, drop a training seed, or retrain/reselect
until this test wins. A poor outcome remains evidence for the next explicitly
separated development experiment.

The new recipe changes domain randomization, training horizon, demonstration
volume and loss weight together. This comparison cannot attribute a gain to any
single change; matched ablations remain necessary. Two chosen policies are
warm-start checkpoints, so any aggregate gain must not be described as evidence
that 900 online RL episodes consistently help. Independent simulator validation
and realistic sensing remain open requirements.
