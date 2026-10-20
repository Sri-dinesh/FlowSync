# Research status — verified 2026-10-21 IST

**The requested superiority/research-readiness goal is not achieved.** The
execution pipeline is substantially more auditable, but the learned controllers
still trail strong classical baselines. Do not describe this as an RL method
that outperforms every controller or as a validated real-world traffic system.

## Latest diagnostic: future-arrival sensitivity implemented and smoke-verified

The [fixed-state future-arrival diagnostic](ARRIVAL_LABEL_RESULTS_20261021.md)
now preserves queues/backlog and pairs all candidate actions within each of
eight new arrival streams. Its one-source smoke exactly reproduces the
original source and original labels. At the three sampled gates, six of seven
alternatives change delay-gain sign across futures; the single originally
qualified choice becomes harmful in seven of eight new futures. This is a
limited clean-sensing, one-parent/source finding, not a general causal
explanation or improved controller. All 37,200 measured signal samples have
zero violations; there is no real-world safety claim.

The full frozen 18-source training-only panel is prepared but not run. Its
command and expected completion checks are in the linked note. No model was
trained/promoted and no calibration/probe/validation/final-test outcomes were
accessed. The first smoke attempt caught a JSON-key representation mismatch
in the new replay checker; that was fixed with a regression test.

## Previous result: richer observed features fail grouped fitting-data screen

The [prespecified compact/full-state comparison](ACTION_FEATURE_RESULTS_20261020.md)
completed all 36 leave-one-traffic-seed-out fits using fitting data only.
Full-state delay-prediction MAE is 35.851 versus compact 33.342 vehicle-seconds
(7.53% worse); throughput and endpoint-wait errors also worsen. Harmful choices
increase from 18/47 to 64/121 changed proposals. The continuation screen fails.
These errors are not full-run traffic delays, and no new control improvement
is established. No calibration/probe, validation or final-test outcomes were
accessed, and original checkpoints remain unchanged. Exact refits, provenance
hashes and independent aggregate-error reproduction were verified.

Do not expand training or promote this candidate. The next bounded diagnostic
is action-label stability across independent future-arrival realizations at
the same observed state, with paired actions inside each realization. That
now has the implemented protocol and limited smoke above; the full panel
remains pending.
The audited methods/results can be written up now, without claiming
superiority or real-world readiness.

## Previous result: broader data complete, calibrated correction abstains

The user completed all 648 source runs in 24.22 minutes. Role-file/input/model
hashes and all branch cells were verified: 216 fitting, 360 calibration and 72
excluded probe sources, 5,707 branches, 3,060,400 sampled signal states and zero
measured violations. See [the verified fitting/calibration results](ACTION_RANK_CALIBRATION_RESULTS_20261020.md).

Three research-only ridge correction models were fitted and frozen using fit
data only, then calibrated by whole-traffic-seed residuals, and frozen again
before the reserved probe. No DQN weights were retrained. The point-only
ablation changes 13 probe actions: seven qualified benefits, five harmful
changes and one neither. The calibrated primary makes zero changes. Its joint
alternative coverage is 99.21%, but whole-seed coverage fails in two parents
on probe seed 95201. The predefined continuation screen fails.

57 targeted tests passed, exact fits/calibration/report reproduction verified,
and original parents remain unchanged. No full-rollout validation, final-test
access or promotion occurred. Do not repeat collection or expand DQN training
yet. Next model-development work can reuse fitting data only for grouped
prediction comparisons, with no selection on the now-observed calibration
or probe outcomes. No improvement in full-run control is established here.

## Latest diagnostic: uncertainty is not a calibrated prediction bound

The [excluded-training-probe audit](ACTION_RANK_UNCERTAINTY_RESULTS_20261020.md)
scored all 226 non-parent alternatives, not just the few selected corrections.
Actual gains meet the bootstrap lower bound in 54.4% of delay, 46.5% of
throughput and 60.6% of endpoint-wait predictions; simultaneous coverage is
24.8%. These are correlated descriptive samples from one excluded traffic
seed, not independent significance tests or a previously guaranteed 90%
interval. Small ensemble spread does not reliably bound prediction error.
No threshold was loosened and no new performance win is claimed.

