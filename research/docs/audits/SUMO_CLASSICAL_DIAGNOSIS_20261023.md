# Saved-data diagnosis of the executed classical SUMO panel

Input: the [completed 45-run development comparison](../results/SUMO_CLASSICAL_BASELINES_20261023.md).
Output: `results/sumo_classical_analysis/audit_20261023`.
Implementation: [analysis utility](../../analysis/analyze_sumo_classical_panel.py).
No traffic trajectory, model fitting, manuscript editing or policy promotion
is performed. The original collection and its source archive remain unchanged.

## What is recomputed

The utility first runs the full saved-data verifier, then reconstructs waiting
by requested origin and physical location, signal-stage exposure, and proposal
comparisons from every saved delivered packet and pre-action signal context.
It records all mean/tail/throughput regressions and checks that each halted/
pressure pair has an identical complete history until its first differing
proposal. All fifteen pairs pass that history check.

`paired_cases.csv` retains all thirty pressure-versus-reference case rows.
`trace_measurements.json` retains all 45 trajectory measurements.
`first_proposal_splits.json` retains all fifteen common-prefix split states.
`report.json` includes direction counts, input/output hashes, archived analysis
source hashes and scope. `analysis_source.zip` preserves the new analysis and
its local helper/verification dependencies.

The primary mean waiting and all saved summaries still reconstruct. Pressure
improves mean waiting in 14/15 cases versus halted, but p95 worsens in three and
completed trips fall in one. The result note keeps those cases explicitly;
do not reduce the panel to a favorable aggregate percentage.

## Incoming and outgoing information change different proposals

On each same delivered state, compare three action calculations: halted-count
control, a shadow using total incoming counts, and the executed pressure rule.
They share current-phase tie handling, minimum green and clearance rules. The
total-count shadow is **not executed**; no outcomes are assigned to its proposals.

| Observed trajectory | All decision samples | Eligible green decisions | Halted differs from total | Total differs from pressure | Halted differs from pressure |
| --- | ---: | ---: | ---: | ---: | ---: |
| Halted | 1,350 | 323 | 121 | 37 | 114 |
| Fixed | 1,350 | 915 | 321 | 201 | 138 |
| Pressure | 1,350 | 377 | 198 | 73 | 135 |

Eligibility requires green age >=8 s; all other proposals hold for physical
timing. Frames are correlated and each policy visits different states. These
counts are not independent samples or counterfactual control gains.

At the first halted/pressure divergence, total incoming counts agree with
pressure in **14/15** cases. Only source 110103 requires outgoing subtraction
to produce the first pressure proposal: halted counts are all zero, incoming
NS/EW counts are 6/4, outgoing destination counts yield phase pressures 3/4,
and pressure requests EW while the other calculations retain NS.

Later differences also matter: outgoing subtraction changes **73 of 377**
eligible decisions on the pressure trajectories. In 130 of the 135 eligible
halted/pressure disagreements there, total incoming counts agree with pressure;
in the other five, halted and total agree. Another 68 eligible states have
halted and pressure agreeing while total counts would differ. Thus agreement
at initial splits does not imply the outgoing component is inactive later.
Neither pattern proves the sign of its traffic effect.

## Waiting and timing attribution

Pressure saves a mean **120.080 vehicle-seconds per paired run** versus halted.
Location attribution is 107.733333 on incoming lanes plus 12.346667 in external
entry backlog; no stopped waiting is recorded on outgoing/internal edges.
The separate origin partition gives N/S/E/W savings of 38.420000, 42.520000,
25.353333 and 13.786667 vehicle-seconds. Each partition sums to the same total;
do not add location and origin partitions together. These raw integral gains
are distinct from the primary 0.848991 s mean per-requested-vehicle saving,
which normalizes each case before equal-case averaging.

Mean executed green time is 130.000 s for pressure versus 126.933333 s for
halted, with mean switch onsets 12.6 versus 13.333333. This is a timing
association, not an isolated causal clearance effect. Fixed has 160 s total
green, split NS/EW 90/70 s over the declared 180 s episode. Its larger green
total does not by itself imply lower waiting. The shared initial NS phase
and truncated horizon are part of this development setup; they are not a
counterbalanced or steady-state evaluation.

## Project decision and limits

The full result establishes a stronger classical reference for this SUMO
setup and weakens any interpretation of the earlier one-state hindsight
gain as evidence of a novel controller. It evaluates no FlowSync checkpoint
and establishes no learned-control or uncertainty contribution.

The next bounded component experiment should **execute** total-incoming-count
control, keeping delivered packets, ties, timing, insertion, metrics and all
classical references matched. Freeze its protocol, budget and comparisons
before collecting its outcomes; reused cases remain development data. The
present shadow analysis cannot decide whether removing outgoing subtraction
helps or hurts. That experiment is now
[complete and verified](../results/SUMO_COUNT_ABLATION_20261023.md): total counts
raise mean/p95 waiting against pressure while increasing completed trips.
No renewed long DQN training, relaxed old continuation screen or final-test
claim follows from this diagnosis.

Eleven new helper tests cover physical eligibility, the three information
effects, conservation/units of waiting partitions, first-split history checks,
trade-off counts and read-only output boundaries. Together with the previous
SUMO checks, **70 tests pass** in the fresh Python 3.11 environment, with one
existing dependency deprecation warning. Full frontend/backend tests were not
rerun. The raw full comparison verifier separately passes in the existing
Python 3.14 environment; postprocessing reruns zero traffic trajectories.
