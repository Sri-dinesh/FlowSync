# Broader-data residual calibration — fixed before opening role outcomes

Input: the completed `broader_20261020T134122Z` dataset. This experiment fits
research-only action-outcome regressors, not new DQN checkpoint weights.
No validation/final-test scenarios, simulator runs, baseline changes, website
promotion or threshold search are authorized by this protocol.

1. Verify collection completion, role-file hashes, archived sources, parent
   checkpoints, exact role/parent/scenario/fault cells and branch coverage.
2. Separately for each parent, fit the same eight observable difference features
   and three gain targets as the previous pilot. Keep ridge penalty 10, target
   scales [40,1,40], RMS feature normalization with floor .05 and no intercept.
   Fit only traffic seeds 95001–95006. Give each whole traffic seed equal total
   weight across all its scenarios/faults/actions; normalize row weights to
   mean one. No feature or hyperparameter selection.
3. Freeze point-fit files before reading calibration outcomes. For each of the
   ten calibration traffic seeds, take the maximum positive normalized
   overprediction `(predicted_gain - actual_gain) / target_scale` over **all**
   its scenarios, faults, alternatives and three target components. The margin
   is the ceil(0.9*(n+1))-th sorted group score, clamped at zero. With n=10 this
   is the largest calibration group score. Insufficient groups must fail, not
   silently lower the rank. Lower gains are point gains minus margin *
   [40,1,40]. This intentionally conservative joint rule replaces bootstrap
   coefficient spread; the nominal reference is not a camera-safety guarantee.
4. Save/hash calibrated files before reading the two excluded probe traffic
   seeds 95201/95202. Evaluate every alternative and the actual choices of the
   point-only ablation and calibrated primary. Keep original override criteria:
   delay gain >1 vehicle-second, throughput gain >=0, endpoint wait gain >=-1
   second; choose largest predicted delay with lower action index on ties.
5. Report per-parent and pooled prediction MAE, per-component and joint bound
   coverage, full traffic-seed group coverage, abstention, actual first executed
   action changes, realized branch harm and qualified benefit counts.

The engineering continuation gate requires primary executed correction activity
for every parent, at least one qualified benefit per parent, no selected
correction with delay loss >1, any throughput loss, or endpoint wait loss >1,
and every parent's two probe groups fully covered by the joint bound.
This is a small training-probe screen, not statistical evidence of superiority.
If it fails, stop without full-rollout validation; do not substitute the
point-only ablation or loosen the margins to manufacture a passing result.

This rule may abstain completely. That would establish insufficient evidence
for useful confident corrections under this model and rule, not prove that all
possible calibrated models must fail. Parent-policy sampled branch states are
not the distribution of a future corrected policy; branch benefits cannot be
summed into real full-episode improvements. A passing screen would still need
a new frozen full-rollout validation protocol against unchanged strong baselines.
