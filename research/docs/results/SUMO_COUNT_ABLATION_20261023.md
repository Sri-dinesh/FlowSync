# Total-incoming-count SUMO ablation: complete, waiting/throughput trade-off

The [frozen component-test protocol](../protocols/SUMO_COUNT_ABLATION_20261023.md)
is implemented. This is project code and simulation evaluation; manuscript
files, existing policy checkpoints and application defaults are preserved.

## Completed full comparison

The user completed `results/sumo_count_ablation/full_20261023`: **15 new
180-second runs / 27,000 new signal samples**, paired with the existing
45-run / 81,000-sample classical reference. Collection took **165.20 seconds**,
inside the frozen 360-second cap. Saved-data verification was run again after
receiving the result and passes, reconstructing all new observations, proposals,
physical signals, inventory and waiting plus the anchored reused references.
It reruns **zero** traffic trajectories. All new sampled signals have zero
measured conflict/clearance violations.

| Controller | Mean wait per requested vehicle (s) | Average within-run p95 (s) | Average within-run maximum (s) | Mean completed trips | Mean switch onsets |
| --- | ---: | ---: | ---: | ---: | ---: |
| Halted | 6.784512 | 17.974667 | 24.446667 | 95.133333 | 13.333333 |
| Fixed | 10.238577 | 32.036000 | 40.173333 | 98.666667 | 5.000000 |
| Max-Pressure | 5.935522 | 16.457000 | 21.833333 | 101.400000 | 12.600000 |
| Total incoming | 6.362864 | 22.887667 | 41.886667 | 103.866667 | 8.933333 |

Removing outgoing-count subtraction raises aggregate mean waiting by
**0.427342 s / 7.1997%** against pressure and average within-run p95 by
**6.430667 s / 39.0756%**. It completes **2.466667 more trips per run** and
leaves 2.466667 fewer active vehicles, while final entry backlog is unchanged
case by case. This is a throughput/waiting trade-off, not an improvement over
pressure on the primary waiting endpoint. Ratios compare aggregate controller
means; p95/max are averaged within-run quantities, not pooled percentiles or
the single worst vehicle in the panel.

Mean waiting worsens in **13/15** cases versus pressure, p95 worsens in
thirteen, ties in one and improves in one. Completed trips improve in ten,
tie in two and fall in three. Only one case has lower mean waiting without
p95/trip loss. The two mean-wait gains are 110005 (+0.419565 s saved, +1.055 s
p95 saved, +1 trip) and 110105 (+0.187681 s saved, **-2.605 s p95 saved**, +5
trips). Neither case substitutes for the full primary result.

| Family (five cases) | Total counts extra mean wait vs pressure (s) | Extra p95 (s) | Completed trips gained |
| --- | ---: | ---: | ---: |
| Balanced | +0.098995 | +0.829000 | +0.400000 |
| NS dominant | +0.401592 | +9.624000 | +4.200000 |
| EW dominant | +0.781441 | +8.839000 | +2.800000 |

The secondary halted comparison saves 0.421648 s / 6.2149% mean waiting and
adds 8.733333 completed trips, but raises average p95 by 4.913 s; eleven of
fifteen p95 values worsen. Against Fixed, mean waiting falls 37.8540%, average
p95 falls 9.148333 s and completed trips rise 5.2, with p95 still worse in
two cases and trips lower in three. All cases/families remain in the report.

**Retain Max-Pressure as the waiting-oriented reference. Do not promote the
total-count variant or repeat this closed component collection.** The frozen
protocol defines no binary continuation gate; this is an unfavorable primary
component comparison, not a failed execution or retrospectively relaxed screen.
The flag values `anchor_replay_verified: false` and `total_repeat_verified:
false` are expected for the full job, which adds one run per case. Those checks
ran and passed in the separately preserved smoke; their false full-job flags
do not invalidate `verified: true`.

The [saved-trace trade-off diagnosis](../audits/SUMO_COUNT_TRADEOFF_20261023.md)
analyzes all thirty total/pressure trajectories without new traffic. In all
ten asymmetric-demand cases, total counts lower higher-demand-axis mean/p95
waiting and raise lower-demand-axis mean/p95 waiting. The latter's equal-case
mean rises from **4.480273 to 14.725864 s**. This identifies the distributional
cost in the recorded setup; it does not isolate green timing as a sole cause
or establish a learned-control or uncertainty contribution.

## Implemented comparison

