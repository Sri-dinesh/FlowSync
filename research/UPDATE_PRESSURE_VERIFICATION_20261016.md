# Update-pressure implementation verification

The full pilot is prepared, not executed. Run
`bash research/run_update_pressure_pilot.sh` from the project root.
The [frozen design](UPDATE_PRESSURE_PROTOCOL_20261016.md) defines the comparisons
and continuation criteria; no performance improvement is assumed.

## Checks completed

- Broad targeted regression suite: 111 passed. After adding another truncated
  endpoint case, all 13 focused update-pressure tests passed (these overlap the
  broad suite; do not sum the counts).
- Shell syntax and `git diff --check` passed.
- The shared comparator refactor reproduces the saved temporal pilot comparison
  exactly, without changing its negative outcome or earlier artifacts.
- Tests cover aligned target-copy positions, actual per-arm update budgets,
  worker failure propagation, paths with spaces, rejecting mismatched inputs,
  invalid diagnostics and incomplete safety coverage, and refusing to continue
  a truncated pilot or one merely less bad than control.

## Real one-episode mechanics smoke

Artifacts: `results/research_training/update_pressure_smoke_nnr27n4e`.
Both arms used parent seed 101, 24 demonstrations, one online episode,
validation seed 21001, and a 180-second worker budget. This deliberately short
run is not the full pilot and must not be evaluated using its continuation gate.

Both completed (control 64.8 s, low-updates 58.0 s), with exactly 32 and 4
optimizer updates respectively. Verified unchanged parents, initial/warmup
weights equal to parents, paired demonstrations and training inputs, finite
weights/diagnostics, checkpoint hashes, frozen source archive and validation
arrival pairing. All 36 validation rollouts had complete signal-audit coverage:
43,200 samples, zero measured conflict/clearance violations. This is not a
real-world safety claim.

| Smoke checkpoint | Mean validation delay (s) |
| --- | ---: |
| Initial, both arms | 12.489 |
| Control after one episode | 12.574 |
| Low updates after one episode | 12.600 |

Both retained their initial checkpoint. These one-episode values establish no
performance benefit; they only demonstrate that both intended code paths run
and that the comparison can capture regression. No checkpoint was promoted.
The full episode-90, three-training-seed comparison remains necessary to assess
the prespecified learning-procedure hypothesis. No final-test panel was used.
