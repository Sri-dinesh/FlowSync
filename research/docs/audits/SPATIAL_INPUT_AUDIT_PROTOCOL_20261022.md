# Bounded spatial-input/action diagnosis

Freeze this protocol and source archive before collecting outcomes. Input batch:
`results/research_training/spatial_v9_k2bg79oc`; independently reproduce its
saved comparison first. Its failed continuation criteria stay unchanged.

No optimizer, checkpoint edits, threshold fitting, validation simulation or
final-test access. Reading the existing comparison checks provenance only.
All policy replicates 101/202/303 remain included. Use recorded randomized
TRAINING episodes 1, 46, 90, selected by index before running this diagnosis.
Replay their executed demand/fault configurations under final control and
spatial policies, deterministically with the same shield/physical FSM and
spatial sensor boundary: 18 source rollouts of 1,200 ticks. These are training
scenario replays, not exact original epsilon-exploring online trajectories.

At every policy gate, evaluate both arms' initial/30/60/90 networks on the SAME
delivered state using each checkpoint's declared encoding. For spatial weights
also zero ONLY the twelve extra inputs, keeping all other features/masks fixed.
Record finite Q values, valid-action margins, natural-minus-zero Q differences,
proposal differences and shield-filtered execution differences. The zero-input
probe is an input ablation, not evidence about a natural unseen state. Record
mask availability and sensor age. No probe may advance the acting controller,
sensor or RNG. Check the acting proposal/Q against the independent score.

Short branches: for each of the 18 sources select the first gate at/after tick
200 and the first gate at/after tick 600, with >=2 valid actions and >=200 ticks
remaining. At most 36 gates, four proposals each (policy, same policy with zero
spatial inputs, historical Max-Pressure, upstream-only Max-Pressure). Deduplicate
identical proposals. Fork the complete simulator/sensor/fault/hold/shield state;
change one held macro-action and retain its next decision time. All branches
resume the SAME natural acting RL policy afterward, with shield and physical
FSM intact. This is a local teacher-proposal test, not full-run teacher control.
Score 200 ticks (20 s) on identical future arrivals; report incremental stopped
delay in vehicle-seconds, throughput, endpoint accumulated wait, switches and
signal samples. Do not interpret these correlated, single-future branches as
calibrated action labels or generalization evidence. Do not select only gates
with disagreements or favorable outcomes. Missing eligible windows are explicit.

Demo diagnosis: replay recorded demonstrations 1, 12, 24 for each parent,
historical Max-Pressure at the same macro cadence/shield (nine source rollouts).
Require exact logged delay/reward/shield replay within floating tolerance.
Probe the same frozen network curve on these teacher states; measure proposal
agreement and hinge margin violations, not a causal demonstration ablation.

Inspect every saved checkpoint's finite weights, initial zero columns and
column/whole-network changes. Summarize all 90 per-episode telemetry snapshots
in each arm, separately first/last 15: raw/weighted TD loss, demo margin loss,
demo sampled fraction, importance weights, pre-clipping gradient norm and
Q/target values. Each saved snapshot describes the LAST update of four, not
all 360 minibatches. Snapshot losses cannot attribute causality to imitation.

Bound: 27 full sources and <=144 short branches, one CPU Torch thread, 180 s
cooperative wall cap (checks between ticks/branches; one operation may overrun).
Partial outputs are preserved and explicitly incomplete; no extrapolation.
Source hashes, checkpoint/log hashes, frozen cases and output hashes accompany
raw source/gate/branch records. Require full signal-audit coverage and paired
arrival hashes. Tests compare probed versus unprobed source trajectories,
natural/zero score behavior, hold scheduling, teacher replay and rejected
non-training inputs.

Interpretation: distinguish inactive spatial features, small Q changes without
action changes, shield suppression, and harmful local choices. These are
diagnostic possibilities, not presupposed explanations. Only a reproduced
mechanics defect warrants a correction. Otherwise write one next learning
hypothesis with limitations; no further training command or automatic promotion
is authorized by a diagnostic result. No superiority claim follows.
