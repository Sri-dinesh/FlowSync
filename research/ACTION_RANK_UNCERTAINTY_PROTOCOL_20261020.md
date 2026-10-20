# Action-ranking uncertainty audit — fixed before inspecting residuals

Read frozen action-ranking models and only excluded **training** traffic seed
94002 from the completed pilot. Do not open its validation results or the final
test set, refit models, choose new thresholds, or promote a controller.

Score every recorded non-parent action, including harmful/tied alternatives.
Report actual minus predicted gain, absolute error, bootstrap standard deviation,
and the existing componentwise bootstrap 10th-percentile lower bound for delay
saved, vehicles gained, and endpoint maximum-wait saved.

Report empirical lower-bound coverage and simultaneous coverage descriptively.
These bootstrap percentiles describe coefficient variation, not calibrated
predictive intervals; 90% is only a reference, not a guaranteed nominal coverage.
Report Pearson association of spread and absolute error (null for constant
vectors), not a significance test. Report both pooled action-weighted metrics
and parent/scenario/traffic-seed cluster summaries, grouping paired faults
together. Shared traffic across parents means even these clusters are not
independent traffic-seed replicates. There is only one excluded traffic seed.

Separately report frozen mean/uncertain chosen-action qualification using the
original delay >1, throughput >=0, endpoint wait >=-1 requirements. Count
abstentions and branch-point coverage of all decision gates; do not infer the
outcomes of unlabelled gates or sum counterfactual gains into full-run savings.

Require complete source cells, matching parent/model hashes, finite features
and outcomes, all valid actions exactly once, paired arrivals and complete
signal audits. Preserve raw predictions, source/model/input hashes and source
snapshot. Audit failures must fail closed. Findings guide a later prespecified
training-data/calibration experiment, not a retrospective success claim.