A broader training-only collector is implemented and smoke-tested, with six
fitting, ten calibration and two excluded probe traffic seeds, outcome-blind
sampling of eligible decision times, and exact source replay checks.
At that point the full 648-source dataset had not been collected; it has now
completed and been fitted/calibrated as recorded above. The command and
completion checks remain in the linked historical results note. 50 targeted
tests passed at that stage; real-checkpoint smoke and provenance were verified.
No validation/final-test access occurred in this diagnostic or smoke.

## Latest implemented candidate: action ranking, primary validation failed

The [action-ranking pilot](ACTION_RANK_PILOT_RESULTS_20261020.md) now implements
and fits a research-only correction with an observed-input ridge model and
bootstrap-based abstention. All 72 training/probe label sources and 168 separate
validation runs completed. Models fit training seed 94001 only and were frozen
before excluded training-probe seed 94002 and validation seeds 25001/25002.

Parents average 12.814 s delay; the point-estimate ablation 12.726 s (0.684%
lower), the prespecified uncertainty-supervised primary 12.815 s, shielded
Max-Pressure 12.979 s, unshielded Max-Pressure 12.493 s and Greedy 12.145 s.
The primary continuation gate fails; the modest ablation gain is not substituted
as primary success. Both variants have real executed corrections, not silent
no-ops. Keep original parents and report all baselines/trade-offs. No promotion
or final-test evaluation. 103 targeted tests passed; source/model/label
provenance, exact training-only refits and report reproduction verified.

## Latest evidence: coverage screen fails; action-outcome labels collected

The [coverage diagnostic](REPLAY_COVERAGE_RESULTS_20261020.md) completed without
requiring a restart. Broader replay reduces reserved-training-probe MAE from
12.648 to 11.759, still worse than unchanged parents (10.745); the continuation
gate fails. All original probes remain excluded, and all 15 narrow-control
measurement points reproduce exactly. These errors are not traffic delays.

The subsequent [all-action feasibility collector](ACTION_RANK_RESULTS_20261020.md)
completed 18 training-only source runs and 135 paired 40-second branches at 45
decision points. Thirteen points have a lower-delay alternative meeting the
stated throughput/endpoint-wait/signal constraints. This is hindsight label
availability, not an achieved learned-policy gain. All source trajectories were
verified against ordinary unbranched engine execution. That collection alone
did not fit a model or change production control. The subsequent ranking
implementation and full-run validation are summarized above; they did not
establish the requested research-performance gain.

## Previous diagnostic: fixed replay fits but transfer worsens

The [fixed-replay diagnostic](FIXED_REPLAY_RESULTS_20261017.md) completed all
three parents and three matched arms in 86 seconds. With stationary labels,
fit MAE decreases from 11.020 to 1.313 while reserved training-episode MAE
increases from 10.745 to 12.648 (worse for all three parents). These are Q-target
prediction errors, not traffic-delay seconds. The network can fit this small
dataset; that is not evidence of improved control or adequate generalization.
Refreshing targets produces much larger target movement, but initial labels
are not ground-truth returns, so movement alone does not establish a bug.
66 targeted tests passed. No fitted diagnostic weights were saved or promoted.
The subsequent coverage and action-label results are summarized above; no new
long training batch or production target-freezing change is justified yet.

## Latest development result: update pressure reduces regression, not parent delay

