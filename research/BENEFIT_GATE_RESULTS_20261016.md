# Benefit-gate experiment: completed, not promoted

**Decision: keep this gate opt-in for research. It does not improve over
shield-only D3QN and does not establish research-paper readiness.** No existing
checkpoint, website default, prior test result or Supabase artifact was replaced.

## Frozen design and training data

The [protocol](BENEFIT_GATE_PROTOCOL_20261016.md) was written before collecting
labels or running this experiment's validation. Its SHA-256 is
`2a8607b61318a5298fb502e3adf6ce88817911336111f416e47b7be4aacda61a`.

All 216 training-split source rollouts completed: six training templates,
traffic seeds 91001–91006, clean/mixed faults, all three selected v5 policies.
There were 300 paired counterfactuals including shield diagnostics, with
matching branch arrivals and complete 200-tick signal-audit coverage. Source
rollouts contributed 259,200 signal samples; forks contributed 120,000.
No conflict/clearance violations were measured. Archive/source hashes verified.

There were 186 eligible, non-hard-stale fallback comparisons. Forty met the
positive target (lower incremental waiting and no worse endpoint maximum
upstream accumulated wait); 146 did not. These are correlated first-event
samples, not 186 independent experimental replications. No validation events
were used to fit the gate.

The fixed L2=0.1 logistic fit succeeded. At the predeclared threshold 0.5 it
predicted entry for **zero** training examples. The threshold was not lowered
after seeing this result. The model uses only the eight observable features,
and is bound to the recorded checkpoint family and uncertainty-calibration hash.

Gate artifact: `results/benefit_gate/train_20261016/benefit_gate.json`

Gate SHA-256:
`561e921366d6369199b64eaa10d465eb47559800e2cfd642bb1cbdb9a84e016f`

## Matched validation: all 270 planned runs completed

All three selected policies, three validation templates, traffic seeds
21001–21005, two fault profiles and three intervention arms. Each arm contains
90 runs; no best-policy-seed selection. These are reused development-validation
conditions, **not new final-test evidence**.

| Variant | Mean delay (s) | Mean within-run p95 (s) | Mean throughput | Fallback activations |
| --- | ---: | ---: | ---: | ---: |
| Shield-only D3QN | 10.864244 | 36.973556 | 84.488889 | 0 |
| Original full UQ | 11.204756 | 38.081000 | 84.255556 | 85 |
| Gated full UQ | 10.864244 | 36.973556 | 84.488889 | 0 |

The gate vetoed all 106 entry evaluations. All 90 gated/shield-only pairs
matched on recorded delay, p95, throughput, shield interventions, starvation
counts, fallback steps and fallback activations. The apparent ~3.04% mean-delay
improvement over original UQ comes from suppressing fallback, not from
outperforming shield-only D3QN or learning a useful selective switching policy.

Under mixed faults alone, mean delay is 11.485844 s for original UQ and
10.804822 s for both shield-only and gated variants. Clean means are identical
at 10.923667 s. Three original-UQ clean fallback activations did not change
these recorded clean traffic metrics.

All exact planned cells, checkpoint/gate/calibration provenance, source archives,
paired arrivals and finite traffic metrics were checked. There are 324,000
validation signal-audit samples, covering every tick, and zero measured
conflict/clearance violations. This is not a collision or road-safety guarantee.
Hard-stale bypass and dwell/shield behavior are regression-tested; the absence
of gated fallback here does not exercise the hard-stale path in these scenarios.

The runtime gate remains optional. Invalid numeric feature vectors preserve the
original uncertainty supervisor; stale observations bypass the gate; active
fallback retains its dwell/recovery logic; the shield and physical FSM remain
unchanged. **The fairness label is a prediction target, not a runtime bound.**

## Implementation and verification

- `research/uncertainty/benefit_gate.py`: observable feature extraction and
  provenance-bound logistic gate.
- `server/app/controllers/flowsync_uq.py`: optional latched entry gating;
  default behavior unchanged, with gate diagnostics added.
- `research/fit_benefit_gate.py`: training-only fit; rejects incomplete,
  duplicate, unpaired, nonfinite or insufficient-label datasets.
- `research/audit_control_interventions.py`: observable features, split tags,
  and automatic source snapshots for future audits.
- `research/evaluate_validation.py --benefit-gate PATH`: matched three-arm
  validation with provenance, gate counts and complete signal-audit checks.
- 157 targeted regression tests passed, including 22 gate-specific tests.

Artifacts are under `results/benefit_gate/train_20261016/` and
`results/benefit_gate/validation_20261016/seed_{101,202,303}/`.
Each validation folder contains `configuration.json`, `runs.jsonl`,
`summary.json`, per-run bundles and `source_snapshot.zip`.

## Next decision

Do not launch a larger final-test suite or retrain the identical RL recipe on
the basis of this experiment. Do not advertise the gate as a successful novelty.
It reproduces an existing ablation, while the frozen v5 result against
Max-Pressure remains unchanged.

The next learning investigation should measure **which feasible RL phase
decisions lose to the teacher under the same shield**, on training-only paired
rollouts. Include actual action disagreement, switch/clearance cost and the
phase-service fairness objective. This can distinguish an observation/objective
limitation from an optimizer problem before spending another training budget.
Do not leak offline simulator waiting times into deployed observations.

If benefit gating is revisited, a separately declared experiment needs evidence
that observable features distinguish beneficial from harmful controller choices,
not just high perception error. Lowering a threshold to force activations is
not evidence of that distinction. Any new method must retain the shield-only
control and all policy seeds, and earn a new frozen evaluation only after a
meaningful validation improvement.
