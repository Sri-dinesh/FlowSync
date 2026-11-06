#!/usr/bin/env python3
"""
Generate results/flowsync_results_slim.json from results/flowsync_results.json.
Changes:
1. Drop raw_eval entirely.
2. training_curves: for each controller/ablation, average across seeds and keep mean and std per point.
   Downsampled to <= 100 points using a moving average over equal-sized episode windows.
3. timeseries_example: keep only 3 controllers (fixed_timer, greedy_max_queue, d3qn_fpa), <= 80 points each.
4. Keep unchanged: meta, summary, improvement_vs_fixed_timer_pct, significance, ablation_summary, phase_behavior, generalization, compute, notes.
5. Round floats to 4 significant digits in the slim file only.
6. Compact formatting: indent=1 and no line breaks inside numeric arrays.
7. Target: under 1500 lines and under 150 KB.
"""

import json
import math
import os
import re
import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT_DIR / "results" / "flowsync_results.json"
OUTPUT_FILE = ROOT_DIR / "results" / "flowsync_results_slim.json"

def round_sig(x, sig=4):
    if x is None or isinstance(x, (bool, str, int)):
        return x
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x) or x == 0:
            return x
        return float(f"{x:.{sig}g}")
    return x

def round_recursive(obj, sig=4):
    if isinstance(obj, dict):
        return {k: round_recursive(v, sig) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_recursive(v, sig) for v in obj]
    else:
        return round_sig(obj, sig)

def collapse_primitive_arrays(text):
    def replacer(match):
        inner = match.group(0)
        collapsed = ' '.join(inner.split())
        collapsed = re.sub(r',\s*', ', ', collapsed)
        collapsed = re.sub(r'\[\s*', '[', collapsed)
        collapsed = re.sub(r'\s*\]', ']', collapsed)
        return collapsed
    pattern = re.compile(r'\[[\s\d\.\,\-eEnulltruefalse\+]+\]')
    return pattern.sub(replacer, text)

def collapse_leaf_dicts(text):
    pattern = re.compile(r'\{\s*(\"[a-zA-Z0-9_]+\":\s*(?:\"[^\"]*\"|[^,\{\}\[\]]+)(?:,\s*\"[a-zA-Z0-9_]+\":\s*(?:\"[^\"]*\"|[^,\{\}\[\]]+))*)\s*\}')
    def replacer(match):
        inner = match.group(1)
        collapsed = ' '.join(inner.split())
        return '{ ' + collapsed + ' }'
    prev = None
    curr = text
    while curr != prev:
        prev = curr
        curr = pattern.sub(replacer, curr)
    return curr

def main():
    print(f"Reading input from {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Drop raw_eval entirely
    data.pop("raw_eval", None)

    # 2. Downsample training_curves: average across seeds, keep mean and std per point
    tc = data.get("training_curves", {})
    new_tc = {}
    for ctrl, cdata in tc.items():
        if cdata is None:
            new_tc[ctrl] = None
            continue
        min_eps = min(len(sdata["episode"]) for sdata in cdata.values())
        metrics = ["reward", "avg_wait_s", "loss", "epsilon"]
        
        # Window size 3: 219 // 3 = 73 points (<= 100 points)
        win_size = 3
        num_windows = min_eps // win_size

        episodes_ds = []
        metric_means = {m: [] for m in metrics}
        metric_stds = {m: [] for m in metrics}

        seeds = sorted(list(cdata.keys()))
        for w in range(num_windows):
            start_idx = w * win_size
            end_idx = (w + 1) * win_size
            mid_ep = int(round(float(np.mean([cdata[seeds[0]]["episode"][i] for i in range(start_idx, end_idx)]))))
            episodes_ds.append(mid_ep)

            for m in metrics:
                seed_win_avgs = []
                for s in seeds:
                    vals = cdata[s][m][start_idx:end_idx]
                    seed_win_avgs.append(float(np.mean(vals)))
                metric_means[m].append(float(np.mean(seed_win_avgs)))
                metric_stds[m].append(float(np.std(seed_win_avgs, ddof=1)) if len(seed_win_avgs) > 1 else 0.0)

        new_tc[ctrl] = {
            "episode": episodes_ds,
            "reward": {"mean": metric_means["reward"], "std": metric_stds["reward"]},
            "avg_wait_s": {"mean": metric_means["avg_wait_s"], "std": metric_stds["avg_wait_s"]},
            "loss": {"mean": metric_means["loss"], "std": metric_stds["loss"]},
            "epsilon": {"mean": metric_means["epsilon"], "std": metric_stds["epsilon"]},
        }
    data["training_curves"] = new_tc

    # 3. timeseries_example: keep only 3 controllers, <= 80 points each
    ts = data.get("timeseries_example", {})
    if ts:
        allowed_ctrls = {"fixed_timer", "greedy_max_queue", "d3qn_fpa"}
        if "queue_len_total" in ts:
            ts["queue_len_total"] = {k: v[:80] for k, v in ts["queue_len_total"].items() if k in allowed_ctrls}
        if "wait_cumulative" in ts:
            ts["wait_cumulative"] = {k: v[:80] for k, v in ts["wait_cumulative"].items() if k in allowed_ctrls}
        data["timeseries_example"] = ts

    # 4 & 5. Round all floats to 4 significant digits (in slim file only)
    rounded_data = round_recursive(data, sig=4)

    # 6. Compact formatting: indent=1 and no line breaks inside numeric arrays
    raw_json = json.dumps(rounded_data, indent=1)
    step1 = collapse_primitive_arrays(raw_json)
    final_json = collapse_leaf_dicts(step1)

    print(f"Writing slim results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_json + "\n")

    # 7. Print output file size and line count
    lines = final_json.splitlines()
    line_count = len(lines)
    file_size_bytes = OUTPUT_FILE.stat().st_size
    file_size_kb = file_size_bytes / 1024.0

    print("\n" + "=" * 60)
    print("SLIM EXPORT VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Output File: {OUTPUT_FILE}")
    print(f"Line count:  {line_count} lines  (Target: < 1500 lines)")
    print(f"File size:   {file_size_kb:.2f} KB ({file_size_bytes} bytes)  (Target: < 150 KB)")
    print("Under targets: " + ("YES (SUCCESS)" if line_count < 1500 and file_size_kb < 150 else "NO (NEEDS CUT)"))
    print("=" * 60 + "\n")

    # Validate with json.load
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reloaded = json.load(f)
    print(f"json.load validation passed! Top-level keys: {list(reloaded.keys())}")

if __name__ == "__main__":
    main()