The [matched update-pressure pilot](UPDATE_PRESSURE_PROTOCOL_20261016.md) tests
4 versus 32 optimizer updates per episode on the same original v7 parents,
with target copies aligned in episode time. Both arms retain the same reward,
shield, demonstrations, exogenous training inputs and validation panel.
The user completed all six runs in `update_pressure_5qyi9cmv`; the saved
comparison was independently reproduced. At episode 90, low updates average
10.852 s delay versus control 11.109 s and original parents 10.841 s. That is
2.31% better than control but 0.10% worse than parents; average within-run p95
also worsens versus parents (38.880 versus 37.035 s). The continuation screen
failed. Keep parents; do not rerun or expand this pilot expecting a demonstrated
gain. See the [verified outcome](UPDATE_PRESSURE_RESULTS_20261017.md).
All 360 validation rows have complete signal coverage (432,000 samples, zero
measured violations); this is not road-safety evidence. No model promotion or
final-test evaluation occurred. The subsequent fixed-training-replay diagnostic
is summarized above; it did not evaluate traffic performance of a new policy.
The [implementation verification](UPDATE_PRESSURE_VERIFICATION_20261016.md)
includes regression tests and a real two-arm, one-episode smoke: both paths
complete, but neither smoke checkpoint improves delay. This is mechanics
verification, not an encouraging performance result or a full pilot outcome.

## Previous development result: temporal pilot and training-drift diagnosis

The [completed temporal pilot and drift audit](TRAINING_DRIFT_RESULTS_20261016.md)
found no supported improvement. All six user-run workers completed 90 episodes
and 2,880 updates; temporal delay was 11.217 s versus control 11.070 s at the
predefined episode-90 comparison. All temporal selections retained their initial
checkpoint. The expanded-validation continuation screen failed.

A subsequent 72-rollout, training-only diagnostic found initial/final delays of
9.838/10.051 s for control and 9.838/10.222 s for temporal on six recorded traffic
cases per seed. The aggregate is influenced strongly by a large low-demand loss;
seed 202 improves, so this is not uniform degradation. The issue is not solely
unseen validation traffic. Weighted loss falls while raw sampled TD error rises
and importance weights shrink. Added unweighted-loss/gradient/weight telemetry
without changing optimizer behavior. No causal optimizer defect or performance
fix is established. The subsequent matched update-pressure result is summarized
above; it does not establish an improvement over the parents. No new model was
promoted.

## Previous development result: expanded validation found no clear improvement

Subsequent implementation: the [temporal-input pilot](TEMPORAL_INPUT_EXPERIMENT_PLAN.md)
now has opt-in v8 history/age and zero-history control encodings, explicit
parent-weight expansion and fixed matched optimizer budgets. **221 tests passed**
and a two-arm one-episode mechanics smoke completed; neither smoke arm improved
validation. The user subsequently ran the full pilot; its negative result is
summarized above. No model was promoted; the performance objective remains
unachieved. Do not rerun the temporal launcher expecting a demonstrated fix.

Paper handoff: [audited manuscript scaffold](PAPER_DRAFT_AUDITED_20261016.md),
[generated frozen-evaluation tables/figures](../results/paper_evidence/audited_v5_20261016/README.md),
and [next temporal-input hypothesis](TEMPORAL_INPUT_EXPERIMENT_PLAN.md). The
historical hard-coded figure generator is disabled; old artifacts are preserved.
The replacement rechecks frozen provenance and recomputes the statistical report
from raw runs before rendering. No new training, simulation, model promotion or
controller behavior change was performed for that paper-output step. The
subsequent temporal-input implementation above is opt-in and remains unvalidated
as a performance improvement.

The [expanded validation](EXPANDED_VALIDATION_RESULTS_20261016.md) completed all
330 planned simulations across three training seeds, five additional traffic
seeds, three existing validation templates and two sensing conditions. Candidate
D3QN + shield averaged **11.497 s**, its parents **11.497 s**, Max-Pressure with
the same shield **11.436 s**, and unshielded Max-Pressure **11.245 s**. The primary
saved-delay intervals against parents and matched-shield Max-Pressure both cross
zero. Neither superiority nor equivalence is established. This is development
validation, not a new independent final test, and fallback was disabled.

