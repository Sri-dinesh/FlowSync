# Independent SUMO future-arrival panel — complete and verified

Protocol: [frozen SUMO design](../protocols/SUMO_FUTURE_PANEL_20261023.md).
Artifact: `results/sumo_future_panel/full_20261023`.
Paper export: `results/paper_evidence/sumo_future_20261023`.

## Outcome

All **204 forty-second branches** across **six source states** complete in
1,001.65 seconds (16.69 minutes), within the 30-minute cap. The three demand
families each contribute two sources. Every source has seventeen paired
futures: one single-choice selection future, eight mean-choice selection
futures and eight separate check futures. Sensing is clean, driving is
deterministic and continuation uses halted-count control, with shared physical
timing. No FlowSync checkpoint is trained or evaluated here.

In the 48 check cases, the alternative saves >1 vehicle-second of stopped
waiting in **26**, loses >1 in **19**, and lies within the ±1 deadband in **3**.
**Four of six gates have both signs across their eight futures.** This is a
qualitative replication of future-dependent action labels in an independent
simulator under the declared setup, not a population frequency estimate.

| Source | Demand family | Gate time (s) | Positive / negative / deadband check futures | Both selectors change baseline? | Selected mean delay saved (vehicle-seconds) |
| --- | --- | ---: | --- | --- | ---: |
| 109001 | Balanced | 68 | 8 / 0 / 0 | No | 0.000 |
| 109002 | Balanced | 68 | 5 / 1 / 2 | No | 0.000 |
| 109101 | NS dominant | 60 | 1 / 6 / 1 | No | 0.000 |
| 109102 | NS dominant | 68 | 8 / 0 / 0 | Yes | 47.725 |
| 109201 | EW dominant | 70 | 1 / 7 / 0 | No | 0.000 |
| 109202 | EW dominant | 70 | 3 / 5 / 0 | No | 0.000 |

The sign counts describe the alternative action at every gate, including gates
where a selector retains baseline. They are not harmful-case counts for the
selected rule. Joint selection also constrains throughput and endpoint wait;
a delay-favorable alternative need not satisfy those conditions. For example,
source 109001 has eight positive-delay check futures, but its alternative's
mean completed-trip gain is −0.75 and endpoint-wait saving is −2 seconds.
No thresholds are relaxed after observing those outcomes.

## Local improvement and concentration

Single-future and mean-eight selectors make **identical choices at all six
gates**, changing only source **109102**. At that gate all eight check cases
meet the joint benefit condition, with mean delay saving **47.725
vehicle-seconds**, zero completed-trip loss and **1.4 seconds** mean endpoint
maximum-wait saving. Delay savings range from 33.3 to 54.6 vehicle-seconds.

Averaging equally over all six sources, each selector saves **7.954167
vehicle-seconds**, gains **0 completed trips**, and saves **0.233333 seconds**
of endpoint maximum accumulated wait. Eight changed cases qualify and none
is harmful in the recorded check set; forty cases retain baseline. Every
aggregate saving comes from one source state. Removing that state leaves
zero selected gain. This descriptive concentration check is not a new
selection rule or independent test.

There is **no measured added averaging benefit** in this panel. The local
benefit belongs to simulator-hindsight choices, not a learned predictor or
the original D3QN. It does not demonstrate full-run superiority over
Max-Pressure, Advanced-MP or other strong controllers. No performance-pass
screen was specified for this empirical panel; completion should not be
labelled an algorithmic breakthrough.

## Verification and evidence export

The saved-trace verifier was independently invoked after the user's run and
passes. It checks source/output/archive hashes, complete source/future
partitions, paired requested arrivals, first-action execution, physical signal
timing and raw vehicle/backlog wait integrals, then reconstructs choices and
summary scores. Coverage is **4,040 saved source ticks** and **81,600 branch
ticks**, with zero measured conflict/clearance violations. Replayed histories
and branched futures overlap; these are not independent safety samples.

The paper exporter additionally aggregates gains and joint constraints with
independent decimal arithmetic. It reproduces the sign counts, frozen
selection choices, per-source/aggregate means and benefit/harm counts, and
exports 102 future-pair rows, six source rows, selector summaries and a
PNG/PDF/SVG figure with provenance. This postprocessing reruns **zero traffic
trajectories**; it does not independently recreate the simulation dynamics.

The unified manuscript ledger now reconstructs **148 quantities across nine
separate panels** and binds the updated draft's hash. All 25 targeted evidence
and SUMO helper tests pass in the fresh Python 3.11 environment, with one
existing dependency warning. Repository/link and diff checks pass. These are
targeted checks, not a rerun of the full application/frontend suite. The
executed SUMO runner, shared mechanics and frozen scientific protocol still
match their saved source hashes.

## Interpretation and next action

The finding strengthens the paper's distinction between a favorable branch,
a future-stable action, and a useful learned/full-run controller. It also
preserves a favorable local example: the selected action at one state helps
all eight check futures, while averaging supplies no extra benefit there.
Neither all labels being unreliable nor averaging universally helping follows.

Limitations include six gates on one generated topology, two source seeds per
demand family, correlated futures, deterministic driving, clean sensing, a
forty-second horizon and simulator-assisted selection. Completed trips at the
SUMO network boundary differ from the custom simulator's passed-vehicle metric;
do not pool their means or attach its main-evaluation interval to this panel.
Novelty and venue fit remain open; `publication_ready` remains false.

**The bounded panel is closed. Do not repeat or expand it to seek a more
favorable result.** Finish the manuscript and supplement using every source
and both the positive local result and averaging-null result. No new training,
checkpoint replacement, Supabase upload or signal actuation is justified.
