# Observed-input averaged-label model pilot

[Protocol](AVERAGED_LABEL_MODEL_PROTOCOL_20261021.md).
Runner: `research/run_averaged_label_model_pilot.py`.
Model/scoring helpers: `research/averaged_label_model.py`.

## Full pilot completed: continuation fails

Output: `results/averaged_label_model/pilot_20261021T095353Z`.
All 72 fitting sources, 36 excluded probe sources and six models completed
in 45.46 minutes. All 2,448,000 recorded source/branch signal samples have zero
violations; this is simulation evidence, not a real-world safety guarantee.

Mean-eight makes zero changes across 72 probe gates (576 future cases),
so delay/throughput/endpoint-wait gains are all zero. Single-future changes
one gate: five of eight future cases qualify, three are harmful. Across all
576 cases its gains are [0.2500, -0.00521, 0.01823] in the protocol's units.
Mean-eight delay prediction MAE falls from 24.561 to 22.603 vehicle-seconds,
but the activity and improvement checks fail. **Do not promote the model or
advance it to a full rollout.**

The descriptive audit is saved at
`results/averaged_label_model_audit/pilot_20261021`. Input/output/source hashes,
all six exact refits, all persisted pre-outcome predictions and scores match.
Six independent source/original-branch replays (one per parent and role)
also match; not all 108 sources or all resampled futures were replayed.

On fitting data the mean-eight predictor identifies only 5/36 alternatives
with qualified mean outcomes; on the excluded probe it identifies 0/23.
Six probe alternatives are predicted to save delay, but all are predicted
to lose throughput, so none qualifies. Five of those six actually increase
mean delay: dropping the throughput requirement is not supported. Thresholds
were left unchanged. This audit describes already observed fit/probe data;
it is not a new independent evaluation or proof of a single causal defect.

The subsequent [joint-benefit screen](JOINT_BENEFIT_RESULTS_20261021.md) uses
only fitting data and also fails. Its result must not replace this negative
excluded-probe result. No DQN checkpoint, production default or safety shield
was changed.

### User rerun: exact output reproduction

`results/averaged_label_model/pilot_20261021T114544Z` completed the same panel
in 1,041.49 seconds (17.36 minutes). All thirteen reported output hashes,
including data, all six models and pre-outcome predictions, exactly match the
earlier run and were checked against files. The mean-eight model again makes
zero corrections and the continuation screen fails. This is reproducibility
evidence for the same experiment, not additional independent traffic seeds or
a new model improvement. Preserve both runs; do not launch another repetition.

## Original design and execution instructions (historical)

The preceding frozen-choice experiment passed, but used simulator outcomes to
choose actions. This next pilot trains predictors whose inputs are only
delivered traffic observations, known signal context and parent Q values.
It compares single-future training labels with eight-future averages using
the same compact features, fitting states, normalization and ridge penalty.

The full run collects 72 fitting sources on four new traffic seeds, fits and
freezes six small JSON models (two per parent), then evaluates 36 sources on
two excluded traffic seeds. All sources use the six training templates and
clean sensing. Probe choices/predictions are flushed before action outcomes
are simulated. No probe data may alter weights or thresholds. All parent DQN
checkpoints remain unchanged; these are not new production checkpoints.

Raw fitting/probe branches, model coefficients and hashes, pre-outcome probe
predictions, per-source scores, decisions and source provenance are retained.
Budget stops preserve completed sources, explicitly mark incomplete, and
cannot fit a truncated fitting panel or pass the full continuation screen.

## Completed mechanics smoke

Output: `results/averaged_label_model/smoke_20261021`.
Two fitting sources (96901/96902) and one excluded probe (96903), parent 101,
train_ew_asymmetric_01, completed in 66.69 seconds. Both models fit six
non-parent examples from the same four fitting gates; their coefficients
were saved and frozen before the probe. This intentionally tiny fit tests
mechanics, not adequacy of training data.

Both models retain the parent at both probe gates: 16 future cases each,
zero executed corrections and zero delay gain. The continuation screen is
false, as required for a smoke; there is no demonstrated control improvement.
Prediction MAEs in target order are single [19.532, 1.285, 15.038] and mean8
[19.432, 0.322, 3.188]. These one-source errors are not a performance claim.
All 54,000 recorded source/branch signal samples have zero violations; this
does not establish real-world safety.

78 targeted tests passed. All input/source/output/model hashes verified;
both models refit exactly from fitting data only; saved pre-outcome choices,
prediction errors, score rows and report reproduce. Independently replaying
all three smoke sources without future resampling reproduced both the full
source trajectories and original single-future branch outcomes exactly.
At smoke completion, full-pilot source seeds and future streams were untouched. The new collector
explicitly includes the actual source seed in future-stream derivation, rather
than the original diagnostic's fixed seed 95001.

## Original full command — already completed; do not repeat for this candidate

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u \
  research/run_averaged_label_model_pilot.py \
  results/averaged_action_labels/panel_20261021T091742Z \
  --output "results/averaged_label_model/pilot_$(date -u +%Y%m%dT%H%M%SZ)" \
  --max-wall-seconds 5400
```

Estimated 45–65 minutes, with a 90-minute cooperative simulation budget.
Expect 72 fit sources, 36 probe sources, six fitted models and
`full_pilot_complete: true`. That confirms execution, not model superiority.
`continue_to_full_rollout_pilot` reports the separate development screen.
The user's full run is now verified above; the command is retained for provenance.

Even a pass needs separate full-episode validation of the learned corrections
against unchanged strong baselines. This pilot only changes one macro-action
then returns to the parent policy. It does not prove that repeated corrections
will improve whole-simulation traffic, and it does not establish sensing-fault
robustness or real-world readiness. No automatic upload/promotion occurs.