All exact cells, checkpoint/scenario/source provenance and paired arrivals
verified. All 396,000 signal-audit samples were covered with zero measured
conflict/clearance violations; this is not real-world safety evidence. The
expanded targeted regression suite passed **185 tests**. No candidate was
promoted, no default was changed and historical results remain intact.

Do not run another identical training batch or claim the project now beats all
baselines. Use the verified evidence and limitations for drafting; a stronger
algorithmic claim needs a new, training/validation-only hypothesis and a fresh
frozen test after a reproducible validation gain. Publication readiness and
real-world readiness remain unestablished.

## Previous development step: policy-decision audit and paired learning pilot

The [36-run training-only policy audit](POLICY_DECISION_RESULTS_20261016.md)
found 39 RL/teacher proposal disagreements over 518 decision gates. In 34
eligible paired 20-second branches, the teacher helped delay in 19 and hurt
in 15; it is not always the better action. This motivates testing an optional
release of the fixed imitation margin, not asserting a discovered optimizer bug.

The trainer now supports an online-only margin-weight decay while preserving TD
replay, warmup, the shield and old defaults. A real two-episode smoke run verified
finite updates and zero final weighted imitation loss with demonstrations still
sampled. It is not comparative performance evidence. The user completed the
[short paired pilot](MARGIN_RELEASE_PROTOCOL_20261016.md) in
`results/research_training/margin_release_6usc2j0j`. Its comparator uses common
completed validation candidates and all three parent seeds. Releasing the margin
improved the mean of selected delays by only 0.028 s, entirely from seed 101;
at the common episode-90 checkpoint it worsened mean delay by 5.33%. Seeds 202
and 303 retained their parents. Full margin release is not supported or adopted.
The subsequent frozen constant-arm selections were checked above, including
both unchanged seeds. No model has been promoted.

## Previous development experiment: benefit gate (not promoted)

The [training-only benefit-gate experiment](BENEFIT_GATE_RESULTS_20261016.md)
completed 216 source rollouts and 270 matched validation simulations. Forty of
186 eligible training comparisons met its delay-plus-wait-protection target.
The fixed gate vetoed all 106 validation entry evaluations and exactly matched
shield-only D3QN's recorded traffic metrics in all 90 paired cases.

Mean validation delay was 10.864 s for both gated and shield-only D3QN, versus
11.205 s for original full UQ. This is **not a new gain over shield-only** and
does not demonstrate a useful selective fallback mechanism. The gate remains
opt-in, no default or checkpoint was replaced, and no new final-test evaluation
was launched. All 270 planned cells, provenance and paired arrivals verified;
324,000 signal-audit samples had zero measured conflict/clearance violations.
157 targeted regression tests passed. The next investigation is training-only
action-level learning regret under the same shield, not more identical training.

## Previous development diagnostic: intervention audit

The [36-run validation intervention audit](INTERVENTION_AUDIT_20261016.md)
completed with 65 paired, 20-second counterfactual comparisons. Keeping sampled
shield overrides usually worsened total short-horizon delay but reduced the
endpoint largest upstream wait in 22 of 38 comparisons. This is a genuine
fairness/efficiency trade-off, not grounds to remove the shield unconditionally.
Keeping fallback helped delay in seven of 27 sampled comparisons, hurt in 14,
and tied in six. These are correlated development diagnostics, not independent
final-test trials or a threshold-search result.

The phase-service timer is confirmed not to be an individual vehicle-wait
measurement. Its semantics are now explicit in research telemetry and tests.
A clearance-override accounting defect was corrected without changing executed
actions. No additional training, controller-threshold tuning or final-test
reuse occurred. See the audit for the training-only benefit-gate next step.

## Latest completed evaluation: v5 pilot with matched shield controls

