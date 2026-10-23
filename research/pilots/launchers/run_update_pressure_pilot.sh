#!/usr/bin/env bash
# User-run experiment: two sequential waves, three workers per wave.
set -u
if [[ ! -x server/venv/bin/python || ! -f research/training/train_policy.py ]]; then
  echo "Run from the FlowSync project root with the server venv installed." >&2
  exit 1
fi
pressure_dir=$(PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/pilots/prepare_update_pressure_pilot.py) || exit 1
echo "Results and logs: $pressure_dir"
stop_children() {
  trap - INT TERM
  local running_pid
  while read -r running_pid; do
    [[ -n "$running_pid" ]] && kill -TERM "$running_pid" 2>/dev/null || true
  done < <(jobs -pr)
  wait || true
  echo "Interrupted; partial results retained in $pressure_dir" >&2
  exit 130
}
trap stop_children INT TERM
pressure_failed=0
for arm in control low_updates; do
  pressure_pids=()
  updates=32
  target_interval=200
  if [[ "$arm" == low_updates ]]; then
    updates=4
    target_interval=25
  fi
  for training_seed in 101 202 303; do
    IFS= read -r parent_checkpoint < "$pressure_dir/parent_$training_seed.txt" || exit 1
    PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u research/training/train_policy.py \
      --output "$pressure_dir/${arm}_seed_$training_seed" \
      --checkpoint "$parent_checkpoint" --seed "$training_seed" \
      --observation-version v7_36dim_observed \
      --episodes 90 --demo-episodes 24 --imitation-updates 0 --pretrain-updates 0 \
      --updates-per-episode "$updates" --learning-rate 0.0001 --validate-every 30 \
      --target-update "$target_interval" \
      --domain-randomization --episode-steps 1200 --validation-seeds 21001 21002 \
      --skip-initial-baselines --demo-loss-weight 0.5 --train-with-shield \
      --max-wall-seconds 360 > "$pressure_dir/${arm}_seed_$training_seed.log" 2>&1 &
    pressure_pids+=("$!")
  done
  for training_pid in "${pressure_pids[@]}"; do
    if ! wait "$training_pid"; then pressure_failed=1; fi
  done
  echo "Completed $arm wave (inspect summaries for actual completed episodes)."
  if [[ "$pressure_failed" != 0 ]]; then break; fi
done
echo "Results: $pressure_dir"
echo "Failed-process flag: $pressure_failed (0 = no process failures)"
if [[ "$pressure_failed" == 0 ]]; then
  PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/pilots/compare_update_pressure_pilot.py "$pressure_dir" \
    > "$pressure_dir/comparison.json"
  comparison_status=$?
  echo "Matched comparison: $pressure_dir/comparison.json (status $comparison_status)"
  echo "Primary: episode 90 across all six runs; truncated runs cannot pass the continuation screen."
  exit "$comparison_status"
fi
exit "$pressure_failed"
