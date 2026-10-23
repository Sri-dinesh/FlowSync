# Initial-phase and horizon robustness — fixed final component study

Freeze before collecting these outcomes. Project implementation/evaluation only;
no paper writing, learning, controller tuning, checkpoint promotion or repetition
of the closed earlier collections. Complete this study and close this component
series regardless of sign. Do not choose a favorable start, horizon or seed.

## Fixed question, policies and physical boundary

Check whether the total-count/pressure waiting and completion trade-off survives
both initial green phases and a longer horizon on fresh arrival realizations.
Use the unchanged `max_pressure` and `total_incoming` implementations and their
same clean previous-step count packet. No future arrivals, IDs, rates, family
or backlog become controller features. Equal pressure/totals retain the current
phase. Preserve two-second decisions, eight-second minimum green, three-second
yellow, one-second all-red and the existing deterministic straight-only network,
entry FIFO, SUMO 1.24.0 and 0.1 s physical step. Start empty at NS or EW green;
both phase clocks and pending-phase state start consistently at age zero.

Keep all recorded source files unchanged. A reversible phase-label adapter may
reuse the frozen initially-zero signal engine: change internal binary phase
labels and lamp-axis labels together, map the clock/action to canonical NS/EW
at the policy boundary, and record canonical phase/action labels. Incoming,
outgoing and halted vectors, vehicle/arrival records, lamps, ages, stage and
waiting must never be rotated or substituted. Verify canonical executed lamps
independently and test EW->NS clearance explicitly.

Pinned source SHA-256 values:

| Source | SHA-256 |
| --- | --- |
| `research/policies/sumo_classical.py` | `15c66f3f47507496204595823d026df6d4bc25bacd8d5456918ce8a1d2c30be1` |
| `research/policies/sumo_total_count.py` | `2c39bea997473584606bdc73a3621e733b88b8a7148d4ef2ac2afe4206ea3342` |
| `research/audits/sumo_branch_feasibility.py` | `f150579af1bb14befaf2f9af2a930929b532dcc77639dc7d78bb4672bbed329b` |
| `research/experiments/sumo_observed_episode.py` | `2aa8f40f5ddf37679e61cdaf76e1774b61696723e100d7c88717584e985df73e` |

## Cases, endpoints and budget

| Family | Per-approach NS/EW rate (vehicles/s) | Traffic seeds |
| --- | --- | --- |
| Balanced | 0.20 / 0.20 | 112001, 112002 |
| NS dominant | 0.30 / 0.10 | 112101, 112102 |
| EW dominant | 0.10 / 0.30 | 112201, 112202 |

These seeds were absent from the preserved manifest/plan/case/documentation
records checked before implementation. They are new arrival realizations in
known families/topology, a robustness study rather than independent final
validation or a population sample.

Six traffic seeds x two initial phases x two controllers = **24 runs**, each
**360 seconds / 3,600 ticks**, with an empty initial state. Generate/freeze
the entire schedule before any run and pair it across both starts/policies.
SUMO seed remains 110000. Main endpoint is **360 seconds**. Also report the
predefined **180-second prefix** of the same run using only requests due before
that endpoint. No separate full-job 180-second rollout, warmup discard, drain
extension or post-hoc endpoint selection. Prefix and long-run measurements
overlap and are not independent replications. Unique executed sample count:
**86,400**, not the sum of both endpoint coverage counts.

Full cooperative cap: **900 seconds / fifteen minutes**, including setup and
measurement reconstruction. The user runs this job after mechanics pass.
Preserve partial gzip traces and failure status on timeout/interruption;
incomplete subsets cannot be scored as complete.

Smoke: separate balanced seed **112901**, 80-second episodes and a 40-second
prefix. Both starts, both policies, two identical repeats = eight episodes.
Add one separate 40-second pressure prefix replay per start = two more runs.
Total **ten new runs / 7,200 unique signal samples**, 180-second cap. Repeats
must match exactly; each short pressure trajectory must match the corresponding
longer pressure prefix exactly. Smoke is mechanics only; do not use its
rankings to tune policies or label it the 24-run study.

## Measurements, hierarchy and interpretation

Primary: total-count versus pressure mean stopped waiting per requested vehicle
at 360 seconds, with all stopped active vehicles and entry backlog included.
Report p95/max accumulated waiting, completed network exits, final inventory,
endpoint waiting, switches and mean/p95 waiting by axis. Lower/higher-demand
roles use declared family rates for evaluation only. Phase absence of green
with stopped demand is not individual waiting or a claim of no yellow discharge.
All p95/max aggregates are averages of within-run or within-axis values.

For each endpoint retain all twelve seed/start paired contexts, every controller
mean and all per-axis values. Average both starts within each traffic seed,
then average six traffic seeds for the aggregate. Report phase-specific and
family summaries and seed direction counts. There are **six traffic replicates**,
not twelve independent starts, 24 independent policies or thousands of independent
vehicles/frames. The asymmetric subset contains four seeds and eight start
contexts. Include both endpoints, phase/horizon sign changes and unfavorable
cases. No significance test or population interval is planned.

Execution completion is a coverage decision, not a favorable-result screen.
If the observed finding changes with phase/horizon, record that limitation;
if it persists, retain it as bounded robustness evidence. Neither outcome
establishes a new learned method, steady-state behavior, general fairness
guarantee, real-world validity, publication readiness or automatic learning
continuation. No thresholds or additional follow-up batches are selected from
these results in this component series.

Archive sources/protocol, configuration, exact schedules, command, every raw
decision/lamp/vehicle/request trace, endpoint metrics, paired summaries and
output hashes in a new directory. The read-only verifier reconstructs all
packets/actions, phase mapping, physical state, FIFO/inventory/waiting, axis
profiles and hierarchical summaries. Reject collisions, teleports, SUMO pending
departures and invalid signals during collection. Verification reruns zero
traffic. Old experimental data and manuscripts remain preserved.
