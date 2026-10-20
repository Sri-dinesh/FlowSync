#!/usr/bin/env bash
# User-run, validation-only pilot. No uploads, model promotion, or final tests.
set -u

if [[ ! -x server/venv/bin/python || ! -f research/train_policy.py ]]; then
  echo "Run this script from the FlowSync project root with its server venv installed." >&2
  exit 1
fi
mkdir -p results/research_training || exit 1
pilot_dir=$(mktemp -d results/research_training/pilot_v5_XXXXXXXX) || exit 1
echo "Results and logs: $pilot_dir"

pilot_pids=()
stop_children() {
  trap - INT TERM
  # Restrict termination to jobs still running in this launcher, not stale PIDs.
  local running_pid
  while read -r running_pid; do
    [[ -n "$running_pid" ]] && kill -TERM "$running_pid" 2>/dev/null || true
  done < <(jobs -pr)
  wait || true
  echo "Pilot interrupted. Partial artifacts retained in: $pilot_dir" >&2
  exit 130
}
trap stop_children INT TERM

for training_seed in 101 202 303; do
  PYTHONDONTWRITEBYTECODE=1 server/venv/bin/python -u research/train_policy.py \
    --output "$pilot_dir/seed_$training_seed" \
    --seed "$training_seed" \
    --episodes 900 \
    --demo-episodes 200 \
    --imitation-updates 2000 \
    --pretrain-updates 500 \
    --learning-rate 0.0001 \
    --validate-every 50 \
    --observation-version v7_36dim_observed \
    --target-update 200 \
    --domain-randomization \
    --episode-steps 3000 \
    --validation-seeds 21001 21002 21003 21004 21005 \
    --demo-loss-weight 0.5 \
    --train-with-shield \
    --max-wall-seconds 600 \
    > "$pilot_dir/seed_$training_seed.log" 2>&1 &
  pilot_pids+=("$!")
done

pilot_failed=0
for training_pid in "${pilot_pids[@]}"; do
  if ! wait "$training_pid"; then
    pilot_failed=1
  fi
done
echo "Results: $pilot_dir"
echo "Failed-process flag: $pilot_failed (0 = no process failures)"
echo "Check summary.json for budget stops, actual episodes and completed validation."
exit "$pilot_failed"
