# From Perception to Control Benefit: An Empirical Audit of Learned Traffic Signals

Working manuscript, 2026-10-23. Writing deadline: 2026-10-31. The user accepts
an empirical evaluation paper. This draft consolidates the earlier audited
evidence and completed independent SUMO study. Novelty and venue fit remain open.
Authors, venue, page limit and citation style remain to be supplied. The user
has completed the independent SUMO panel; its saved raw evidence is verified.
This manuscript update performs no additional traffic trajectory reruns.
The earlier manuscript and addendum remain preserved as dated records.

## Abstract

Uncertainty estimation and richer observations are often intended to improve
learned traffic signal control, but numerical prediction changes need not
produce useful control decisions. We investigate this distinction using an
audited single-intersection simulation workflow with explicit checkpoint
provenance, delivered synthetic sensing, matched supervision and paired traffic
arrivals. A frozen 2,800-run evaluation includes three trained policy replicates
and twenty traffic seeds. Shielded D3QN achieves 12.004 seconds mean stopped
waiting per arrived vehicle, compared with 11.953 seconds for equally shielded
Max-Pressure; superiority is not established. Uncertainty-triggered fallback
adds no established mean-delay benefit. Separate development experiments
examine action sensitivity and counterfactual label stability. Added upstream
inputs change Q values but change none of the final policy's proposals at 320
inspected states when removed at inference. In another panel, delay gain changes
sign across future arrivals for 75 of 125 alternatives. Averaged hindsight
labels improve their development screen, but the observed-input predictor
makes no excluded-probe corrections. An independent SUMO panel evaluates 204
branches at six fixed states; four exhibit both delay-gain signs across eight
check futures. Single-future and mean-eight selectors choose the same one-state
correction, supplying no added averaging benefit. These results distinguish
numerical prediction changes, future-stable action benefit and learned control
improvement. External validity remains limited by small state panels, simplified
demand/sensing and the absence of learned-policy transfer or field evaluation.

## 1. Introduction

Traffic signal controllers must choose actions whose effects unfold through
minimum-green periods, clearance intervals and future arrivals. For a learned
controller using imperfect measurements, several intermediate improvements
may appear promising: a sensor-error estimator can detect corruption, a richer
representation can change action values, or a simulator branch can identify an
alternative that reduces waiting. Each intermediate result requires a separate
test before it can support a claim of improved traffic control.

We study these stages in FlowSync, an interactive traffic-simulation project
with a separately audited headless research workflow. The executed research
environment is a custom single intersection with synthetic sensor faults.
Camera interfaces and city visualizations exist elsewhere in the application,
but they do not validate this environment or its results. Our original goal
was a learned controller that reliably outperformed strong classical control.
The recorded experiments do not achieve that goal.

The empirical question is therefore narrower: where does the expected chain
from observed information to useful action fail in the evaluated system? We
ask three research questions:

1. **Matched control benefit:** Does D3QN improve stopped waiting over
   Max-Pressure under matched sensing and supervision, and does uncertainty
   fallback add benefit to the same shielded policy?
2. **Decision sensitivity:** Do added upstream-demand features change policy
   choices, as distinct from changing Q magnitudes?
3. **Future stability and learnability:** Do favorable branch-action labels
   persist under separate arrival futures, and do averaged labels produce
   useful corrections from observed inputs on excluded sources?

This study contributes an explicitly scoped record of matched component
comparisons, a same-state input-removal diagnostic, separate-future action-label
experiments and a bounded independent SUMO replication. These are empirical
analyses of the evaluated
system, not a novel control algorithm or a general impossibility result.
Their scientific distinctiveness requires comparison with the related work
below; the number of runs or amount of software alone does not establish it.

## 2. Related work and intended distinction

