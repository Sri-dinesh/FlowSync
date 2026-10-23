# Initial-phase/horizon robustness: complete; component series closed

The [fixed protocol](../protocols/SUMO_ROBUSTNESS_20261023.md), runner, endpoint
measurements and standalone verifier are complete. This was the last planned
component study in this series. **The component series is now closed.**
Project scope remains simulation code/evaluation. Manuscript files, original
experimental data, policy implementations and application defaults are preserved.

## Full outcome and independent saved-data verification

The user completed `results/sumo_robustness/full_20261023`: **24 runs**, six
traffic seeds, twelve paired seed/start contexts and **86,400 unique executed
signal samples**. Collection took **379.23 seconds / 6.32 minutes**, inside
the 900-second cap. Saved-data verification was run again after receiving the
result and passes. It reconstructs every delivered packet/action, phase label,
physical state, request/FIFO/inventory, stopped-wait integral, axis profile and
hierarchical comparison. Verification reruns **zero** traffic trajectories.
All recorded signal-conflict/clearance checks pass. These are simulated signal
measurements, not collision or real-world safety validation.

Positive saved waiting in the raw report favours total counts; the following
table instead shows the **extra cost of total counts** to make the outcome clear.

| Endpoint | Pressure mean wait (s) | Total-count mean wait (s) | Extra mean wait (s) | Extra average p95 (s) | Completed trips gained per run |
| --- | ---: | ---: | ---: | ---: | ---: |
| 180 s prefix | 6.317717 | 6.689734 | +0.372018 | +5.475833 | +4.083333 |
| 360 s primary | 7.745665 | 8.083196 | +0.337531 | +7.378333 | +6.666667 |

At the primary endpoint, total counts raise mean waiting by **4.3577%** and
average within-run p95 by **39.4995%**. Pressure/total mean completed trips are
248.666667/255.333333; their average p95 values are 18.679583/26.057917 s.
At the prefix endpoint, mean waiting is 5.8885% higher and p95 is 31.6141%
higher under total counts. Percentages compare controller aggregate means.

The aggregate trade-off holds for both starts:

| Endpoint | Starting green | Total-count extra mean wait (s) | Extra average p95 (s) | Trips gained |
| --- | --- | ---: | ---: | ---: |
| 180 s | NS | +0.456894 | +5.725833 | +4.500000 |
| 180 s | EW | +0.287142 | +5.225833 | +3.666667 |
| 360 s | NS | +0.331630 | +7.292500 | +6.666667 |
| 360 s | EW | +0.343432 | +7.464167 | +6.666667 |

After averaging both starts within each seed, mean waiting is worse for total
counts in **five of six seeds at both endpoints**. At 360 s, p95 is worse in
all six seeds; trips improve in five and fall in one. No strict mean-wait sign
reversal is detected between starts or between the two endpoints. The twelve
individual contexts include ten mean-wait regressions at each endpoint and
eleven p95 regressions at 360 s; they remain correlated start conditions,
not twelve independent traffic replicates.

The balanced family is an explicit exception to aggregate mean-wait dominance:
its primary mean favours total counts by 0.246080 s, while average p95 worsens
by 0.450000 s. Seed 112002 improves primary mean waiting by 0.656067 s but
worsens p95 by 0.200000 s and loses 0.5 trips after averaging starts. Retain
these favourable/unfavourable metrics together; pressure does not dominate
every case or every metric.

## Distributional finding persists in the tested variants

In **all eight asymmetric seed/start contexts**, total counts worsen lower-rate
axis mean/p95 waiting and improve higher-rate axis mean/p95 waiting at both
endpoints. The table averages case-axis values across both starts within the
four asymmetric traffic seeds. Its p95 is an average within-axis percentile,
not a pooled percentile or the overall panel p95.

| Endpoint | Axis role | Pressure mean wait (s) | Total-count mean wait (s) | Extra total-count wait (s) | Total-count trips gained |
| --- | --- | ---: | ---: | ---: | ---: |
| 180 s | Lower arrival rate | 5.830394 | 14.726574 | +8.896180 | -2.625000 |
| 180 s | Higher arrival rate | 7.069254 | 5.020584 | -2.048669 | +8.750000 |
| 360 s | Lower arrival rate | 6.149682 | 17.153860 | +11.004178 | -5.500000 |
| 360 s | Higher arrival rate | 8.439932 | 5.640937 | -2.798995 | +14.625000 |

At 360 s, lower-rate-axis average p95 rises 18.434375 -> 45.521250 s, while
higher-rate-axis p95 falls 19.190000 -> 15.503750 s. Mean longest absence of
green with stopped demand on the lower-rate axis rises 21.0875 -> 51.3250 s.
That phase exposure is not an individual wait timer or proof of no yellow
discharge. Timing and waiting harm occur together; timing was not independently
varied to establish it as the sole cause.

The finding survives the two tested initial phases and longer horizon in this
panel. It does not establish behavior for every initialization, horizon,
network, demand process or noise condition. Six seeds, only two per family,
and four asymmetric seeds remain a small descriptive robustness scope.

**Decision:** retain pressure as the waiting-oriented reference, preserve total
counts as a throughput/unequal-waiting ablation, and close this component series.
No controller tuning, additional rollout batch, automatic learning, model
promotion or new-controller/IEEE-readiness claim follows. Reliable learned
superiority and useful uncertainty supervision remain unachieved.