The user completed the [v5 pilot](LEARNING_PILOT_PROTOCOL_20261015.md), and the
separately frozen [matched-shield evaluation](MATCHED_SHIELD_PROTOCOL_20261015.md)
completed all 2,800 planned simulations. It includes all three selected models,
20 fresh traffic seeds (81001–81020), seven clean test templates and three
additional fault conditions. No additional training or selection occurred.

| Controller | All-ten-condition mean delay (s) | Average within-run p95 (s) |
| --- | ---: | ---: |
| Max-Pressure | 11.514 | 39.418 |
| Bare D3QN | 11.528 | 40.285 |
| Greedy | 11.725 | 41.891 |
| Max-Pressure + shield | 11.953 | 40.029 |
| D3QN + shield | 12.004 | 40.241 |
| Full FlowSync-UQ | 12.019 | 40.112 |
| Fixed | 15.496 | 40.539 |
| Actuated | 16.463 | 63.448 |

The preregistered primary contrast, shielded D3QN against shielded Max-Pressure,
has saved delay -0.050 s, descriptive crossed-bootstrap 95% interval
[-0.219, 0.125]. Its p95 saved-delay interval is [-0.920, 0.445], mean -0.212 s.
Neither establishes superiority. Bare D3QN against Max-Pressure saves -0.014 s,
interval [-0.180, 0.151]; this does not establish equivalence either.

Adding the shield increases D3QN mean delay by 0.476 s (saved-delay interval
[-0.661, -0.291]) and Max-Pressure mean delay by 0.439 s ([-0.572, -0.302]).
The validation tail-delay advantage **did not generalize** to this fixed test
set. Of D3QN's 896 shield interventions, 892 are anti-starvation and four are
max-green. All 300 shielded Max-Pressure interventions are anti-starvation.
This identifies the anti-starvation mechanism as the dominant intervention,
not proof that any particular threshold is optimal or should be relaxed.
Mandatory physical minimum-green/clearance protections remain on for all arms.

Full UQ adds 0.015 s mean delay over the same shielded D3QN, with saved-delay
interval [-0.104, 0.071]. It actually activated fallback 306 times, covering
260,298 simulated ticks across 600 runs, so lack of measured improvement is
not simply a disabled fallback. Neither fallback mean nor tail benefit is
established. The old calibration remains a count-error model, not a predictor
of the backup controller's advantage.

Bare D3QN's saved-delay intervals favor it over Fixed (mean 3.969 s), Actuated
(4.935 s) and Greedy (0.197 s); these are descriptive, unadjusted comparisons,
not a claim of beating every mode. The shield-selected checkpoints were reused
unchanged for removal ablations; bare D3QN was not selected using this test.

All 2,800 exact planned cells, checkpoint/calibration/scenario hashes, paired
arrival traces and frozen source archive were verified. There are 4,340,000
signal-audit samples, covering every simulated step, and zero observed conflict
or clearance violations. This does not establish collision or real-world safety.
All numeric traffic metrics checked are finite. The only source change after
the simulation freeze was the separately invoked exporter: it now groups by
intervention label instead of merging shield-only D3QN with full UQ by class
name. Its actual source and input hashes are preserved in separate postprocessing
artifacts; the original simulation archive is unchanged. 126 targeted tests
passed across the core suite and exporter tests.

- [Completed evidence summary](../results/replicate_evaluation/matched_shield_v5_20261015/EVIDENCE_SUMMARY.md)
- [Full statistical report](../results/replicate_evaluation/matched_shield_v5_20261015/report.json)
- [All-condition controller table](../results/replicate_evaluation/matched_shield_v5_20261015/all_condition_controller_summary.csv)
- [Clean-only controller table](../results/replicate_evaluation/matched_shield_v5_20261015/clean_controller_summary.csv)

Next development should investigate actual vehicle waiting versus the shield's
phase-level starvation proxy, and whether uncertainty predicts beneficial
fallback decisions. Use training/validation data only; do not tune against
81001–81020. More episodes alone are not supported by these findings. Independent
simulator validation, contribution evidence and deployment evidence remain open.

