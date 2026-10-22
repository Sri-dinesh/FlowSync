# Opt-in shield-aware training

Status: implemented and the user completed the full matched training batch.
It did not improve aggregate validation delay; see the
[learning-update audit](../audits/LEARNING_UPDATE_AUDIT_20261015.md). The original
experiment specification below is retained as historical protocol.
The previous 540-run validation ablation found a mean-delay/tail-delay trade-off
from anti-starvation interventions. It motivates matching training dynamics to
deployment; it does not justify removing safety/liveness constraints.

## Behavior

Add `--train-with-shield` to `research/train_policy.py` for a **new output run**.
The existing default remains bare D3QN. With the flag enabled:

- Demonstration and online replay collection apply the same `SafetyShield`
  implementation, sensor-only context adapter, thresholds and microtick timing
  as FlowSync-UQ inference. No new privileged simulator inputs are provided.
- Replay stores the proposed policy action. The shield-filtered execution
  determines the reward and next state. This learns the consequences of a
  proposal in the shielded environment, rather than relabeling it as a different
  action after the fact.
- Checkpoint selection runs the policy with the shield enabled and uncertainty
  fallback disabled. Results explicitly label it `d3qn_shield`, not plain D3QN.
- Episode logs record shield interventions and reasons. The manifest records
  shield/fallback flags and replay semantics; `selection.json` records the
  required evaluation controller.
- The bare-policy final evaluator rejects shield-selected models to prevent
  silently evaluating a different controller than the one used for selection.
  A future final evaluation needs an explicitly matched shield-aware protocol.

No website defaults, existing weights, fitted calibration or shield thresholds
are changed. This does not implement decision-risk supervision or fix fallback
selection. Neither automated Supabase promotion nor real-world readiness follows.

## Required matched experiment before a performance claim

Use the same train-only randomized recipe, seeds, observation format, episode
budget and validation cells as the no-shield training control. For that control,
evaluate all its retained candidate checkpoints under the **same shield-only
validation rule**; do not reuse a checkpoint chosen by a different bare-policy
criterion. Freeze selections before any new test and retain all training seeds.
Report both mean and tail delay, throughput, starvation and interventions.
Previously inspected test outcomes must not select checkpoints or thresholds.

The opt-in flag and short integration checks establish execution compatibility,
not that the resulting policy will outperform the old policy or Max-Pressure.

## Matched experiment specification (before new training)

At specification time, no full shield-aware batch had started. The batch changes
only the collection shield relative to the completed domain-randomized recipe:

- Fresh training seeds 101, 202 and 303; no parent checkpoint.
- v7 observations; 900 online episodes; 200 demo episodes; 2,000 imitation and
  500 TD pretraining updates; learning rate 0.0001; target sync every 200 updates.
- Train-only domain randomization, 3,000 microticks per episode, demo loss
  weight 0.5, validation every 100 episodes including initial/warmup candidates.
- All three validation templates, traffic seeds 21001–21005, clean and mixed
  faults. Same minimum-mean-delay selection and incumbent-on-ties rule.
- Shield enabled during collection and validation; fallback disabled. No
  threshold, reward, observation or architecture changes in this experiment.
- For a user-approved 60-minute batch, use a 3,300-second cooperative limit per
  concurrent run to leave startup/reporting margin. Record actual completed
  episodes; an incomplete run is not a matched 900-episode experiment.

The old-recipe controls are selected by `research/select_shield_control.py`
under the same shielded validation rule. Its outputs are separate from original
training outputs. All 11 scheduled checkpoints per seed are evaluated, with
checkpoint/source/scenario hashes and original fault profiles checked. This
selection is validation-only; it does not overwrite the original final test.

Compare both training recipes under the same shield-only evaluation controller
and include the strong classical baselines. New final-test seeds and protocol
must be declared before looking at new test outcomes. Report all training runs,
including any warmup winners or negative results. The unresolved fallback-risk
model is deliberately outside this single-variable training comparison.

## Completed control selection

All 990 validation cells completed and checkpoint/source provenance passed.
The separately selected bare-training controls under shield-only evaluation are:

| Training seed | Selected checkpoint | Shielded mean validation delay |
| --- | --- | ---: |
| 101 | warmup | 10.7702 s |
| 202 | episode 400 | 10.7728 s |
| 303 | episode 500 | 10.8106 s |

Artifacts are in
`results/validation_comparison/shield_control_selection_20261015_seed{101,202,303}`.
These replace no original selections. Two controls differ from their original
bare-policy selections, demonstrating why a matched selection rule matters.
The user chose to run the next full training batch personally; do not launch a
duplicate batch automatically.
