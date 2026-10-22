#!/usr/bin/env bash
# User-run two-arm pilot. About 12 minutes plus atomic validation/save overhead.
set -u
if [[ ! -x server/venv/bin/python || ! -f research/training/train_policy.py ]]; then
  echo "Run from the FlowSync project root with the server venv installed." >&2
  exit 1
fi
temporal_dir=$(PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/pilots/prepare_temporal_pilot.py) || exit 1
echo "Results and logs: $temporal_dir"
stop_children() {
  trap - INT TERM
  local running_pid
  while read -r running_pid; do
    [[ -n "$running_pid" ]] && kill -TERM "$running_pid" 2>/dev/null || true
  done < <(jobs -pr)
  wait || true
  echo "Interrupted; partial results retained in $temporal_dir" >&2
  exit 130
}
trap stop_children INT TERM
temporal_failed=0
for arm in control temporal; do
  temporal_pids=()
  temporal_version=v8_64dim_zero_history
  [[ "$arm" == temporal ]] && temporal_version=v8_64dim_temporal
  for training_seed in 101 202 303; do
    IFS= read -r parent_checkpoint < "$temporal_dir/parent_$training_seed.txt" || exit 1
    PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u research/training/train_policy.py \
      --output "$temporal_dir/${arm}_seed_$training_seed" \
      --checkpoint "$parent_checkpoint" --expand-v7-parent --seed "$training_seed" \
      --observation-version "$temporal_version" \
      --episodes 90 --demo-episodes 24 --imitation-updates 0 --pretrain-updates 0 \
      --updates-per-episode 32 --learning-rate 0.0001 --validate-every 30 --target-update 200 \
      --domain-randomization --episode-steps 1200 --validation-seeds 21001 21002 \
      --skip-initial-baselines --demo-loss-weight 0.5 --train-with-shield \
      --max-wall-seconds 360 > "$temporal_dir/${arm}_seed_$training_seed.log" 2>&1 &
    temporal_pids+=("$!")
  done
  for training_pid in "${temporal_pids[@]}"; do
    if ! wait "$training_pid"; then temporal_failed=1; fi
  done
  echo "Completed $arm wave (inspect summaries for actual completed episodes)."
  if [[ "$temporal_failed" != 0 ]]; then break; fi
done
echo "Results: $temporal_dir"
echo "Failed-process flag: $temporal_failed (0 = no process failures)"
if [[ "$temporal_failed" == 0 ]]; then
  PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/pilots/compare_temporal_pilot.py "$temporal_dir" \
    > "$temporal_dir/comparison.json"
  comparison_status=$?
  echo "Matched comparison: $temporal_dir/comparison.json (status $comparison_status)"
  echo "Primary: latest common completed checkpoint across ALL six runs, not each run's best."
  exit "$comparison_status"
fi
exit "$temporal_failed"