## Previous fresh-seed evaluation: domain-randomized batch

All 2,000 planned simulations completed with the three frozen selected models,
20 fresh traffic seeds (61001–61020), seven clean scenarios and three additional
fault conditions. Every planned cell is unique, selected checkpoint/calibration
hashes match, safety audit samples cover every simulated step, and archived
source hashes were independently verified. No retraining or threshold selection
occurred during this evaluation.

| Controller | Seven-clean-scenario mean delay (seconds) |
| --- | ---: |
| Max-Pressure | 11.781 |
| D3QN | 11.918 |
| Greedy | 12.123 |
| FlowSync-UQ | 12.560 |
| Fixed | 15.212 |
| Actuated | 18.165 |

D3QN's mean saved delay against Max-Pressure is -0.137 seconds, with descriptive
crossed-bootstrap 95% interval [-0.325, 0.043]. This does not establish superiority
or statistical equivalence. Against Greedy the saved delay is 0.205 seconds,
interval [-0.042, 0.490], also inconclusive. Against Fixed it is 3.293 seconds,
interval [2.844, 3.709]. The earlier validation advantage did not establish a
consistent held-out advantage against the strongest baseline.

Across all ten condition cells, FlowSync-UQ increases delay relative to its own
D3QN by 0.559 seconds (saved-delay interval [-0.726, -0.401]). Do not promote UQ
as an efficiency improvement. In clean balanced, incident and burst scenarios,
fallback steps are zero but shield interventions occur and UQ has higher delay;
this points to the shield/control interaction as a diagnostic target, not proof
that fallback calibration is the sole cause or that safeguards should be removed.
Under severe faults, fallback uses the same corrupted sensor stream, not an
independent reliable sensor. The measured signal violation total is zero; this
does not validate real traffic safety.

The subsequent [matched validation ablation](SUPERVISOR_ABLATION_20261015.md)
completed 540 runs. The disabled wrapper matches D3QN exactly. Shield-only
raises mean delay from 10.578 to 10.799 s while lowering within-run p95 from
39.279 to 37.675 s; all recorded interventions are anti-starvation overrides.
Fallback-only raises mixed-fault mean delay from 10.558 to 11.040 s and also
worsens aggregate p95. This distinguishes a fairness/efficiency trade-off from
an uncertainty target that does not establish backup-controller benefit.
No controller defaults or thresholds were changed. Preserve the final test;
do not retune against it. A subsequent development experiment should investigate
shield-aware training and decision-risk supervision. Independent simulator
validation and training-recipe contribution ablations remain missing.

- [Latest evidence summary](../results/replicate_evaluation/domain_frozen_20261015/EVIDENCE_SUMMARY.md)
- [Raw runs](../results/replicate_evaluation/domain_frozen_20261015/runs.jsonl)
- [Frozen protocol](DOMAIN_EVALUATION_PROTOCOL_20261015.md)

## Earlier completed evidence (before domain-randomized training)

The frozen evaluation contains 2,000 runs, three independent policy-training
seeds and 20 paired traffic seeds. The seven clean-scenario means are:

| Controller | Mean delay (seconds) |
| --- | ---: |
| Max-Pressure | 11.944 |
| Greedy | 12.199 |
| D3QN | 13.123 |
| FlowSync-UQ | 13.262 |
| Fixed | 15.786 |
| Actuated | 17.709 |

D3QN saves 2.663 seconds against Fixed (crossed-bootstrap descriptive 95%
interval: 1.972–3.289), but loses 1.179 seconds against Max-Pressure (saved-delay
interval: -1.701 to -0.735). The intervals resample training runs and paired
traffic seeds; they are not multiplicity-adjusted hypothesis tests.

Across all ten scenario/condition cells, UQ saves only 0.096 seconds relative to
its underlying D3QN; the interval [-0.225, 0.465] includes no improvement.

