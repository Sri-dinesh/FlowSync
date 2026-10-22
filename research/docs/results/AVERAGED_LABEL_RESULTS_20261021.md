# Averaged labels: full frozen-choice experiment passed its development screen

Implementation: `research/evaluate_averaged_action_labels.py`.
[Protocol](../protocols/AVERAGED_LABEL_PROTOCOL_20261021.md).
Input: `results/arrival_label_stability/panel_20261021T063020Z`.

## Completed full panel

Verified output: `results/averaged_action_labels/panel_20261021T091742Z`.
All 18 sources completed in 728.23 seconds (12.14 minutes). The 54 choices
have exactly the same SHA256 as the pre-evaluation smoke's frozen file:
`a4721b9961227e4da8fd12d2444dfbdfa872147a9f84f7dc76bfa11dbe414ad0`.
Evaluation future IDs 8–15 are disjoint from selection and smoke streams.

| Arm | Mean delay saving vs parent, vehicle-seconds | Changed gates / 54 | Qualified changed cases | Harmful changed cases |
| --- | ---: | ---: | ---: | ---: |
| Parent | 0.000 | 0 | Not applicable | Not applicable |
| Single | -1.975 | 21 | 62/168 | 102/168 (60.71%) |
| Mean8 | +1.071 | 9 | 41/72 | 28/72 (38.89%) |

Means include all 432 gate/future cases per arm, with equal source weighting.
These are vehicle-seconds saved over 40-second branches, NOT seconds saved
per vehicle or full-run mean delays. Mean8's throughput and endpoint-wait
gains are +0.0208 vehicles and +0.0507 seconds. All three parent-level delay
means are positive (0.4125, 1.4764, 1.3229), but source-level gains are positive
in five sources, zero in eleven and negative in two. Not every traffic case
improves. The remaining harmful fraction is material.

All predefined development checks pass. This justifies a small observed-input
model pilot, not promotion, calibrated safety, significance or superiority
over full-run baselines. These choices were obtained using simulator outcomes,
not learned predictions, and cover only one source traffic seed with clean
sensing. No DQN or production controller changed in this experiment.

Verification covered input/checkpoint/source/output hashes, all 18 original
replays, exact old-data reconstruction of frozen choices, future disjointness,
action/arrival pairing, score/report reproduction and independently computed
means and benefit/harm counts. All 666,000 recorded source/branch signal
samples have zero measured violations; this is not real-world safety evidence.

Next: [observed-input model pilot](AVERAGED_LABEL_MODEL_RESULTS_20261021.md).

## Implementation and historical smoke

The runner validates the prior panel and fitting-source provenance, freezes
all 54 choices from existing outcomes, and only then evaluates new futures.
It records three arms at every gate: unchanged parent, original single-future
choice, and choice from eight-future mean gains. Means exclude the original
single-future sample. Selection thresholds and shields stay unchanged.

The saved `frozen_choices.json` hash is recorded before any evaluation and
rechecked afterward. Full evaluation uses future IDs 8–15; the separate
mechanics smoke uses 100–107. All actions within a future are paired, and the
complete original source and original branch outcomes must replay exactly.
Raw branches, per-future arm scores, per-source aggregates, provenance and
all screen checks are saved. Partial runs cannot pass the continuation screen.

This is an offline label-quality experiment using simulator outcomes, not
a deployable predictor, retrained DQN or live-lookahead controller. It cannot
establish superiority over Max-Pressure or other full-run baselines.

## Completed mechanics smoke

Output: `results/averaged_action_labels/smoke_20261021`.
All 54 choices were frozen before evaluation. Across the full selection panel,
single changes 21/54 proposals; mean8 changes 9/54 (parents 101/202/303: 1/5/3).
These are choice counts, not evidence that the changed actions are beneficial.

The separate-stream smoke completed the first source in 46.83 seconds using
IDs 100–107. Parent 101, `train_ew_asymmetric_01`, source seed 95001:

| Arm | Changed gates / 3 | Qualified / changed future cases | Harmful / changed future cases | Mean delay saving vs parent, vehicle-seconds |
| --- | ---: | ---: | ---: | ---: |
| Parent | 0 | Not applicable | Not applicable | 0.0 |
| Single | 1 | 2/8 | 6/8 | -2.0 |
| Mean8 | 0 | Not applicable | Not applicable | 0.0 |

The mean8 arm retains the parent throughout this source: it avoids the
single-future choice's observed loss here but achieves no improvement over
the parent. The smoke cannot pass the full-panel continuation screen.
All 37,200 source/branch signal samples have zero measured violations.
No full evaluation futures (IDs 8–15) have been consumed.

72 targeted tests passed. Source/input/output/frozen-choice hashes, all
54 old-data choice reconstructions, exact source replay, future split, saved
score rows and report reproduction were verified. Arm means were independently
recomputed from raw branch outcomes. Tests cover future-label exclusion,
separate stream sets, invalid/duplicate records, action and signal checks,
incomplete/smoke handling, abstention, risk and parent-level regression gates.

## Full panel command

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u \
  research/evaluate_averaged_action_labels.py \
  results/arrival_label_stability/panel_20261021T063020Z \
  --output "results/averaged_action_labels/panel_$(date -u +%Y%m%dT%H%M%SZ)" \
  --max-wall-seconds 1800
```

Allow roughly 15 minutes based on the previous comparable panel; actual time
varies. The cooperative simulation budget is 30 minutes. Expect 18 sources
and `full_panel_complete: true`; that means execution completed, not that the
method improved. `continue_to_label_model_pilot` separately reports whether
every prespecified development check passed. No model is trained or uploaded.
