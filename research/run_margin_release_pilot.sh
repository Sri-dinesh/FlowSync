#!/usr/bin/env bash
# User-run paired continuation pilot, about ten minutes; no final tests/uploads.
set -u
if [[ ! -x server/venv/bin/python || ! -f research/train_policy.py ]]; then
  echo "Run from the FlowSync project root with the server venv installed." >&2
  exit 1
fi
margin_dir=$(PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/prepare_margin_pilot.py) || exit 1
echo "Results and logs: $margin_dir"
stop_children() {
  trap - INT TERM
  local running_pid
  while read -r running_pid; do
    [[ -n "$running_pid" ]] && kill -TERM "$running_pid" 2>/dev/null || true
  done < <(jobs -pr)
  wait || true
  echo "Interrupted; partial results retained in $margin_dir" >&2
  exit 130
}
trap stop_children INT TERM
margin_failed=0
for arm in constant release; do
  margin_pids=()
  margin_flags=()
  if [[ "$arm" == release ]]; then
    margin_flags=(--demo-loss-final-weight 0 --demo-loss-decay-episodes 60)
  fi
  for training_seed in 101 202 303; do
    IFS= read -r parent_checkpoint < "$margin_dir/parent_$training_seed.txt" || exit 1
    PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u research/train_policy.py \
      --output "$margin_dir/${arm}_seed_$training_seed" \
      --checkpoint "$parent_checkpoint" --seed "$training_seed" \
      --episodes 120 --demo-episodes 24 --imitation-updates 0 --pretrain-updates 0 \
      --learning-rate 0.0001 --validate-every 30 --target-update 200 \
      --observation-version v7_36dim_observed --domain-randomization --episode-steps 1200 \
      --validation-seeds 21001 21002 --skip-initial-baselines \
      --demo-loss-weight 0.5 --train-with-shield --max-wall-seconds 300 \
      "${margin_flags[@]}" > "$margin_dir/${arm}_seed_$training_seed.log" 2>&1 &
    margin_pids+=("$!")
  done
  for training_pid in "${margin_pids[@]}"; do
    if ! wait "$training_pid"; then margin_failed=1; fi
  done
  echo "Completed $arm wave (inspect summaries for actual episode counts)."
  if [[ "$margin_failed" != 0 ]]; then break; fi
done
echo "Results: $margin_dir"
echo "Failed-process flag: $margin_failed (0 = no process failures)"
echo "Compare both arms on common completed validation checkpoints, not only their selected best."
if [[ "$margin_failed" == 0 ]]; then
  PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python research/compare_margin_pilot.py "$margin_dir" \
    > "$margin_dir/comparison.json"
  comparison_status=$?
  echo "Paired comparison: $margin_dir/comparison.json (status $comparison_status; 0 = available)"
  if [[ "$comparison_status" != 0 ]]; then exit "$comparison_status"; fi
fi
exit "$margin_failed"
