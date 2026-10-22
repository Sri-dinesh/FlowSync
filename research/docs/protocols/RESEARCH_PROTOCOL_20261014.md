# Simulation-only research protocol — 2026-10-14

Scope confirmed by the user: simulation only. No claim of camera/hardware or live
road deployment readiness. No promise of superiority over every controller.

## Development and selection (before fresh test evaluation)

- Repair shared execution, observation corruption, checkpoint loading and safety
  measurement first; preserve the original evaluation archive.
- Use six `research/scenarios/train/` templates for demonstration collection and
  learning. Use three `validation/` templates and seeds 21001/21002 for candidate
  selection. Never collect replay from validation/test scenarios.
- Select minimum mean validation delay over clean and mixed sensor conditions;
  retain the incumbent on a tie. Save all candidates, including the initial
  network and demonstration warm start. A selected episode-zero/warmup checkpoint
  is not evidence that subsequent online RL improved it.
- Development runs: one 60-episode fine-tuning pilot; two fresh 240-episode v6
  runs (101/202); three fresh 240-episode v7 runs (101/202/303). All runs and weak
  outcomes are retained under `results/research_training/`.
- v7 adds four observed downstream counts and four observed phase-wait timers to
  the v6 sensor vector. It does not access additional simulator truth. Its recipe
  also uses masked imitation warm start and a 200-update target refresh. Therefore
  differences from earlier v6 runs cannot isolate the representation contribution;
  matched-budget ablations remain necessary for such a claim.
- Three v7 runs, not the best training seed, form the frozen candidate family for
  fresh traffic-seed evaluation. They use no shared pretrained parent.

## Uncertainty model

`research/calibration/calibrate_uncertainty.py` fits nonnegative logistic coefficients on
observable uncertainty features. Ground-truth synthetic count error supplies
labels only. The event is total absolute count error >= 3 vehicles over the 12
movements, **not** crash risk, model epistemic uncertainty, or fallback utility.

Validation-only rollout seeds: 31001 for fitting, 31002 for choosing a threshold
with <=10% false positives on its sampled frames, 31003 for audit. The recovery
threshold is 0.6 times the entry threshold. No final test data sets coefficients
or thresholds. Frame-level samples are temporally correlated; thousands of
frames are not thousands of independent experiments.

The calibration dataset was collected using the fine-tuned v6 pilot without
fallback/shield. Transferring it to the independently trained v7 policies is an
additional distribution shift; final control tests must establish its utility.
The separate hard failover on >=1,000 ms observation age remains disclosed.

## Frozen test evaluation

Use `research/evaluation/evaluate_replicates.py` with all three selected v7 checkpoints and
the fixed calibration artifact. No checkpoint/threshold selection inside it.

- Traffic seeds: 51001–51020, unused in the above development runs.
- Seven existing test scenario templates under clean sensing.
- Additional miss_30, latency_1000ms and combined_severe conditions on balanced
  demand. These fault names refer to the exact profiles saved in source; they
  are synthetic stress conditions, not measured camera-error distributions.
- Four classical baselines: Fixed, Actuated, Greedy, Max-Pressure.
- Both D3QN and calibrated FlowSync-UQ for each of three training seeds.
- 2,000 planned cells; identical arrival traces checked for paired cases.
- Primary performance comparison: mean delay across the seven clean scenarios.
  Report all per-scenario outcomes. Faulted cases and the ten-cell overall mean
  are secondary; do not treat the latter as an unbiased deployment-demand mix.
- Secondary measures: per-run p95 delay, throughput, starvation counts, actual
  fallback/shield interventions and measured signal conflicts/clearances.
- Uncertainty: crossed bootstrap of training runs and paired traffic seeds,
  keeping the benchmark scenarios fixed. Three training runs remain a small
  sample; intervals are descriptive, not a guarantee of universal superiority.
- Do not tune on these results. Any subsequent development must label this
  evaluation as previously inspected and reserve fresh final evidence.

## Remaining publication requirements

Passing software tests and running 2,000 cells do not by themselves make a paper
ready. Required review includes simulator validity/calibration, truthful metric
definitions (the reported "queue" currently includes approaching/backlogged
vehicles), strong tuned baselines, matched-recipe ablations, seed sensitivity,
compute budgets, training provenance and positioning against existing research.
The v7 format is supported by the research controller path; website model loading
and end-to-end parity are not established. Do not upload/promote it as a verified
website/deployment replacement.

Relevant primary research guiding the evaluation approach:

- Agarwal et al., [Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264): few-run uncertainty and reliable comparisons.
- Zhang et al., [Expression might be enough](https://arxiv.org/abs/2112.10107): traffic-state representation and strong pressure-based baselines; pressure features alone are not a novelty claim.
- [Towards Robust Deep RL for Traffic Signal Control](https://arxiv.org/abs/1904.08353): robustness to demand, incidents and sensors is an existing research direction, not unique merely because faults were injected.