A separate 210-run sensitivity check at 600 simulated seconds retains the same
ordering of the strongest methods: Max-Pressure 14.119 seconds, Greedy 14.321,
UQ 15.070, D3QN 15.707. This check uses only three traffic seeds and is diagnostic.

Artifacts, preserved without overwriting earlier results:

- [Frozen evaluation summary](../results/replicate_evaluation/frozen_v7_20261014_run2/EVIDENCE_SUMMARY.md)
- [Raw frozen runs](../results/replicate_evaluation/frozen_v7_20261014_run2/runs.jsonl)
- [Long-horizon summary](../results/replicate_evaluation/frozen_v7_600s_20261014/EVIDENCE_SUMMARY.md)
- [Uncertainty calibration report](../results/uncertainty_calibration/pilot_20261014/report.json)
- [Protocol and limitations](RESEARCH_PROTOCOL_20261014.md)

## Integrity checks repeated at handoff

- All 2,000 planned cells are present.
- Every learned run's checkpoint hash matches its frozen training-seed selection;
  the checkpoint files still match those hashes.
- Every UQ run's calibration hash matches the frozen calibration artifact.
- All Python files in the frozen source archive match the recorded source hashes.
- Signal-audit coverage is 1,500 or 2,000 samples per run, according to scenario
  duration; no measured simulated conflict/clearance violations occurred.
- **103 targeted regression tests passed** on the current worktree. Tests cover
  observed-input training/evaluation parity, checkpoints, faults, scenarios,
  controllers, calibration, bootstrap calculations, RL/simulation regression and
  cooperative runtime limits/selection integrity across interrupted stages,
  rejection of reused final-evaluation traffic seeds, explicit factorial
  ablation switches, and disabled-wrapper traffic-metric identity under both
  clean and corrupted observations, and shield-aware collection/inference
  parity with real interventions plus correctly matched validation selection.
- `git diff --check` passed. No commit/push or automatic model promotion occurred.

These checks do not establish collision safety, simulator validity, website
parity, or hardware/deployment readiness. The user has scoped this work to
simulation only. Existing test scenario families have already been inspected;
fresh traffic seeds do not make those families unseen.

## What improved, and what did not

The fitted uncertainty model recognizes a defined synthetic count-error event
on an audit seed: 68.4% recall at 6.1% false positives, versus zero recall at the
old heuristic threshold. That is error detection, not proof that fallback
improves traffic delay. Frame samples are temporally correlated.

The v7 policy adds observed downstream counts and phase-wait timers. Training
selection retains all three initializations, rather than reporting the winning
seed alone. Two of the three selected v7 models are demonstration warm-start
checkpoints: subsequent online RL did not improve their validation score.
This is a learning-stability/generalization problem still requiring work.

## Extended batch — subsequently completed by the user

The user launched `results/research_training/domain_rCXu3gDe`. All three runs
completed 900 online episodes, 200 demonstration episodes, 2,000 imitation
updates and 500 TD warmup updates in about 28–29 minutes each. All selected
checkpoint hashes, validation-selection minima and paired arrival traces were
verified. There was no pretrained parent checkpoint.

Selected mean validation delays over 30 cells (three templates, five traffic
seeds, clean and mixed faults): seed 101 warmup 10.5599 s; seed 202 episode 700
10.5166 s; seed 303 warmup 10.6589 s. Max-Pressure scored 10.8450 s on the same
cells. The three-run mean is about 2.5% lower, but these data selected the models:
they do not prove independent superiority. Warmup still wins in two runs.

The fresh-seed evaluation is specified in
[its frozen protocol](DOMAIN_EVALUATION_PROTOCOL_20261015.md), retaining all
training seeds and using traffic seeds 61001–61020, with overlap checks against
both earlier evaluations. Known scenario families and unchanged transferred
UQ calibration are explicit limitations.

### Historical budget/launch issue (resolved by the user's later run)

