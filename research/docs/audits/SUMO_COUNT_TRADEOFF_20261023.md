# Total-count trade-off: longer waits on lower-demand axes

Input: the [completed total-count ablation](../results/SUMO_COUNT_ABLATION_20261023.md)
and its anchored classical references. Output:
`results/sumo_count_analysis/audit_20261023`. The
[analysis utility](../../analysis/analyze_sumo_count_ablation.py) verifies the full
collection, then measures all fifteen total/pressure pairs: **30 stored
trajectories**, zero new traffic rollouts, fitting steps or policy promotions.
Original source archives, protocols and results remain unchanged. No manuscript
file is edited.

## Waiting and completion attribution

Each requested ID is paired across policies using its recorded origin, not
its spelling. Accumulated stopped waiting includes entry backlog and unfinished
vehicles; completed and zero-wait vehicles remain in the denominator. The
lower/higher-demand role follows the already declared NS/EW arrival rates,
not realized outcomes or a fitted threshold. These labels are evaluation-only.

All ten asymmetric cases show the same direction: total counts reduce mean
and p95 waiting on the higher-demand axis and increase both on the lower-demand
axis. The table averages each case-axis statistic equally across those ten
cases; it is not the overall per-requested-vehicle panel mean or pooled p95.

| Axis role / policy | Mean wait (s/requested vehicle) | Average within-axis p95 (s) | Average completed trips | Mean longest absence of green with stopped demand (s) |
| --- | ---: | ---: | ---: | ---: |
| Lower demand / pressure | 4.480273 | 14.745000 | 24.5 | 16.39 |
| Lower demand / total counts | 14.725864 | 42.708000 | 22.7 | 49.70 |
| Higher demand / pressure | 6.696174 | 17.071000 | 74.6 | 16.00 |
| Higher demand / total counts | 4.457403 | 13.575000 | 79.9 | 16.00 |

This is a distributional cost of the observed policy change: higher-demand
axes gain 5.3 completed trips per case while lower-demand axes lose 1.8 in
the asymmetric cases. More total completions do not imply everyone benefits.
Across all fifteen cases, the **2,135 matched requested vehicles** include 676
with lower accumulated waiting, 946 unchanged and 513 worse under total
counts. There are 72 additional completions and 35 lost completions: net 37,
or the recorded 2.466667 per-run gain. Vehicles/frames are correlated and do
not become 2,135 independent traffic replicates. No population inference is made.

## Signal exposure is separate from individual waiting

The analysis records continuous intervals with no executed green for an axis,
including initial/terminal partial intervals. Its stopped-demand variant
requires a halted incoming vehicle or external entry backlog for that axis
throughout the interval. These are phase exposure measurements, not vehicle
waiting timers or proof of zero discharge on yellow. All recorded lamp and
clearance rules still pass. Transition correctness does not establish an
acceptable waiting distribution.

Total counts have fewer switches on average (8.933333 versus pressure's
12.6), and lower-demand axes have substantially longer periods without green
while stopped demand is present. This describes the observed timing and harm
together; green timing was not independently varied to isolate it as the
sole cause. The controlled component removed outgoing subtraction from the
declared pressure variant; the resulting whole-episode comparison applies
to these consumed cases and this simulator boundary.

## Reproducibility and project decision

`case_axes.csv` preserves all sixty controller/case/axis rows.
`paired_vehicles.csv` preserves all 2,135 same-ID comparisons.
`signals.json` records every case's signal exposure. `report.json` contains the
verified primary comparison, descriptive role summaries, input/output hashes
and source hashes; `analysis_source.zip` archives the implementation and local
dependencies. All waiting partitions and paired integral differences conserve
the verified stopped-wait totals.

Eleven new tests check backlog/unfinished/zero-wait denominators, phase-exposure
units, conserved identities, malformed records, declared demand-role assignment,
and protected input directories. The combined targeted SUMO suite passes **118
tests**, with one existing dependency deprecation warning. Full frontend/backend
tests were not rerun.

Keep pressure as the waiting-oriented reference and retain total counts as a
negative primary ablation with a throughput gain. Do not promote a winning
seed, reinterpret the halted/Fixed gains as pressure superiority, tune a new
wait threshold against these cases or rerun the closed collection. No causal
optimizer defect or new learned-policy benefit is established. A later bounded
robustness study should explicitly address initial phase and finite horizon;
the [subsequent fixed study](../results/SUMO_ROBUSTNESS_20261023.md) is now
complete and verified, retaining the observed trade-off under both tested
starts/horizons. The component series is now closed.
