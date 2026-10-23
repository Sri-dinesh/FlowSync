# SUMO action-choice diagnosis — saved trace audit

Scope: project diagnosis only. This is a post-hoc analysis of the already
inspected six-state SUMO panel, not a frozen prediction test, new simulation,
learning experiment or manuscript. The original runner, protocol, checkpoints
and results remain unchanged.

Input: `results/sumo_future_panel/full_20261023`.
Output: `results/sumo_action_mechanism/audit_20261023_v2`.
Tools: `research/audits/audit_sumo_action_mechanism.py` and shared saved-trace
measurements in `research/analysis/sumo_trace_metrics.py`.

## What the controller actually used

At every recorded gate, the currently green approaches have zero halted
vehicles. The opposing phase has stopped vehicles, so the halted-count
continuation requests a switch as soon as the eight-second minimum green
expires. All six inspected gates have exactly eight seconds of green age.
This is a property of the selected panel, not a representative sample of all
decision states.

The inputs below come from the last source sample BEFORE the branch action.
Future arrivals, demand-family labels, encoded vehicle IDs and outcomes are
not used to reconstruct proposals. SUMO defines halting as speed <0.1 m/s;
the saved kinematics have six-decimal precision. See the
[official edge API](https://sumo.dlr.de/docs/TraCI/Edge_Value_Retrieval.html).

| Source | Current phase | Halted: current / opposing | All incoming: current / opposing | Halted proposal | Total-count / pressure shadow |
| --- | --- | --- | --- | --- | --- |
| 109001 | NS | 0 / 6 | 8 / 17 | Switch | Switch / Switch |
| 109002 | NS | 0 / 4 | 7 / 8 | Switch | Switch / Switch |
| 109101 | EW | 0 / 3 | 3 / 19 | Switch | Switch / Switch |
| 109102 | NS | 0 / 3 | 15 / 7 | Switch | Hold / Hold |
| 109201 | NS | 0 / 9 | 1 / 20 | Switch | Switch / Switch |
| 109202 | NS | 0 / 6 | 7 / 20 | Switch | Switch / Switch |

At source 109102, all fifteen incoming NS vehicles are moving. The opposing
EW phase has seven incoming vehicles, three halted. The acting continuation
therefore does not account for the larger moving NS stream in its queue
comparison. The two-phase pressure shadow has raw count-differential scores
**7 for NS and 5 for EW**, so it preserves NS green. It sums positive
incoming-minus-destination-outgoing counts under equal capacities. An
independent call to the existing repository Max-Pressure controller with the
same clean counts reproduces the pressure proposal at every one of the six
states.

Both total-count and pressure shadows match the frozen single/mean-eight
choices at all six states, including their only change at 109102. This is
agreement on consumed development states. The shadows have NOT been executed
as full continuation policies; no full-run pressure gain is established.
The SUMO edge-count semantics also differ from the custom simulator's
historical discharged-inclusive movement getter.

The tool additionally records near-stop-line counts and a distance/speed
arrival proxy. These are exploratory clean-state features, not calibrated
predictions or validated camera measurements. Entry backlog, route/cohort
attribution and future outcomes are explicitly evaluation-only.

## Where the 47.725 vehicle-seconds come from

At 109102, the alternative holds NS for one extra two-second decision interval
and then resumes the same halted-count continuation. Over the eight check
futures, independent stopped-vehicle counting decomposes the mean gain:

| Attribution | Mean delay saved (vehicle-seconds) |
| --- | ---: |
| Vehicles originating NS | +60.2875 |
| Vehicles originating EW | −12.5625 |
| Total | +47.7250 |
| Vehicles already active/pending at the gate | +38.6000 |
| Vehicles requested after the gate | +9.1250 |

The directional and cohort partitions each sum to the same total; they are
different decompositions and must not be added together. All mean saving at
this state is recorded on incoming lanes; the direct mean entry-backlog
contribution is zero. These are descriptive waiting attributions, not causal
mediation estimates.

## Timing and finite-horizon effects

For all eight check futures at 109102, the lamp sequence is identical within
each action. The baseline starts yellow immediately, gives EW green at +4 s
and returns NS green at +16 s. The hold branch starts yellow at +2 s, gives EW
green at +6 s and returns NS green at +18 s. Later phase timing remains shifted.
Both actions have four yellow onsets inside the branch. No clearance rule is
bypassed: complete transitions still use three seconds yellow and one all-red.

Within the forty-second window, baseline has 24 s green, 12 s yellow and 4 s
all-red. Holding has 26 s green, 11 s yellow and 3 s all-red because the window
ends at a different point in the clearance sequence. This endpoint contribution
cannot be interpreted as a steady-state reduction in physical clearance cost.

| Existing prefix endpoint | Mean accumulated delay saved (vehicle-seconds) |
| --- | ---: |
| +2 s | 0.0000 |
| +4 s | +4.0000 |
| +6 s | −1.1000 |
| +12 s | +17.4000 |
| +20 s | +26.2000 |
| +30 s | +24.8375 |
| +40 s | +47.7250 |

The last ten seconds contribute 22.8875 vehicle-seconds, but positive saving
is already present at +20 s. This neither isolates a sole clearance mechanism
nor proves a longer-horizon benefit. These are prefixes of saved trajectories,
not newly selected primary endpoints or additional independent samples.

## Why this does not justify holding everywhere

| Source | Alternative hold delay saved (vehicle-seconds) | Mean completed-trip gain | Mean endpoint max-wait saving (s) | Harmful / qualified check cases |
| --- | ---: | ---: | ---: | --- |
| 109001 | +14.9625 | −0.750 | −2.0000 | 8 / 0 |
| 109002 | +2.4125 | −0.625 | +0.1625 | 4 / 2 |
| 109101 | −6.3000 | −0.250 | 0.0000 | 7 / 0 |
| 109102 | +47.7250 | 0.000 | +1.4000 | 0 / 8 |
| 109201 | −29.2125 | 0.000 | −2.0125 | 7 / 1 |
| 109202 | +4.7250 | +0.375 | −2.0000 | 8 / 0 |

All sources are retained, including delay-favorable holds that fail joint
throughput/wait constraints. A generic green extension is not established as
an improvement. The useful observation is narrower: a stopped-only decision
can turn away from moving traffic, and existing observable count/pressure
information distinguishes the local successful action in this panel.

## Implementation and checks

The auditor verifies the full input panel first, reconstructs all six original
proposals, and partitions all 204 branches / 102 future pairs by direction,
location, pre-gate/future cohort, time window and signal timing. Every waiting
partition conserves the independently reconstructed original delay. Outputs
include source inputs, pair/source CSVs, full signal runs, diagnostic plots,
analysis-source archive and input/output hashes. It performs zero traffic
rollouts, fitting steps, model promotions or website changes.

Twenty-seven targeted tests pass across mechanism, signal, panel and evidence
helpers in the fresh Python 3.11 environment; one existing dependency warning
remains. This is not the full application/frontend suite. Tests cover missing
ticks, fabricated wait increments, duplicate/unknown vehicles, feature leakage,
shadow pressure consistency, timing and conservation.

Run the saved-data diagnosis with a NEW output directory if needed:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python \
  -m research.audits.audit_sumo_action_mechanism \
  results/sumo_future_panel/full_20261023 \
  --output /tmp/flowsync-sumo-action-diagnosis
```

## Next project task

Add executed Fixed and Max-Pressure SUMO baselines with matched sensing,
arrival streams and physical rules. Keep these consumed six states as
development diagnostics, not fresh confirmation. Establish the complete
classical baseline behavior before attributing any correction benefit to
learning or fitting a new rule from this one favorable state. The current
audit establishes no new D3QN optimizer defect or need for a long training run.
