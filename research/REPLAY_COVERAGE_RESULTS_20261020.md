# Replay-coverage outcome (verified 2026-10-20)

Artifacts: `results/replay_coverage/update_pressure_20261017`, collected on
2026-10-17. The completed report was inspected after the execution handle became
unavailable; the experiment was not restarted. Runtime was 56.32 seconds.
[Frozen protocol](REPLAY_COVERAGE_PROTOCOL_20261017.md).

| Mean reserved-training-probe label MAE | Value |
| --- | ---: |
| Unchanged parents | 10.744884 |
| Narrow fit: eight episodes | 12.647955 |
| Broader fit: twenty episodes | 11.759138 |

Broader coverage reduces error 7.03% relative to narrow fitting, but remains
9.44% worse than unchanged parents. Its continuation gate fails. These are
errors against initial Q targets, **not traffic-delay seconds** or ground-truth
optimal returns. Do not adopt a production training change from this result.

| Parent seed | Original / expanded fit transitions | Probe transitions | Parent / narrow / broader probe MAE |
| --- | ---: | ---: | --- |
| 101 | 100 / 253 | 62 | 3.920 / 4.149 / 4.259 |
| 202 | 80 / 234 | 54 | 11.479 / 13.081 / 12.740 |
| 303 | 85 / 216 | 36 | 16.835 / 20.714 / 18.278 |

All broader fits worsen probe error versus parents; seed 101 also worsens
relative to narrow fitting. The transition-level demonstration fractions changed
from 47.0% to 43.5%, 46.3% to 52.1%, and 50.6% to 49.1%, respectively. This
experiment changes sample coverage/reuse/realized mixture together; it does not
isolate a single optimizer mechanism.

Verified all input, archived-source and dataset hashes, unchanged original
fit/probe tensors and labels, and the original narrow sampling schedules.
All 15 narrow-arm measurement points reproduce the previous fixed-label curve
exactly. The report recomputes from all 30 raw measurement points. The original
datasets, models and failed experiments remain preserved. The combined replay,
learning and pilot regression suite passed 75 tests on 2026-10-20.

Decision: stop this Q-error/replay-size line as a demonstrated remedy; it has
not produced a traffic-performance improvement. The next collected evidence is
[all-action branch labels](ACTION_RANK_RESULTS_20261020.md), which scores actual
short-horizon traffic consequences rather than only prediction accuracy.
