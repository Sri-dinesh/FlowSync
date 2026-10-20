# Arrival-label diagnostic: mechanics verified, full panel pending

Protocol: [fixed-state future-arrival comparison](ARRIVAL_LABEL_PROTOCOL_20261020.md).
Implementation: `research/audit_arrival_label_stability.py`.
Verified smoke output: `results/arrival_label_stability/smoke_20261021`.

## What is implemented

Replay an existing fitting-data source and its recorded policy gates. At each
gate, preserve the full current simulation state and all existing traffic.
Compare every valid action under eight different future-arrival streams,
pairing the arrivals exactly between actions within each stream. Preserve the
parent's macro-action duration, subsequent policy, shield and physical signal
transitions. Resample only the copied spawner RNG, not its clock/backlog.

An optional research callback in `audit_policy_decisions.audit_run` supports
this diagnostic; its default behavior is unchanged. No production controller,
DQN weights or saved fitting labels have been altered.

## Smoke findings — limited scope

One source completed in 48.70 seconds: parent 101, fitting traffic seed 95001,
`train_ew_asymmetric_01`, clean sensing. It covers three recorded gates,
seven non-parent alternatives and eight future streams per gate.

- Six of seven alternatives have both positive (>1 vehicle-second) and
  negative (<-1 vehicle-second) delay savings across the sampled futures.
- The constrained hindsight-best action differs across futures at all three
  gates.
- One gate has a qualified beneficial alternative under its original saved
  future. That original choice is beneficial in only one new future and
  harmful in seven.
- All eight arrival traces are distinct at each gate. Each trace is exactly
  paired between candidate actions.
- All 37,200 recorded source/branch signal samples have zero measured
  violations. This is not a real-world safety guarantee.

“Qualified” requires delay saving >1 vehicle-second, no throughput loss and
endpoint maximum-wait increase <=1 second. “Harmful” is delay loss >1
vehicle-second, any throughput loss, or endpoint maximum-wait increase >1
second. These are paired 40-second branch labels, not whole-run policy gains.

This shows that future arrivals can change an action label at these sampled
states. It does NOT prove that arrival variability explains all previous
prediction errors or that a different training scheme will improve control.
The same observed state hides exactly the same present truth in this
experiment; uncertainty here is introduced in the future, not by changing
current queues or detections.

## Verification and corrected checker

The first attempt (`smoke_20261020`) stopped at the replay check; it is
preserved and is not counted as completed evidence. The new checker compared
live integer phase-timer keys with their saved JSON string representation.
It now compares both in JSON form, without rounding numeric values or
dropping outcome fields. A regression test ensures even a 1e-12 timer change
still fails.

62 targeted tests passed. The successful smoke exactly reproduces the original source trajectory and
all original action outcomes. Input/checkpoint/archive/output hashes,
future seed derivation, action coverage, paired arrival hashes and report
reproduction have been verified. The saved source archive records the actual
smoke implementation; subsequent changes only add the budget to the manifest
and print the output location.

## Next run: the frozen 18-source panel

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u \
  research/audit_arrival_label_stability.py \
  results/action_rank_dataset/broader_20261020T134122Z \
  --output "results/arrival_label_stability/panel_$(date -u +%Y%m%dT%H%M%SZ)" \
  --max-wall-seconds 1800
```

This evaluates all three parents and all six training scenarios at the
prespecified source traffic seed with clean sensing. Allow roughly 15 minutes
based on the smoke, with a 30-minute cooperative simulation budget; actual
runtime varies by scenario and hardware. It does not train or upload a model.
Expect `full_panel_complete: true` and 18 completed sources. A budget stop
retains completed sources and reports incomplete; do not call it success.

Only after inspecting the complete diagnostic should we decide whether
multi-future averaged action labels justify a separately specified training
experiment. No retuning to calibration/probe or final-test results is allowed.
No superiority, publication-readiness or deployment-readiness claim follows
from this smoke.
