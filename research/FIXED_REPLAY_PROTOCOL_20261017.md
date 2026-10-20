# Fixed-training-replay diagnostic (pre-execution)

Purpose: distinguish inability to fit a stationary objective from changing
bootstrap targets and data. This is a mechanics/learning diagnostic, not a new
controller, performance experiment or publication-readiness test.

Input batch: `update_pressure_5qyi9cmv`, all parents 101/202/303. Verify its
comparison, source archive and parent hashes before starting. Preserve inputs.
Record current sources, protocol, parent and input hashes in a fresh output.

For each parent, regenerate transitions from the first six recorded demonstration
cases (Max-Pressure teacher), and recorded online cases 1/16/31/46/61/76 with the
unchanged parent and exploration OFF. Use their recorded scenario, fault and
traffic seed, shield ON, fallback OFF, v7 input and audited research reward.
These are newly regenerated parent trajectories, NOT the original online replay
buffer or trajectories of the later trained model. All scenarios must be train.

Fit on first four demonstration cases and online cases 1/16/31/46. Probe on the
last two demonstration cases and online cases 61/76. Split by whole episode,
never random transitions. Probe data are excluded from optimizer batches; they
are seen-domain training diagnostics, not independent validation or final tests.
The previously problematic online case 61 stays in the probe partition.

Freeze/save dataset and 200 precomputed uniform-with-replacement index batches
of size 128 per parent (local RNG seed 77000 + parent seed). Reuse exactly the
same batches in all arms; uniform weights are 1. Disable priority sampling and
updating for this diagnostic. The sample count may exceed the fit dataset size.
No data collection occurs after fitting starts. Retain demonstration flags and
margin loss weight 0.5 in every arm; Adam 0.0001, same initial parent, fresh
optimizer, same production `train_step` and clipping.

Three arms, 200 optimizer updates each:

1. `fixed_labels`: labels computed ONCE using the initial parent masked
   Double-DQN target. Feed these labels as synthetic supervised rewards with
   bootstrap discount zero and done one to the unchanged production update.
   These terminal flags are an algebraic diagnostic adapter, NOT real traffic
   terminal events or a change to production replay semantics.
2. `moving_selector`: standard Bellman targets, target network held at parent;
   online next-action selection still changes. No target copies.
3. `moving_target`: standard Bellman targets; target copy every 25 updates.

Measure full fixed fit/probe sets at steps 0/25/50/100/200: error against original
labels, live Bellman error, target drift, demonstration margin, joint frozen
objective, and masked action disagreement with parent. For copying steps,
measure AFTER the copy. Minibatch loss is not substituted for these full-set
metrics. Fixed-label joint objective includes the same demonstration margin;
margin constraints can conflict with labels. Demonstration normalization within
minibatches can differ from full-set normalization.

Maximum total execution budget 240 seconds, cooperative checks at simulation
ticks/optimizer steps. Preserve partial output and mark incomplete on timeout.
Save no trained checkpoints; learned diagnostic weights are discarded. Verify
input hashes unchanged afterward. No traffic-efficiency/safety benefit claim,
threshold tuning, website promotion, final-test access or long batch follows
automatically. If stationary fitting succeeds, that rules out gross fitting
failure only on these samples; it does not establish policy quality or isolate
PER as a cause. Moving-target errors need not mean a mathematical bug.
