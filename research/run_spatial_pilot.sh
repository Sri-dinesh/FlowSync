#!/usr/bin/env bash
# User-run paired representation pilot; no checkpoint promotion.
set -u
if [[ ! -x server/venv/bin/python || ! -f research/train_policy.py ]]; then
  echo "Run from the FlowSync project root with the server venv installed." >&2
  exit 1
fi
spatial_dir=$(PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/prepare_spatial_pilot.py) || exit 1
echo "Results and logs: $spatial_dir"
stop_children() {
  trap - INT TERM
  local running_pid
  while read -r running_pid; do
    [[ -n "$running_pid" ]] && kill -TERM "$running_pid" 2>/dev/null || true
  done < <(jobs -pr)
  wait || true
  echo "Interrupted; partial results retained in $spatial_dir" >&2
  exit 130
}
trap stop_children INT TERM
spatial_failed=0
for arm in control spatial; do
  spatial_pids=()
  version=v9_48dim_zero_spatial
  [[ "$arm" == spatial ]] && version=v9_48dim_spatial
  for training_seed in 101 202 303; do
    IFS= read -r parent_checkpoint < "$spatial_dir/parent_$training_seed.txt" || exit 1
    PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u research/train_policy.py \
      --output "$spatial_dir/${arm}_seed_$training_seed" \
      --checkpoint "$parent_checkpoint" --expand-v7-parent --seed "$training_seed" \
      --observation-version "$version" \
      --episodes 90 --demo-episodes 24 --imitation-updates 0 --pretrain-updates 0 \
      --updates-per-episode 4 --learning-rate 0.0001 --validate-every 30 --target-update 25 \
      --domain-randomization --episode-steps 1200 --validation-seeds 21001 21002 \
      --skip-initial-baselines --demo-loss-weight 0.5 --train-with-shield \
      --max-wall-seconds 600 > "$spatial_dir/${arm}_seed_$training_seed.log" 2>&1 &
    spatial_pids+=("$!")
  done
  for training_pid in "${spatial_pids[@]}"; do
    if ! wait "$training_pid"; then spatial_failed=1; fi
  done
  echo "Completed $arm wave (inspect actual episodes and validation completeness)."
  if [[ "$spatial_failed" != 0 ]]; then break; fi
done
echo "Results: $spatial_dir"
echo "Failed-process flag: $spatial_failed (0 = no process failures)"
if [[ "$spatial_failed" == 0 ]]; then
  PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/compare_spatial_pilot.py "$spatial_dir" \
    > "$spatial_dir/comparison.json"
  comparison_status=$?
  echo "Matched comparison: $spatial_dir/comparison.json (status $comparison_status)"
  echo "Primary: episode 90 across all six runs, versus matched control AND unchanged parents."
  exit "$comparison_status"
fi
exit "$spatial_failed"
