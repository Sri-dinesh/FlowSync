# Executed total-incoming-count ablation — frozen before outcomes

Project code and simulation evaluation only. The completed classical and
future-arrival collections stay closed. No DQN training, manuscript editing,
new-method claim, final testing or model promotion is part of this experiment.

## Question and controlled change

Execute the axis with the larger **total incoming vehicle count**, including
moving vehicles, with current-phase tie handling. Retain the current phase
during clearance or before eight seconds of actual green. The policy receives
the same delivered incoming/outgoing/halted count packet and physical clock
as the classical comparison; it ignores halted/outgoing values by design.

Primary contrast: total counts versus Max-Pressure, isolating removal of
destination outgoing-count subtraction. Secondary contrast: total counts versus
halted control, isolating use of all incoming vehicles instead of halted ones.
Keep the existing Fixed reference and every case/family visible. No duration,
score coefficient, threshold, horizon or best-case selection is fitted.

Use the frozen physical/vehicle step, deterministic SUMO 1.24.0 driving,
two-second decisions, 0.1 s simulation ticks, initial empty intersection and
NS green, eight-second minimum green, three-second yellow and one-second
all-red. Supply the selected proposal at EVERY decision. Controllers receive
only previous completed-step counts and the physical clock, not IDs, family,
seed, future arrivals or external entry backlog. No new shield/noise layer.

## Reused references and precommitted cases

Reuse all verified classical references, without rerunning their trajectories:

- Full: `results/sumo_classical_panel/full_20261023`; report SHA-256
  `7cd78ca440dd49157d5046aebc9256b4e5f35fc20b07a713064f9d61410fd1bc`.
- Mechanics: `results/sumo_classical_panel/smoke_20261023`; report SHA-256
  `38e2e3e1dbe4d6dc4a741239c6801c05198af11ba03690bc761a3722ed2e9fc6`.

The runner/verifier must validate these anchored report/output/source hashes,
raw traces and full coverage before using the references. Copy the existing
network, route file and exact frozen schedules into a new output directory.
Use the same SUMO seed 110000 and command options. Preserve the old recorded
implementations and protocols unchanged; the new callback-based episode/check
adapter must match their observed packet, physical and metric semantics.

Full job: **15 new total-count runs**, one per existing case, **180 seconds /
1,800 ticks** each. Reuse seeds 110001–110005 balanced, 110101–110105 NS dominant,
110201–110205 EW dominant, with their exact original requested schedules and
rates. These are deliberately **consumed development cases**, not fresh test
seeds or independent confirmation. No warmup discard or drain extension.
The job has a **360-second / six-minute cooperative cap**, including reference
verification. Preserve partial traces and report incomplete on errors,
interruption or budget stop; never score only a favorable completed subset.

Smoke: reuse the separate mechanics seed 110901 and its 80-second / 800-tick
schedule. Execute one Max-Pressure anchor and two identical total-count repeats
(**three new runs**, 120-second cap). The anchor's entire semantic trace must
equal the original Max-Pressure repeat-zero trace, not merely its aggregate
metrics. Total-count repeats must match each other. This is mechanics only;
do not use its rankings to tune the policy or interpret it as the full ablation.
The user runs the full job after the smoke and compatibility checks pass.

## Metrics, evidence and interpretation

Preserve the classical endpoints: stopped waiting per requested vehicle,
including stopped active vehicles and all entry backlog; linear-interpolated
within-run p95 and maximum accumulated waiting; completed network exits;
final active/backlogged inventory; endpoint accumulated waiting and switches.
Aggregate cases with equal weight; aggregate p95/max are means of within-run
values. Requested schedules are paired; insertion can vary with the controller.
Report primary and both secondary contrasts per case and family, with counts
and identities of mean/p95/trip regressions. Record the reused reference
coverage separately from new trajectories/signal samples.

Completion is a coverage decision, not a superiority screen. The comparison
is reported regardless of sign and has no automatic training/promotion gate.
There is no threshold relaxation or claim that this simple classical ablation
is a new controller contribution. No significance, population uncertainty,
learned-policy transfer or causal conclusion about individual decisions follows
from the seen-state proposal counts. The executed paired experiment estimates
the component difference only in this declared development setup, including its
fixed initial phase and finite horizon.

Save gzip traces with every delivered decision, exact schedules, configuration,
source/protocol archive, reference anchors, command, run metrics, all paired
summaries, output hashes and failure status. Reject executed conflicts, invalid
clearance, collisions, teleports, SUMO pending departures and inconsistent
inventory. The read-only verifier requires the original reference directory,
reconstructs every new packet/proposal/FSM, entry FIFO and per-vehicle waiting,
checks anchor/repeat equality and all paired reports, and reruns zero traffic.
It must reject partial cells, changed/replaced references, edited raw outcomes,
missing evidence and smoke relabelled as a full ablation.
