# Auditing Learned Traffic Signal Control Under Synthetic Sensing Faults

Working manuscript scaffold, not submission-ready text. Simulation-only scope.
Author names, target venue, novelty assessment and independent simulator validation
remain open. Do not copy the historical performance tables in README/CONTENT or
the pre-audit IEEE figures into this draft.

## Abstract — evidence-backed draft

We study the empirical effects of rule-based shielding and uncertainty-triggered
fallback in a learned traffic signal controller under synthetic sensing faults.
An audited headless workflow records checkpoint and scenario provenance, paired
traffic arrivals, and executed signal states. A frozen evaluation comprises
2,800 simulations with three trained policy replicates, 20 traffic seeds, and
ten fixed scenario-condition combinations. Across these conditions, D3QN with
shielding achieves 12.004 seconds mean accumulated waiting per arrived vehicle,
compared with 11.953 seconds for Max-Pressure with the same shield. The paired
saved-delay estimate is -0.050 seconds, with a descriptive crossed-bootstrap
95% interval of [-0.219, 0.125] seconds; superiority is not established.
Adding uncertainty-triggered fallback also yields no established mean-delay
benefit over shielded D3QN. All 4,340,000 audited simulated signal samples show
zero measured conflict or clearance violations, which does not establish
collision safety or deployment readiness. Subsequent development diagnostics
identify efficiency/fairness trade-offs and a mismatch between predicting
perception error and predicting fallback benefit. The findings support careful
component attribution and matched-baseline evaluation rather than a universal
claim that learned or hybrid control outperforms classical control.

## I. Introduction and research questions

Position this as an empirical component/evaluation study unless a new method
later demonstrates an independently validated contribution. The current code
combines existing approaches; combination alone does not establish novelty.

- RQ1: Does the learned policy improve delay over strong classical baselines
  under matched sensing and matched shield settings?
- RQ2: What changes when the same checkpoint is evaluated with or without the
  additional shield, and with or without uncertainty-triggered fallback?
- RQ3: Do validation improvements persist on additional traffic seeds, and do
  intervention diagnostics explain why aggregate improvements disappear?

