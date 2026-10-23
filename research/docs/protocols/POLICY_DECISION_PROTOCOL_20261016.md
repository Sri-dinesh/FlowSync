# Fast policy-decision diagnostic

Fixed before collection: all three selected v5 policies, six train templates,
traffic seed 92001, clean and existing mixed faults (36 source rollouts).
No final-test or validation input, policy optimization, or threshold search.

Run shield-only D3QN. At every real policy decision gate record RL and
Max-Pressure proposals, same-shield executions, Q values and observable inputs.
For the first four eligible effective disagreements per run, fork identical
states for 200 ticks (20 seconds). Change one proposed macro-action and its
held-action state, then resume the same frozen RL continuation in both branches.
Keep shield and mandatory physical FSM unchanged. Pair arrivals and perception
RNG states; preserve source rollout state and immutable policy weights.

Compare accumulated waiting vehicle-seconds, endpoint maximum upstream wait,
throughput, switches, and undiscounted training-reward components. These are
short-horizon correlated diagnostic samples, not unbiased policy-value estimates
or independent superiority trials. Q values predict longer discounted returns;
a short-horizon ranking disagreement alone does not prove incorrect TD code.

Use this evidence to identify a targeted learning change, not to promote a
simulator-truth oracle or claim the teacher is always optimal. Frozen final-test
results, existing checkpoints, website defaults and physical timing stay intact.
