# Empirical-paper positioning — primary-source check, October 23

This is targeted positioning, not a systematic literature review or proof of
novelty. Abstract-level evidence and inspected methods are distinguished.
No competing implementation was independently reproduced. Authors' reported
numerical gains are not FlowSync results.

| Primary source | Evidence inspected | Overlap and consequence |
| --- | --- | --- |
| [Ault and Sharon, RESCO, 2021](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/f0935e4cd5920aa6c7c996a5ee53a70f-Abstract-round1.html) | Proceedings abstract. | Benchmarking and sensitivity to sensing/layout are established topics. A custom RL/classical comparison alone is insufficient differentiation. |
| [Mei et al., LibSignal](https://arxiv.org/abs/2211.10649v2) | Author abstract and publication metadata. | Unified evaluation across SUMO/CityFlow already exists. Source organization or number of experiments does not establish a novel benchmark. |
| [Zhang et al., Advanced-MP/Advanced-XLight, 2022](https://proceedings.mlr.press/v162/zhang22ah.html) | Proceedings abstract. | Running/queuing representations and pressure-based learning precede our spatial extension. Our historical/upstream pressure variants do not faithfully implement their baseline. |
| [Li et al., CFLight](https://arxiv.org/html/2512.09368v2) | Methods §§3.1–3.2, implementation appendix and discussion of simulator-query versus learned counterfactual dynamics. | A learned structural causal model generates alternative-action trajectories/objectives for safe RL. Our direct-simulator branch diagnostics do not originate counterfactual traffic control. The proposed comparison focuses on action-label variation under explicitly separated arrival streams and excluded-source learnability. Do not assert that their complete work omits a feature based on keyword search. |
| [Bodagala and Bodagala, UCATSC](https://arxiv.org/html/2602.07784v3) | Framework §§IV-A–IV-E, uncertainty/risk implementation §V and SUMO setup §VI. | Belief-space rollouts filter actions using predicted safety/service constraints. Its Monte Carlo calculation concerns uncertain speed/distance and dilemma-zone risk. Our arrival-future experiment asks a different empirical question, but uncertainty, counterfactual evaluation and hard constraints are already closely anticipated. Their model-relative properties are not evidence for our guarantees. |

The additional close uncertainty-gated DQN lead from the
[earlier triage](RESEARCH_NOVELTY_TRIAGE_20261022.md) remains full-text unverified.
Do not present this comparison as complete until its method is obtained or
the access limitation is explicitly retained. Journal/conference acceptance
and title/version metadata require primary publisher verification before final
bibliography formatting; arXiv version identifiers above are unambiguous.

## Candidate distinction to test

The strongest candidate is the measured separation of **observation/Q change,
action change, future-stable action advantage and excluded-source/full-run
benefit** in one auditable case study. The current evidence shows gaps along
this chain; it does not establish that these distinctions are new concepts.

The independent SUMO study has now [completed](../results/SUMO_FUTURE_PANEL_RESULTS_20261023.md)
with frozen states/choices and separate selection/check streams. Four of six
states have both delay-gain signs, but single/mean-eight choices coincide and
all selected saving is confined to one source. This establishes that limited
qualitative replication, not D3QN transfer, added averaging benefit, general
robustness, practical camera accuracy or superior control. It does not by
itself establish the novelty of studying this distinction.

## Explicitly excluded claims

- First uncertainty-aware, fallback, shielded or counterfactual traffic control.
- New pressure state representation merely from upstream counts.
- State-of-art performance without faithful contemporary baselines.
- A theorem or universal causal explanation derived from one project's failures.
- Publication worthiness inferred solely from negative results or test counts.

The manuscript can be completed on the declared schedule. Its eventual venue
fit still depends on how distinctive and well-supported this empirical
question is, including the independent replication and unresolved comparison.
