# Research contribution triage — 2026-10-22

The superior learned-controller objective remains unachieved. The new
teacher-disagreement experiment rules out blindly replacing the historical
teacher with upstream-only Max-Pressure at the tested 20-second horizon.
No publication-readiness percentage or breakthrough claim is justified.

## Primary-source checks

| Relevant work | Verified overlap | Consequence for FlowSync |
| --- | --- | --- |
| [Zhang et al., *Expression might be enough*](https://arxiv.org/abs/2112.10107), submitted 2021, revised 2022 | Advanced-MP uses queuing/running vehicles; Advanced-XLight combines its representation with RL. | Additional spatial inputs and a pressure teacher are insufficient novelty claims. Implementing an upstream-count variant does not reproduce Advanced-MP. |
| [Wang et al., *Learning the max pressure control … considering the phase switching loss*](https://www.sciencedirect.com/science/article/pii/S0968090X22001139), 2022, DOI 10.1016/j.trc.2022.103670 | Switching-curve MP, position weighting and policy-gradient optimization explicitly address switching loss. | A learned hold/switch threshold or clearance-aware pressure alone is already closely anticipated. It is a stronger baseline candidate, not automatically a new contribution. |
| [Li et al., *CFLight*](https://arxiv.org/abs/2512.09368), 2025 preprint | A counterfactual framework predicts alternative-action outcomes to improve intersection safety. | Do not claim the first counterfactual traffic-control method. Our branch-future diagnostics concern target stability and observed-input learnability, not their collision claim. |
| [T-REX robustness framework](https://link.springer.com/article/10.1186/s12544-026-00841-1), 2026 | Network-level incident modeling, reproducible robustness metrics and RL/classical benchmarking. | A custom single-intersection fault benchmark alone faces substantial prior-work and simulator-validity gaps. |

These methods were inspected in their primary abstracts/publisher pages, not
independently reproduced. No other paper's reported numerical improvements
are adopted as FlowSync evidence.

A particularly close bibliographic lead is *Uncertainty-Aware Gated DQN for
Robust Traffic Signal Control under Imperfect Sensing Conditions*, DOI
[10.1109/CAC67268.2025.11487190](https://doi.org/10.1109/CAC67268.2025.11487190).
Public indexes list the title, but the primary IEEE page was blocked by its
browser-verification gate. Its full method has NOT been verified. Obtain the
paper before making novelty claims about uncertainty-gated DQN. Do not cite
an index's abstract as a verified primary-method comparison.

These are targeted checks, not a systematic review or proof that a new
contribution cannot exist. The accessible sources establish concrete overlap
that must be addressed; a search returning no exact match would not prove novelty.

## What the current evidence can support

The defensible artifact is a reproducible simulation-only sequence of negative
ablations: checkpoint/decision-cadence errors can invalidate evaluations;
uncertainty about count error does not establish the benefit of fallback;
future-sensitive branch labels may fail to yield a useful observed-input
policy; extra inputs can move Q magnitudes without changing decisions; and
more geometrically specific demand need not improve closed-loop control.

An empirical methods/failure-analysis paper could center on the distinction
between hindsight action improvement, stability under separate futures, and
learned full-run improvement. That is a CANDIDATE framing. Novelty against
counterfactual-policy learning, action-label noise and robustness benchmarking
still requires a deeper review and external simulator replication. It does
not satisfy the original superior-controller objective by changing its label.

## Practical decision under the time constraint

1. Close failed recipes promptly; do not spend more episodes on the unchanged
   D3QN/spatial/teacher recipes or tune their screens retrospectively.
2. Distinguish short-horizon switch costs from longer-horizon payback using
   fixed-prefix replay. This is the bounded mechanism diagnostic in
   `TEACHER_HORIZON_PROTOCOL_20261022.md`; it cannot overturn the failed screen.
3. Before another learned-controller claim, require a reproducible development
   control gain, matched-information strong baselines (including a faithful
   research baseline), and a defined contribution beyond familiar ingredients.
   Do not treat the current historical Max-Pressure as Advanced-MP or SCMP.
4. Independently replicate the candidate finding in an established microscopic
   simulator before making broad traffic claims. SUMO/netgenerate executables
   were not found in this environment. No independent simulator was installed
   or silently substituted during these diagnostics.
5. Preserve the audited manuscript scaffold and evidence exports as dated
   snapshots. New results should be cited from their own protocols/raw files,
   not inserted into old frozen tables or pooled with inspected final panels.

There is currently no evidence-backed shortcut to a superior learned policy.
The fastest defensible progress is to reject unsupported hypotheses cheaply
and identify an effect that survives paired control and independent futures,
rather than relabel a classical heuristic or selected winning seed as a new
RL contribution.