The user authorized up to four additional hours. The recorded plan set a window
from **2026-10-14 15:17:12 UTC to 19:17:12 UTC**. At revalidation on
2026-10-14 20:33:43 UTC that window had passed.

At that earlier handoff, **the batch was prepared but not started**. There were
no extended-batch model artifacts then. The six earlier training output
directories are the fine-tuning pilot, two fresh v6 runs and three fresh v7 runs.
Do not infer execution from [the extended plan](EXTENDED_TRAINING_PLAN_20261014.md)
or the existence of new training flags. No new long training run is authorized
by that status document. The user subsequently ran it, as recorded above.

During the follow-up, a runtime-limit gap was fixed without launching new
training: the old limit checked only online episode boundaries, leaving
demonstration collection, pretraining and validation unbounded. All stages now
check the same elapsed-time budget. Interrupted validation cannot replace a
fully evaluated selection; incomplete rows have a null score. The summary
records the stop stage, completed counters and an unselected interrupted
checkpoint. The limit is cooperative, not a hard process kill: one in-flight
validation simulation/optimizer step and checkpoint saving may overrun it.
These changes do not alter the previously recorded comparative results.

## Completion requirements still open

The opt-in [shield-aware training path](SHIELD_AWARE_TRAINING.md) is now
implemented. A 44-second integration smoke test at
`results/research_training/shield_smoke_updates_20261015` completed 16 demo
episodes, two imitation updates, two TD warmup updates and 45 online TD updates
across two training episodes. Saved weights changed, checkpoint selection used
the shield-only controller, and hashes matched. An earlier smaller smoke test
did not fill the batch buffer and performed no optimizer updates; it is retained
at `results/research_training/shield_smoke_20261015` and is not learning evidence.
Six saved clean/noisy UQ validation cells were reproduced exactly after the
shared-adapter refactor. The subsequently completed full batch is recorded below.
The fallback
supervisor is unchanged and its measured deficit remains unresolved.

The matched bare-training control selection subsequently completed 990
validation cells over all retained candidates. Shield-only selection chooses
warmup/episode 400/episode 500 for seeds 101/202/303, respectively (mean delays
10.7702/10.7728/10.8106 s). All candidate/source hashes and complete selection
sets were verified; original bare selections are untouched. The user then ran
the full batch at `results/research_training/shield_mW0ZwjUP`: all three completed
900 episodes, but matched validation mean delay worsened about 0.87% (10.7845 to
10.8781 s). Selected checkpoints were episode 100/warmup/episode 100. The recipe
did not establish improvement. No duplicate batch should be launched.

The subsequent [learning-update audit](LEARNING_UPDATE_AUDIT_20261015.md)
reproduced a triple-counted switch penalty and incomplete macro-action targets.
The research path now explicitly uses v5 single-switch reward and drops partial
end-of-horizon replay transitions. Added diagnostics measure sampled demos and
reward components. Regression and short integration tests pass; no new full
training batch or performance claim follows. Legacy website v4 reward/collector
paths remain unmigrated and must not be presented as corrected by this change.

| Requirement | Current evidence |
| --- | --- |
| Learned controller beats strong baselines | Not established on latest fresh seeds; Max-Pressure has lower mean delay |
| Reliable UQ control benefit | Latest batch's UQ increases mean delay relative to its own D3QN |
| Stable benefit from additional RL training | Not established; warm starts win selection in two seeds |
| Attribute improvement to a specific contribution | Matched-recipe ablations remain incomplete |
| Research-grade simulation validity | Independent simulator/calibration evidence remains missing |
| Reproducible local execution and provenance | Verified for the recorded experiments |
| Newly randomized training batch | All three runs and the 2,000-run fresh-seed evaluation completed |

Do not add training merely because a test result is unfavorable. Retain all
outcomes and select only on validation data. Every new confirmatory test must
use a separately declared fresh seed set, disclose inspected scenario families,
and include losses.
