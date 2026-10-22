# Complete arrival-label panel: single-future choices are unstable

Verified input: `results/arrival_label_stability/panel_20261021T063020Z`.
[Protocol](ARRIVAL_LABEL_PROTOCOL_20261020.md).

All 18 sources completed in 837.44 seconds (13.96 minutes): three unchanged
parents, six training scenarios, clean sensing and source traffic seed 95001.
There are 54 gates, 125 non-parent alternatives and eight independently
resampled future-arrival streams per gate. All actions within each future
received exactly paired arrivals; all eight traces are distinct at each gate.

## Results

- 75/125 alternatives (60.0%) have both positive and negative delay gains
  across futures, using the prespecified +/-1 vehicle-second thresholds.
- 41/54 gates (75.9%) change their constrained hindsight-best choice across
  futures. This is a label comparison, not an online controller decision.
- 21 gates have an originally qualified beneficial choice. Across 168 new
  future cases for those choices, 56 remain qualified (33.3%), 108 are harmful
  (64.3%) and four are neither under the prespecified multi-metric criteria.
- Only 3/21 originally qualified choices remain qualified in at least six
  of eight futures.
- All 666,000 recorded source/branch signal samples have zero measured
  violations. This is not a road-safety guarantee.

| Parent | Alternatives changing delay-gain sign | Original qualified-choice gates | Qualified new cases | Harmful new cases |
| --- | ---: | ---: | ---: | ---: |
| 101 | 29/43 | 10 | 24/80 | 53/80 |
| 202 | 26/45 | 6 | 20/48 | 28/48 |
| 303 | 20/37 | 5 | 12/40 | 27/40 |

These are correlated descriptive samples from one source traffic seed, not
independent final-test observations. Future-arrival randomness changes many
labels at these states, but this does not prove that it explains every earlier
prediction failure or that DQN learning is fundamentally defective. Nothing
here demonstrates a better full-run traffic controller.

## Verification

All input/checkpoint/source-archive/output hashes verified. All 18 saved source
trajectories and original single-future action labels exactly match the fitting
records. Scenario/parent coverage, gate selection, future-seed derivation,
candidate actions and paired arrival hashes were checked. Saved event/report
outputs reproduce; sign-flip and benefit/harm counts were also recomputed
directly from the raw branch outcomes independently of the report functions.
This verification did not rerun all 18 simulations.

## Next experiment

The [averaged-label protocol](AVERAGED_LABEL_PROTOCOL_20261021.md) freezes
parent, single-future and mean-eight-future choices at every existing gate,
then evaluates them on separate new futures. It does not retrospectively split
the already inspected eight streams and call some of them unseen. Fresh full
evaluation IDs are 8–15; mechanics-smoke IDs are 100–107. No fitted policy or
checkpoint is produced. Details and command are in
[the next experiment note](AVERAGED_LABEL_RESULTS_20261021.md).