## Full design and what it addresses

The completed design compared Max-Pressure and total incoming counts on six new
traffic seeds in the same three demand families. It executed every schedule from an
empty intersection, once starting with NS green and once with EW green, for
both controllers: **24 runs**, each **360 seconds**, **86,400 unique executed
signal samples**, with a **fifteen-minute cooperative cap**.

The primary endpoint is 360 seconds. The fixed 180-second prefix is also
reported from the same trajectory, using only arrivals due before its endpoint.
No extra full-job short-horizon simulation or favorable-horizon selection occurs.
Prefix/full measurements overlap and do not add independent samples.

| Family | NS/EW rate per approach (vehicles/s) | New traffic seeds |
| --- | --- | --- |
| Balanced | 0.20 / 0.20 | 112001, 112002 |
| NS dominant | 0.30 / 0.10 | 112101, 112102 |
| EW dominant | 0.10 / 0.30 | 112201, 112202 |

The main question is whether the observed mean/tail/throughput and axis waiting
trade-offs survive changed starting phase and a longer horizon. These are new
arrival realizations in known demand families/topology, not a new simulator,
steady-state study or independent final validation. Original controller and
physical-source hashes are pinned before collection. No policy parameter,
wait threshold, additional shield or observation is tuned.

Both phases reuse the frozen physical step and delivered-count episode engine.
A reversible internal phase-label mapping provides EW startup; the policy and
stored trace retain canonical NS/EW phase/action labels. Vehicle edges, counts,
packets, lamps, requests, ages, clearance and waiting are unchanged by the
mapping. Policies receive only canonical counts and physical context.

The report preserves every seed/start/endpoint and per-axis mean/p95 waiting,
completed trips, inventory and signal exposure. It averages starts within each
traffic seed before the aggregate: **six traffic replicates**, twelve paired
start contexts and 24 policy runs. The asymmetric subset contains four seeds
and eight contexts. Vehicle/frame counts, starts and the two endpoints do not
become independent replicates. All p95/max summaries average within-run or
within-axis values. Phase absence of green is separate from vehicle waiting.

## Completed mechanics

Artifact: `results/sumo_robustness/smoke_20261023`.
SUMO/traci/sumolib 1.24.0 completed ten runs in **47.18 seconds**, inside its
180-second cap. The separate mechanics seed 112901 supplies eight 80-second
episodes (both starts, both policies, two identical repeats) and two separate
40-second pressure replays, one per start.

- Each repeated full trajectory matches exactly for both policies and starts.
- Each separate pressure short run matches the corresponding long-run prefix
  exactly, including requests, vehicles, clocks, decisions and lamps.
- Both canonical starting phases and their clearance transitions reconstruct.
- All **7,200 unique executed signal samples** pass the timing/conflict audit.
- The raw verifier passes in Python 3.11 and Python 3.14, with zero traffic
  reruns. It also reconstructs both endpoint and axis measurements.

`results/sumo_robustness/canonical_check_20261023/report.json` separately records
direct canonical `Signal(phase=start, pending=start)` reconstruction without
using the phase-label adapter: all 7,200 recorded signal states and **360
delivered decisions** match the frozen policy/clock rules. This postprocessing
is not an independent traffic rollout or an additional safety sample.

The **147-test targeted SUMO suite passes**, including 29 new checks for canonical
EW->NS timing, unchanged packet/vehicle semantics, reversible labels, fixed
prefix denominators, six-seed aggregation, phase/horizon sign changes, exact
prefix/repeat matching, tampered metrics and missing/extended traces, scope
relabelling and partial-output preservation. One existing dependency deprecation
warning remains. Full application/frontend suites were not run.

Smoke rankings are not reported as controller-performance evidence. Its
40/80-second endpoints cannot be relabelled as the full 180/360-second study.
The full study subsequently completed separately, as recorded above.

## Read-only evidence and closure export

Do not repeat the completed launcher. Verify saved raw evidence without starting SUMO:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  -m research.audits.verify_sumo_robustness \
  results/sumo_robustness/full_20261023
```

`results/sumo_robustness/closure_20261023` contains eight CSV tables with every
controller, endpoint, phase, family, seed, paired context, axis profile and
signal exposure. No cases are filtered out. It also preserves exact collection
report/manifest copies, exporter source, input/output hashes and verification
scope. The [read-only exporter](../../evidence/export_sumo_robustness.py) starts
no simulation or fitting and writes no manuscript. Balanced-family lower/higher
fields are blank to mean not applicable, not zero. The 180-second prefix is
not a separate evaluation run. Do not pool these six seeds with prior panels
or count starts/vehicles as independent replicates.

`complete` and `robustness_complete` are coverage flags. The full report's
`mechanics` entries say `smoke_only`; those exact-repeat checks already passed
in the separate smoke and are not repeated during the 24-run job. The full
report retains both endpoints, all phases/families/seeds, direction counts and
sign changes. No favorable-result gate, automatic training or promotion exists.
The completed series is closed; collection completion is not publication readiness.
The original learned-controller superiority and useful-UQ goals remain unachieved.