The new `total_incoming` policy chooses the axis with more incoming vehicles,
including moving ones. It ignores outgoing/halted values but receives the
same validated clean packet as the existing policies. It holds ties and
respects the same minimum green and clearance. Decisions continue throughout
each episode; the new callback adapter passes only delivered counts and the
physical clock to the policy.

The completed full job added **15 new runs**, with 180-second horizons and a
**six-minute cooperative cap**, including reference verification. It reused the
verified halted, Fixed and Max-Pressure results for all fifteen cases. Original
network/routes/schedules and SUMO options are retained. It does not rerun the
old classical/future launchers. Source archives and hash anchors reject replaced
references, changed frozen dependencies, omitted cells and overwritten evidence.

The primary total-versus-pressure contrast measures removing outgoing-count
subtraction; the total-versus-halted secondary contrast measures replacing
halted counts with all incoming counts. Fixed remains visible. All per-case
and family comparisons retain delay, p95, trips and remaining inventory.
Positive saved waiting means the total-count policy has lower waiting than
the named reference. Aggregate p95/max are averages of within-run values.

These reuse **consumed development cases**, not new confirmation seeds. Neither
an improved component result nor execution completion is a new-controller,
learned-method or publication-readiness result. No training/promotion gate is
attached, and no policy parameters are tuned after the smoke.

## Completed mechanics and compatibility checks

Smoke artifact: `results/sumo_count_ablation/smoke_20261023`.
The isolated SUMO/traci/sumolib 1.24.0 environment completed three new 80-second
runs in **11.94 s**, inside its 120-second cap: one Max-Pressure anchor replay
and two total-count repeats on the separate mechanics schedule.

- The Max-Pressure **entire semantic trajectory** matches the original
  classical smoke repeat-zero trace exactly.
- Both total-count trajectories match each other exactly.
- All 120 new decision records reconstruct from delivered packets and clocks.
- All **2,400 new executed signal samples** have zero measured conflict or
  clearance violations. These are correlated mechanics samples.
- The saved-data verifier passes in Python 3.11 and 3.14. It separately checks
  the reused six-run/4,800-sample smoke reference; reused samples are not new
  trajectories. Verification reruns zero traffic trajectories.

`results/sumo_count_ablation/compatibility_20261023/report.json` also verifies
that the new callback checker reconstructs every metric of **all 45 saved
classical runs / 81,000 signal samples**, with no traffic rerun. Recorded raw
trace hashes and frozen inputs match; every halted, Fixed and pressure
packet/proposal/physical/metric contract is preserved. This check took 17.19 s
and stores checker-source/input provenance and matched run/metric hashes.

The 37 new tests pass, and the combined targeted SUMO suite passes **107 tests**
in the fresh Python 3.11 environment. The new checks cover moving
demand, ignored-input invariance, timing/ties, continuous proposals, equivalent
reference checking, unfinished/backlog waiting, changed raw records even with
updated hashes, anchor/repeat mismatch, replaced references, incomplete evidence,
all-case summaries, and partial-trace preservation on timeout/interruption.
The existing dependency deprecation warning remains; full frontend/backend
checks were not run. Repository checks also pass for 301 Python files and 424
local documentation links, and `git diff --check` is clean. Smoke controller
rankings are not a performance screen.

## Read-only inspection of the completed evidence

Verify both new and reused raw evidence without starting SUMO:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  -m research.audits.verify_sumo_count_ablation \
  results/sumo_count_ablation/full_20261023 \
  --reference results/sumo_classical_panel/full_20261023
```

Both original directories are required. Do not rerun their collection commands.
The new analysis is preserved at `results/sumo_count_analysis/audit_20261023`:
per-case axis statistics, matched requested-vehicle waits/completions, signals,
source archive and input/output hashes. Eleven new measurement tests pass, and
the combined targeted SUMO suite now passes **118 tests**. Full application and
frontend checks were not run.

`complete` and `comparison_complete` describe collection coverage. The full
report keeps all contrasts, individual cases, families and regression counts
regardless of sign. A cap/error report cannot pass as a completed comparison.
This result supports preserving outgoing-count subtraction for the declared
waiting-oriented comparison. Scope remains an empty initial intersection,
initial NS green, finite horizon, straight-only topology and previously observed
demand families. A future robustness study should freeze initial-phase and
horizon controls before new outcomes; that final bounded study is now
[completed separately](SUMO_ROBUSTNESS_20261023.md), with the observed trade-off
persisting under the tested changes and the component series now closed. No
new long training batch, model promotion or final-test claim follows.
