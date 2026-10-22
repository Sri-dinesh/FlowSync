# Experimental artifacts

Raw runs, checkpoints, source snapshots, logs and generated evidence are
normally local and ignored. A fresh clone does not contain recorded user
experiments or trained checkpoints. Missing weights must not be silently
replaced by randomly initialized policies.

`final/` and `tables/` contain historical outputs predating the audited
pipeline. Their names do not certify numerical claims. The
[evaluation audit](../research/EVALUATION_AUDIT.md) explains why the original
policy-performance conclusions are invalid.

Use [research status](../research/RESEARCH_STATUS.md) and the
[research index](../research/README.md) for artifact interpretation and locations.
New exports must derive from raw measurements and verify checkpoint,
configuration and source provenance.

Use a new output directory for every experiment. Preserve unfavorable cases,
protocols, manifests, hashes and frozen source. Do not rewrite old results,
merge development observations into final samples or delete source archives
during maintenance.