[RESCO](https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/hash/f0935e4cd5920aa6c7c996a5ee53a70f-Abstract-round1.html)
provides traffic-signal RL benchmarks and reports sensitivity to sensing
assumptions and intersection layouts.
[LibSignal](https://arxiv.org/abs/2211.10649) provides unified model interfaces,
metrics and comparisons across SUMO and CityFlow. Consequently, neither
benchmarking RL against classical control nor identifying sensitivity to an
evaluation setting is sufficient as a novelty claim here.

[Advanced-MP and Advanced-XLight](https://proceedings.mlr.press/v162/zhang22ah.html)
already use running/queuing vehicle information and pressure-based state
representations. Adding an upstream-demand input is not itself a new research
principle. FlowSync's historical Max-Pressure and upstream-only variant are
not reproductions of those methods.

[CFLight](https://arxiv.org/abs/2512.09368) studies counterfactual learning for
traffic-signal safety. [UCATSC](https://arxiv.org/abs/2602.07784) describes an
uncertainty-aware, constrained decision layer using belief-space rollouts
under vision-based partial observability. Their existence precludes a first
counterfactual or first uncertainty-aware constrained-control claim. Inspected
methods distinguish CFLight's learned counterfactual dynamics/objectives from
UCATSC's belief-space action filtering and sampled dilemma-zone risk. Our
question concerns observed-input action-label stability across arrival streams
and the translation of numerical changes into decisions. The dated
[primary-source comparison](EMPIRICAL_RELATED_WORK_20261023.md) records the
sections inspected and remaining gaps; no competing baseline was reproduced.

Before submission, expand the method-level comparison, including the close
uncertainty-gated DQN lead recorded in the
[novelty triage](RESEARCH_NOVELTY_TRIAGE_20261022.md). Its full method remains
unverified. Prior works' performance claims are not adopted as FlowSync
measurements, and this draft makes no systematic-review claim.

## 3. System and evaluation method

### 3.1 Execution and sensing boundary

The headless runtime applies declared demand and synthetic sensing faults,
constructs a delivered observation/context, requests a controller proposal,
and applies optional fallback and additional shielding before common physical
signal transition rules. An independent audit samples executed lamps each
simulation tick. Simulator truth scores outcomes and training rewards; it
does not replace delivered noisy inputs in the audited controller boundary.

Bare D3QN retains physical minimum-green and clearance rules. The additional
shield is a separate component, including service-protection interventions.
Phase-service timers indicate elapsed service age, not individual vehicle
waiting time. Removing the additional shield does not remove physical signal
constraints. Incidents are represented through discharge-headway changes,
rather than validated vehicle-level incident behavior.

The learned controller uses a dueling network, masked Double-DQN targets,
prioritized replay and demonstration assistance. Later research fixes charge
a switch once at GREEN-to-YELLOW and retain only completed decision-to-decision
macro-transitions. Checkpoints carry observation/reward version metadata.
The matched evaluation uses v7 features: the base 28-input encoding plus four
delivered outgoing counts and four phase-service timers. The website trainer
is a separate integration path; equivalence is not assumed.

### 3.2 Distinct experimental panels

The main frozen evaluation has 2,800 runs: twenty paired traffic seeds,
three selected policy-training replicates, seven clean scenario templates
and three additional sensing conditions. Classical methods run once per
condition/traffic seed; they are not treated as three independently trained
models. Scenario families had previously been inspected. All selected parent
replicates are retained, including a warmup-selected checkpoint.

The input-use, action-label and teacher experiments are later development
panels with their own protocols and role seeds. They are not added to the
frozen sample or described as independent final confirmation. Each analysis
retains its original controls and failed continuation conditions.

A separate SUMO panel uses six fixed source states from three declared demand
families, with one single-choice selection future, eight mean-choice selection
futures and eight disjoint check futures per state. Both phase actions are
branched for forty seconds, giving 204 branches. Source states and future keys
are fixed before collection; all selector choices are fixed before check
outcomes. This replicates one qualitative diagnostic, not the trained FlowSync
policy or the original frozen controller comparison.

### 3.3 Endpoints and inference

The main delay endpoint is accumulated stopped waiting per arrived vehicle
over a finite horizon, including vehicles present/backlogged at the endpoint.
It is not completed-trip travel time. Aggregate p95 is an average of within-run
percentiles, not a pooled vehicle percentile. Branch-action delay differences
are measured in vehicle-seconds; they must not be interpreted as full-run
seconds saved per vehicle.

Main matched contrasts use 5,000 crossed-bootstrap draws over training
replicates and paired traffic seeds with condition cells fixed. Intervals are
descriptive and unadjusted, with only three policy-training replicates. Gates,
alternatives, futures and lamp samples are correlated; they are not counted
as independent trained policies or intersections. Later branch panels receive
descriptive analysis rather than fabricated independent-event significance.

## 4. Matched controller and uncertainty results

| Controller | Mean delay (s) | Mean within-run p95 (s) |
| --- | ---: | ---: |
| Fixed | 15.496 | 40.539 |
| Actuated | 16.463 | 63.448 |
| Greedy | 11.725 | 41.891 |
| Max-Pressure | 11.514 | 39.418 |
| Max-Pressure + shield | 11.953 | 40.029 |
| D3QN | 11.528 | 40.285 |
| D3QN + shield | 12.004 | 40.241 |
| Full FlowSync-UQ | 12.019 | 40.112 |

The primary matched-shield saved-delay estimate is −0.050 seconds, with
95% interval [−0.219, 0.125]. The UQ increment relative to shielded D3QN is
−0.015 seconds, interval [−0.104, 0.071]. Positive savings would favor the
candidate. Neither superiority nor equivalence is established.

Fallback activates 306 times and occupies 260,298 ticks across 600 UQ runs.
Its lack of demonstrated benefit is therefore not explained by inactivity.
Calibration predicts synthetic count error, not the expected benefit of a
backup action. In this panel, anti-starvation accounts for 892 of 896 D3QN
shield interventions. Mean-delay costs can coexist with service/tail benefits;
the comparison does not imply that fairness protections should be removed.

All 4,340,000 audited lamp samples have zero measured conflict/clearance
violations. This is finite simulated signal-state coverage, not collision or
deployment safety. The historical checkpoint-free 2,040-run experiment is
excluded because its learned policies were randomly initialized.

## 5. Richer observations and action sensitivity

Historical movement counts include some vehicles already beyond the stop
line. The spatial treatment adds twelve delivered counts for vehicles at or
before it, with the same documented backlog assumption. Treatment/control
both have 48 inputs, shared fault delivery and zero-expanded v7 parent weights;
only the control zeros the new inputs. Masks/shield retain historical delivered
demand, isolating additional network information rather than replacing all
demand semantics. Ghost/jitter spatial assignment is a documented assumption,
not measured camera calibration.

All six runs finish ninety online episodes and 360 optimizer updates. At the
fixed endpoint, spatial mean delay is 10.840583 seconds, control 10.783722 and
unchanged parents 10.841389. Spatial fails the predefined improvement, seed,
tail/throughput continuation screen. Used development seeds/templates are not
fresh confirmation, and a selected earlier checkpoint cannot replace this result.

The training-only input audit probes natural versus zero spatial features
at the same delivered state with the same checkpoint/mask. Spatial weights
become nonzero and Q values change. Nevertheless, none of 320 inspected
episode-90 proposals changes: 108 spatial-policy states, 110 control-policy
states and 102 teacher states.

On spatial-policy states, mean maximum absolute Q change is 0.863911, mean
range of Q changes across valid actions is 0.099808, and mean action margin
is 2.170554. Most numerical movement is shared across action values in this
panel. These means are not per-state bounds. No changed final proposal exists
for the shield to suppress. Input removal at inference also does not undo
possible effects on gradients/targets during training; the result does not
prove universal irrelevance of spatial information.

## 6. Future-dependent labels and excluded-source learning

### 6.1 Action labels under additional arrivals

A branch diagnostic examines eighteen sources, 54 gates and 125 alternatives
under eight additional futures each. Delay gain changes sign for 75/125
alternatives, using the prespecified +1/−1 vehicle-second deadband.
Original choices are harmful in 108/168 future cases, and only
3/21 original choices qualify in at least six futures. This is evidence of
future sensitivity on the tested panel, not an estimate for all traffic states.

A separate experiment freezes choices using eight futures before evaluating
eight different futures. Single-future choices change 21/54 gates, save
−1.975 vehicle-seconds on average and have 102/168 harmful changed cases
(60.71%). Mean-eight choices change 9/54 gates, save +1.071 vehicle-seconds
and have 28/72 harmful cases (38.89%). Means include unchanged gates with
equal source weighting. The label-averaging development screen passes, but
choices still use simulator outcomes and are not a deployable controller.
The 108/168 and 102/168 harmful-case counts refer to different future sets;
the latter uses separate IDs 8–15 and is not a corrected count for the former.

### 6.2 Learning from averaged labels

The next pilot fits six observed-input ridge models using 72 fitting sources,
then freezes them before 36 excluded-probe sources. Fitting seeds 96301–96304
and probe seeds 96401–96402 are separated. The mean-eight model makes no
corrections across 72 probe gates and 576 future cases. The single-future model
changes one gate with five good/three harmful future cases and aggregate
throughput loss. The learned continuation screen fails.

Thus a favorable simulator-hindsight screen does not establish useful
observed-input correction in this experiment. The result does not show that
all predictors must fail. An exact repeat matching thirteen output hashes
demonstrates deterministic reproduction, not additional independent evidence.

### 6.3 Teacher substitution and horizon sensitivity

A subsequent prerequisite selects seven eligible historical/upstream teacher
disagreement gates from nine replayed training configurations. The historical
teacher and policy hold at each gate; the upstream teacher switches. Their
two hold comparisons are duplicate actions, not independent baselines.

Across a separate check set of eight futures per gate, the upstream action
adds 5.339286 vehicle-seconds of twenty-second branch delay and loses 0.946429
vehicles per branch on average, while improving endpoint maximum accumulated
wait by 3.016071 seconds. Only two gates meet the predefined per-gate robustness
condition. The teacher-training screen fails.

An exploratory extension preserves every original twenty-second prefix inside
sixty-second branches. The first future set now saves +4.430357 vehicle-seconds,
but the separate set saves −5.137500; throughput falls in both. Both sets were
already inspected at twenty seconds before the extension. Longer-horizon
results cannot replace the failed prerequisite or supply fresh confirmation.

## 7. Independent SUMO future-arrival replication

### 7.1 Design and reconstruction

The frozen [SUMO protocol](../protocols/SUMO_FUTURE_PANEL_20261023.md) uses
SUMO/traci/sumolib 1.24.0 on one generated four-arm intersection with 200 m
single-lane incoming/outgoing roads, straight movements and protected NS/EW
phases. Minimum green is eight seconds, yellow three seconds and all-red one
second. Driving is deterministic; sensing is clean. Continuation uses incoming
halted-count control with two-second decisions and holds on ties. This
continuation is not the original learned controller or Advanced-MP.

The balanced family uses 0.20 vehicles/s per approach. Dominant-axis families
use 0.30 on the dominant approaches and 0.10 on the other approaches. Each
family has two fixed source seeds. One gate per source is the first eligible
decision at/after sixty seconds with at least eight seconds of green, without
outcome-based selection. Future arrivals are independent Bernoulli draws at
the declared family rates and paired across actions. Entry-blocked vehicles
remain in an external FIFO included in waiting measurements.

Snapshot reload failed to reproduce continuation in mechanics checks despite
matching visible state. Every scientific branch therefore restarts and fully
replays its source history; the complete prefix must match at six-decimal trace
precision before arrivals/actions diverge. These checks address reconstruction
in this configuration, not a universal claim about snapshot validity.

Single and mean-eight hindsight selectors change the pre-outcome baseline
proposal only for >1 vehicle-second mean delay saving, nonnegative completed-trip
gain and endpoint maximum-wait saving >=−1 second on their selection futures.
Otherwise they retain baseline. Outcomes use stopped-wait integrals, completed
trips at the network boundary and endpoint accumulated waiting. These metrics
are not pooled with the custom simulator's per-arrived-vehicle delay or
intersection-passed counts.

### 7.2 Results and concentration

All 204 branches complete within the declared budget. Across 48 check cases,
the alternative saves >1 vehicle-second in 26, loses >1 in nineteen, and falls
within the ±1 deadband in three. Four of six gates show both signs:

| Source | Demand family | Positive / negative / deadband futures | Selected delay saved (vehicle-seconds) |
| --- | --- | --- | ---: |
| 109001 | Balanced | 8 / 0 / 0 | 0.000 |
| 109002 | Balanced | 5 / 1 / 2 | 0.000 |
| 109101 | NS dominant | 1 / 6 / 1 | 0.000 |
| 109102 | NS dominant | 8 / 0 / 0 | 47.725 |
| 109201 | EW dominant | 1 / 7 / 0 | 0.000 |
| 109202 | EW dominant | 3 / 5 / 0 | 0.000 |

Single and mean-eight selectors choose the same action at every gate and
change baseline only at source 109102. All eight check cases at that gate
qualify, with mean delay saving 47.725 vehicle-seconds, no completed-trip loss
and 1.4 seconds endpoint maximum-wait saving. Averaging equally over six
sources gives 7.954167 vehicle-seconds saved and 0.233333 seconds endpoint-wait
saving, with zero completed-trip gain and zero harmful changed cases.

All selected savings come from one source; the other five retain baseline.
There is no measured added averaging benefit. Sign counts concern the
alternative at every gate, not the selected rule's harmful-case count.
Joint constraints can reject a consistently delay-favorable alternative:
source 109001 has eight positive-delay futures but loses throughput and
endpoint-wait performance on average. No thresholds are relaxed afterward.

This panel supports future-dependent action labels under a second simulator
and retains a favorable local example. Its selectors still use simulator
hindsight, and it establishes no learned-controller transfer, full-run
superiority, significance or population prevalence. Six gates and their
correlated futures do not constitute 48 independent intersections. Raw-trace
verification covers 4,040 source ticks and 81,600 branch ticks with zero
measured signal timing/conflict violations; overlapping histories are not
independent safety samples.

## 8. Discussion

The results separate four empirical questions: does the sensor-error estimate
describe measurement corruption; does added information affect relative action
values; is an alternative beneficial under different plausible futures; and
does an observed-input policy improve closed-loop traffic? The evaluated system
does not establish that success at one stage reliably answers the next.

Three practical checks follow for this workflow. Match controller information,
physical rules and additional supervision before attributing a gain to RL.
Inspect proposals and action margins alongside Q magnitudes or prediction
losses. Freeze branch-derived choices before testing separate futures, then
evaluate a learned rule on excluded sources and ultimately full trajectories.
These checks are recommendations derived from the case study, not a theorem
or a claim that earlier research omitted them.

Other recorded development recipes—including temporal features, reduced update
pressure and benefit gating—also fail their fixed screens. Preserve them in
the supplement/experiment index rather than choosing only favorable cases.
They are not pooled into the main evaluation, and this manuscript does not
claim a global causal explanation for online-learning degradation.

The independent SUMO result reproduces the qualitative future sensitivity but
does not reproduce an added averaging benefit. This boundary is material:
stable local action gains can coexist with unstable alternatives elsewhere,
and a positive aggregate can be concentrated at one state. These observations
cannot establish that averaging universally helps, that all action labels
are unreliable or that the learned controller now improves traffic.

## 9. Limitations

The experiments use one custom simulator, synthetic sensing faults, three
training replicates and previously inspected scenario families. Simplified
motion, backlog visibility, permissive turns and incident headway surrogates
limit external validity. The branch panels contain correlated states/futures
and unequal replicate coverage. Calibration across policies and model-class
choices also limit interpretation. All future seeds inspected during analysis
are consumed for subsequent model decisions.

No recorded-camera validation, calibrated real traffic, faithful Advanced-MP
baseline, learned-policy transfer or physical signal operation is established.
The independent SUMO panel is limited to six gates on one generated topology,
deterministic driving, clean sensing and forty-second branches with simple
halted-count continuation. It does not validate the custom simulator's dynamics
or establish external validity for its complete controller rankings. Snapshot
reload failures are preserved and not used for scientific branching.
Lamp audits do not validate pedestrians/collisions. Library tests
and application builds are engineering checks, not scientific confirmation.
Novelty beyond the cited evaluation/counterfactual literature remains to be
established. A single-project negative result alone is not a universal finding.

## 10. Conclusion

In the recorded FlowSync panels, matched evaluation does not establish a
learned-controller advantage or useful added uncertainty fallback. Richer
upstream inputs change Q values without changing final proposals on inspected
states, and apparently useful branch labels depend on future arrivals and
do not yield active useful corrections in the excluded-source model pilot.
The evidence supports reporting intermediate prediction changes separately
from action changes, future stability and full-run control benefit. An
independent SUMO panel also exhibits future-dependent action gains at four of
six states, while both frozen selectors choose the same single-state benefit.
These limited cross-simulator observations do not establish added averaging
benefit or a superior learned controller; broader traffic and learned-policy
validation remain necessary.

## Evidence map for final tables and figures

The [numerical ledger](../../../results/paper_evidence/empirical_audit_20261023_v3/README.md)
reconstructs quantities from nine separate preserved panels, refits the six
models and reproduces stored probe predictions. Its manifest binds this
manuscript revision, inputs, archived-source checks and outputs. It performs
no traffic rollout and is not an independent validation of the simulator,
every prose claim or novelty.

![Same-state spatial sensitivity](../../../results/paper_evidence/empirical_audit_20261023_v3/input_action_sensitivity.png)

**Figure draft:** Mean numerical sensitivity and final proposal changes for
three training-state distributions. Shared Q movement and action-margin
comparisons are descriptive means, not per-state bounds. All final proposal
changes are zero; inference removal does not undo learning-time effects.

![Future labels and excluded-source corrections](../../../results/paper_evidence/empirical_audit_20261023_v3/future_labels_and_probe.png)

**Figure draft:** Arrival-future sign variation, frozen hindsight selection
and excluded-source learned correction. The latter two are distinct panels
with different sources; their means are not a paired method contrast.
Single-model positive mean delay saving does not satisfy its joint
throughput/wait constraints. No significance or full-run gain is inferred.

![Independent SUMO action-future evidence](../../../results/paper_evidence/sumo_future_20261023/sumo_future_stability.png)

**Figure draft:** Left: paired alternative gains under eight check futures at
each of six fixed source gates. Dotted lines mark the ±1 vehicle-second
deadband. Right: the two frozen hindsight selectors choose identical actions;
all selected delay saving comes from source 109102. Neither plot provides
independent-replicate confidence intervals or a learned-policy improvement.

| Manuscript material | Authority / preserved artifact |
| --- | --- |
| Main methods/results/intervals | [Matched-shield protocol](../protocols/MATCHED_SHIELD_PROTOCOL_20261015.md); `results/replicate_evaluation/matched_shield_v5_20261015`; `results/paper_evidence/audited_v5_20261016/` |
| Reward/replay validity | [Learning audit](../audits/LEARNING_UPDATE_AUDIT_20261015.md) |
| Spatial controlled endpoint | [Spatial results](../results/SPATIAL_INPUT_RESULTS_20261021.md); `results/research_training/spatial_v9_k2bg79oc/` |
| Same-state input ablation | [Input-use audit](../audits/SPATIAL_INPUT_AUDIT_RESULTS_20261022.md); `results/spatial_input_audit/pilot_20261022/` |
| Arrival sensitivity | [Arrival panel](../results/ARRIVAL_LABEL_PANEL_RESULTS_20261021.md); `results/arrival_label_stability/panel_20261021T063020Z/` |
| Frozen averaged choices | [Averaged-label results](../results/AVERAGED_LABEL_RESULTS_20261021.md); `results/averaged_action_labels/panel_20261021T091742Z/` |
| Excluded-source model pilot | [Learned-model results](../results/AVERAGED_LABEL_MODEL_RESULTS_20261021.md); `results/averaged_label_model/pilot_20261021T095353Z/` |
| Teacher/horizon diagnostic | [Teacher results](../results/TEACHER_ALIGNMENT_RESULTS_20261022.md); `results/paper_evidence/teacher_diagnostics_20261022/` |
| Independent SUMO panel | [Completed SUMO results](../results/SUMO_FUTURE_PANEL_RESULTS_20261023.md); `results/sumo_future_panel/full_20261023/`; `results/paper_evidence/sumo_future_20261023/` |
| All negative follow-ups | [Research status](../../RESEARCH_STATUS.md) and [results index](../results/README.md) |

Use four main figures: matched-control contrasts; same-state Q/action
sensitivity; custom-simulator future labels and the excluded-source learning
stage; independent SUMO future variation and concentration. Describe the
execution boundary in methods or place its diagram in the supplement.
Put detailed teacher/horizon and failed-recipe
tables in the supplement if the chosen page limit requires it. Plot from raw
provenance-checked measurements; do not draw illustrative values as results.

## Writing execution plan: October 23–31

| Date | Deliverable / stop rule |
| --- | --- |
| Oct 23 | This unified first draft, fixed three-question scope and evidence map. Select a venue/article type with an empirical remit and verify its current rules once specified. |
| Oct 24 | Check claim-to-artifact mapping and full-method novelty overlap; finalize bibliography and strongest limitation statements. Scope reduction is preferable to an unsupported novelty claim. |
| Oct 24–25 | Independent SUMO collection already completed and verified. Finalize the per-source result, both selector outcomes, figure and limitations. Do not repeat it to seek stronger gains. |
| Oct 26 | Freeze the experiment set, retaining the full independent panel separately from original panels. No architecture search, threshold relaxation or new training campaign. |
| Oct 26–28 | Complete figures, methods/related work, supplement, citations, authorship and venue template. Remove draft/editorial notes and every unsupported claim. |
| Oct 29–30 | Review units, sample dependence, intervals, source/checkpoint identities, every numeric claim and wording. Compile the manuscript and check references/figure legibility. |
| Oct 31 | Deliver the complete written manuscript and reproducibility/limitations supplement. Writing completion is not acceptance or validated superiority. |

The independent diagnostic is complete and closed. Its limited qualitative
replication and one-state hindsight benefit are included without changing the
old failed recipes or frozen tables. No learned policy was transferred, new
training started or model promoted. Remaining work is manuscript/supplement,
novelty/venue review and typesetting; existing CONTENT.md changes are separate.
