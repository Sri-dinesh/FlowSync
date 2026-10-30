"""Export verified PPO curves and descriptive same-state policy-change diagnostics."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.distributions import kl_divergence

from research.pilots.run_ppo_restoration_pilot import verify, load_batch, means, STAGES, sha, write
from research.policies.ppo import PPOController


def csv_file(path, rows):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def policy_changes(source, worker):
    """Identical delivered states/masks, not counterfactual traffic rollouts."""
    folder = source/worker["output"]
    initial = PPOController(folder/"checkpoint_0.pt").model
    final = PPOController(folder/"checkpoint_90.pt").model
    rows = [t for batch in worker["updates"] for episode in load_batch(folder/f"batch_{batch['episode']}.npz") for t in episode]
    states = torch.as_tensor(np.stack([t.state for t in rows]))
    masks = torch.as_tensor(np.stack([t.mask for t in rows]))
    choices = masks.sum(1) > 1
    demand_choices = choices & states[:, :12].gt(0).any(1)
    with torch.no_grad():
        old, new = initial.distribution(states, masks), final.distribution(states, masks)
        changed = old.logits.argmax(1) != new.logits.argmax(1)
        divergence = kl_divergence(old, new)
    summaries = [json.loads(line) for line in (folder/"episodes.jsonl").read_text().splitlines()]
    proposals = [p for summary in summaries for p in summary["proposals"][:summary["transitions"]]]
    if len(proposals) != len(rows):
        raise ValueError("Proposals do not cover complete decision states")
    return dict(parent=worker["parent"], arm=worker["arm"], completed_decisions=len(rows),
        multiple_valid_actions=int(choices.sum()), multiple_valid_with_demand=int(demand_choices.sum()),
        changed_greedy_actions=int(changed.sum()), changed_with_demand=int((changed & demand_choices).sum()),
        initial_mean_entropy=float(old.entropy().mean()), final_mean_entropy=float(new.entropy().mean()),
        mean_initial_to_final_kl=float(divergence.mean()),
        gate_shield_overrides=sum(p["proposed"] != p["executed"] for p in proposals),
        dropped_partial_ticks=sum(s["dropped_partial_ticks"] for s in summaries),
        actor_updates=sum(log["kind"] == "actor" for batch in worker["updates"] for log in batch["updates"]),
        critic_updates=sum(log["kind"] == "critic" for batch in worker["updates"] for log in batch["updates"]))


def reward_pairs(source):
    rows, arithmetic_failures = [], 0
    for parent in ("101", "202", "303"):
        arms = [[json.loads(line) for line in (source/f"{parent}_{arm}"/"episodes.jsonl").read_text().splitlines()]
                for arm in ("raw", "restored")]
        for raw, restored in zip(*arms):
            if any(raw[k] != restored[k] for k in ("episode", "seed", "scenario", "fault", "arrival_trace_hash")):
                raise ValueError("Training reward contrast is not paired")
            for episode in (raw, restored):
                arithmetic_failures += int(abs(sum(episode["reward_components"].values())-episode["reward"]) > 1e-7)
            dd, dr = restored["avg_delay"]-raw["avg_delay"], restored["reward"]-raw["reward"]
            components = {key: restored["reward_components"][key]-raw["reward_components"][key]
                          for key in raw["reward_components"]}
            rows.append(dict(parent=parent, episode=raw["episode"], seed=raw["seed"],
                delta_mean_delay_s=dd, delta_undiscounted_reward=dr,
                reward_prefers_higher_delay=dd*dr > 1e-8,
                delay_component_prefers_higher_delay=dd*components["delay"] > 1e-8,
                **{f"delta_component_{key}": value for key, value in components.items()}))
    return rows, dict(paired_comparisons=len(rows), component_arithmetic_failures=arithmetic_failures,
        reward_prefers_higher_delay=sum(r["reward_prefers_higher_delay"] for r in rows),
        delay_component_prefers_higher_delay=sum(r["delay_component_prefers_higher_delay"] for r in rows),
        scope="Post-hoc undiscounted full-episode contrasts on paired training arrivals; not PPO's discounted completed-macro objective, independent traffic replicates, a causal explanation or a new reward selection screen.")


def export(source, output):
    if (source/"recovery.json").exists():
        from research.pilots.recover_ppo_restoration_pilot import verify_recovery
        audit = verify_recovery(source)
    else:
        audit = verify(source)
    report = json.loads((source/"report.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    rows = [r for worker in report["workers"] for r in worker["evaluations"]]+report["baselines"]
    csv_file(output/"all_development_cases.csv", rows)
    manifest = json.loads((source/"manifest.json").read_text())
    faults = {c["case_id"]: c["fault"]["name"] for c in manifest["validation_cases"]}
    condition_rows = []
    for method, stage in sorted({(r["baseline"] or f"ppo_{r['arm']}", str(r["stage"])) for r in rows}):
        for fault in ("clean", "validation_mixed", "all"):
            subset = [r for r in rows if (r["baseline"] or f"ppo_{r['arm']}") == method and str(r["stage"]) == stage
                      and (fault == "all" or faults[r["case_id"]] == fault)]
            condition_rows.append(dict(method=method, stage=stage, fault=fault, runs=len(subset), **means(subset)))
    csv_file(output/"condition_summary.csv", condition_rows)
    curve = [dict(parent=w["parent"], arm=w["arm"], episode=stage,
                  **means([r for r in w["evaluations"] if r["stage"] == stage]))
             for w in report["workers"] for stage in STAGES]
    csv_file(output/"checkpoint_curve.csv", curve)
    changes = [policy_changes(source, w) for w in report["workers"]]
    csv_file(output/"same_state_policy_changes.csv", changes)
    paired, reward_audit = reward_pairs(source)
    csv_file(output/"training_reward_pairs.csv", paired)
    write(output/"training_reward_audit.json", reward_audit)
    updates = [dict(parent=w["parent"], arm=w["arm"], episode=batch["episode"], **log)
               for w in report["workers"] for batch in w["updates"] for log in batch["updates"]]
    fields = list(dict.fromkeys(k for row in updates for k in row))
    csv_file(output/"optimizer_telemetry.csv", [{k: row.get(k) for k in fields} for row in updates])
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), layout="constrained")
    for ax, key, ylabel in ((axes[0], "delay", "Mean stopped wait per arrived vehicle (s)"),
                            (axes[1], "p95", "Average within-run p95 stopped wait (s)")):
        for arm, color in (("raw", "#a05b00"), ("restored", "#1768ac")):
            for parent in ("101", "202", "303"):
                subset = [r for r in curve if r["arm"] == arm and r["parent"] == parent]
                ax.plot(STAGES, [r[key] for r in subset], color=color, alpha=.25, linewidth=1)
            ax.plot(STAGES, [report["comparison"]["curve"][f"{arm}_{s}"][key] for s in STAGES],
                    marker="o", color=color, label=f"PPO {arm}: mean of 3 parents")
        for name, color, style in (("pressure_raw", "#8e5ea2", "--"), ("pressure_restored", "#548c64", ":"),
                                    ("pressure_bare", "#565d69", "-.")):
            ax.axhline(report["comparison"]["reference_means"][name][key], color=color, linestyle=style,
                       label={"pressure_raw": "MP shielded raw", "pressure_restored": "MP shielded restored",
                              "pressure_bare": "MP bare raw"}[name])
        ax.set(xlabel="Completed online episodes (first 6: critic only)", ylabel=ylabel, ylim=(0, None))
        ax.set_xticks(STAGES)
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=8, loc="lower left")
    passed = report["comparison"]["continue_to_expanded_validation"]
    fig.suptitle(f"Bounded PPO/restoration development: frozen episode-90 screen {'passes' if passed else 'fails'}")
    fig.supxlabel("Six reused-family development cases; thin lines show every parent, thick lines show equal means.\n"
                  "Descriptive curves without confidence intervals; no best-checkpoint selection or independent final test.", fontsize=9)
    fig.savefig(output/"ppo_curve.png", dpi=220)
    fig.savefig(output/"ppo_curve.svg")
    plt.close(fig)
    (output/"exporter_source.py").write_bytes(Path(__file__).read_bytes())
    inputs = ["manifest.json", "report.json"]
    if (source/"recovery.json").exists():
        inputs += ["recovery.json", "recovery_source.py"]
    write(output/"manifest.json", dict(input_directory=str(source.resolve()), verification=audit,
        input_sha256={name: sha(source/name) for name in inputs},
        output_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()}, publication_ready=False,
        scope="Existing development observations and retrospective same-delivered-state actor comparisons; no new traffic, counterfactual policy performance, statistical significance or promotion."))
    return dict(complete=True, development_cases=len(rows), policy_diagnostics=changes, training_reward_audit=reward_audit,
                continue_to_expanded_validation=passed, publication_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