Do not claim that all prior traffic RL assumes oracle observations: earlier
work already studied sensing failures and uncertainty. Rodrigues and Azevedo
explicitly investigate demand surges, capacity reductions and sensor failures.
[Primary source](https://arxiv.org/abs/1904.08353)

## II. Related work — initial source-checked positioning

- Pressure-based learning is not new: PressLight combines RL with a pressure
  formulation for traffic signals. Compare the specific observable state,
  control constraints and evaluation design, not just the use of DQN plus
  Max-Pressure. [Author-hosted paper](https://faculty.ist.psu.edu/jessieli/Publications/2019-KDD-presslight.pdf)
- Advanced-MP/Advanced-XLight incorporate queuing and running-vehicle information.
  They motivate checking state representation rather than assuming additional
  network complexity is the answer. They have not been implemented or evaluated
  as baselines in FlowSync; do not label the current Max-Pressure implementation
  as Advanced-MP. [ICML 2022 paper](https://proceedings.mlr.press/v162/zhang22ah.html)
- RESCO supplies traffic-signal RL benchmarks with realistic scenario designs;
  it is a candidate independent environment, not evidence that FlowSync has
  already replicated those benchmarks. [NeurIPS 2021 paper](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/f0935e4cd5920aa6c7c996a5ee53a70f-Abstract-round1.html)
- RL reproducibility work motivates retaining training replicates and accounting
  for variability rather than reporting only a winning seed.
  [Henderson et al.](https://arxiv.org/abs/1709.06560)

This is a starting bibliography, not an exhaustive novelty search or a claim
that the proposed empirical findings are the first of their kind.

## III. System and experimental method

Use the frozen protocol and archived source as the methods authority:
[matched-shield protocol](MATCHED_SHIELD_PROTOCOL_20261015.md).

The executed experiment is a single-intersection custom simulator, not the
website's advertised multi-intersection/camera deployment. Policies observe a
synthetic count-sensor stream with causal fault injection; metrics may access
simulator truth, but control inputs must not. The v7 policy has 36 features:
the shared 28-dimensional observation, four observed outgoing counts and four
phase-service timer features. Those timers do not measure individual waits.

D3QN uses a dueling network, double-Q learning and demonstration-assisted
training. All three selected checkpoints are included; seed 101 selected its
warmup checkpoint, so online RL benefit cannot be assumed for every replicate.
The physical signal FSM remains active for every method, including "bare"
D3QN. The additional shield applies rules such as anti-starvation/max-green.
Full FlowSync-UQ adds the calibrated uncertainty supervisor and fallback.
The calibration was fitted with a different policy and predicts count error,
not the relative control benefit of fallback.

Experimental design: seven existing clean test templates and three fault
conditions on balanced traffic, 20 paired traffic seeds (81001–81020), three
training seeds (101/202/303), five classical variants and three learned variants
per checkpoint. Classical baselines run once per cell; they are not three
independently trained models. The scenario families had already been inspected;
only traffic seeds were fresh. The subsequent 330-run development screen is
reported separately and is not added to this final-evaluation sample size.

Primary endpoint: finite-horizon accumulated stopped waiting per arrived
vehicle, including present/backlogged vehicles, averaged equally across the
ten condition cells and all training replicates. This is not completed-trip
travel time. Secondary tail endpoint: average within-run p95, not a pooled
vehicle-level percentile. Intervals use 5,000 crossed-bootstrap draws over
training replicates and paired traffic seeds with conditions fixed; they are
descriptive, unadjusted intervals with only three training replicates.

## IV. Results — frozen evaluation, not the later validation set

| Controller | Mean delay (s) | Mean within-run p95 (s) |
| --- | ---: | ---: |
| Fixed | 15.496 | 40.539 |
| Actuated | 16.463 | 63.448 |
| Greedy | 11.725 | 41.891 |
| Max-Pressure | 11.514 | 39.418 |
| Max-Pressure + shield | 11.953 | 40.029 |
| D3QN | 11.528 | 40.285 |
| D3QN + shield | 12.004 | 40.241 |
| Full FlowSync-UQ | 12.019 | 40.112 |

The primary matched-shield comparison does not establish a D3QN advantage.
Adding the shield increases mean delay by 0.476 seconds for D3QN and 0.439
seconds for Max-Pressure. These are component effects with fixed checkpoints,
not separately optimized training-recipe comparisons or proof that removing
fairness protections is preferable. Adding UQ fallback to shielded D3QN saves
-0.015 seconds, interval [-0.104, 0.071]; fallback actually activates, but its
efficiency benefit is not established.

Use the generated [tables and figures](../results/paper_evidence/audited_v5_20261016/README.md)
for the manuscript. `contrasts.csv` contains all saved mean/tail contrasts and
their scope, including negative results. Do not mix clean-only and all-condition
statistics or attach aggregate bootstrap intervals to individual traffic runs.

## V. Development diagnostics — explicitly exploratory

The [intervention audit](INTERVENTION_AUDIT_20261016.md) compares short paired
branches, not complete counterfactual controller rollouts. Shield overrides
usually increase short-horizon total delay but sometimes reduce the largest
remaining upstream wait. Fallback is sometimes helpful and sometimes harmful.
These selected, correlated events do not support independent-event p-values.

The [benefit gate](BENEFIT_GATE_RESULTS_20261016.md) vetoes every validation
entry and matches shield-only control; it is not a demonstrated selective
fallback improvement. The [margin-release pilot and expanded validation](EXPANDED_VALIDATION_RESULTS_20261016.md)
also fail to establish a reproducible mean-delay improvement. Report these as
negative development findings, not additional independent final-test evidence.

A subsequent [action-ranking correction pilot](ACTION_RANK_PILOT_RESULTS_20261020.md)
trained small observed-input models on paired simulator outcome differences.
On a separate 168-run development panel, the point-estimate ablation reduced
mean delay by 0.684% relative to its parents, but the prespecified
bootstrap-supervised primary did not improve aggregate delay. Both remained
behind Greedy and unshielded Max-Pressure on mean delay. This failed continuation
screen is not an independent final-test win, a calibrated safety claim, or a
reason to replace the manuscript's frozen main results.

## VI. Threats to validity and deployment boundaries

Single custom simulator; synthetic rather than measured camera faults; few
training replicates; short finite horizons; previously inspected scenario
templates; several exploratory comparisons; checkpoint selection under a shield;
calibration transfer across policies; no pedestrian/collision audit; no cabinet
hardware, network-failure, emergency-service or field validation. Zero measured
signal violations is not a formal guarantee of physical safety. Do not claim
Jetson FPS, real CCTV accuracy, road deployment or universal generalization.

## VII. Conclusion and remaining work

The audited pipeline supports reproducible comparisons and exposes component
trade-offs. Strong classical control remains competitive, and neither shielding
nor uncertainty fallback guarantees lower aggregate waiting. Independent
simulator replication and an explicitly tested contribution remain necessary
before making a strong research claim. A candidate next hypothesis is recorded
in [the temporal-input experiment plan](TEMPORAL_INPUT_EXPERIMENT_PLAN.md);
its full comparative pilot failed the predefined continuation screen. A subsequent
[training-only diagnostic](TRAINING_DRIFT_RESULTS_20261016.md) found regressions
on sampled training cases too, with important variation across seeds and cases.
No performance benefit or sole causal explanation is established.

## Submission checklist

- Choose an appropriate venue/article type with the supervisor; verify its
  current submission rules separately. No acceptance/readiness promise.
- Complete a focused novelty review, including newer robustness and hybrid
  traffic-control work; distinguish new findings from existing techniques.
- Replicate key comparisons in an independent simulator or clearly justify
  simulator validation. Do not present unrun SUMO/RESCO results.
- Verify every manuscript value against generated artifacts and their hashes.
- Report all model seeds, exact timings, reward/observation versions, evaluation
  durations and statistical limitations; archive the frozen reproduction bundle.
- Replace or explicitly exclude historical unaudited figures. The existing
  manuscript/template files were preserved, not silently rewritten.
