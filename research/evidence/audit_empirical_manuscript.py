"""Recompute empirical-paper numbers from preserved records; no traffic rollouts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANUSCRIPT = ROOT / "research/docs/papers/PAPER_DRAFT_EMPIRICAL_20261023.md"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def same_fields(saved, recomputed):
    mismatches = [key for key, value in recomputed.items() if saved.get(key) != value]
    if mismatches:
        raise ValueError(f"Raw report does not reproduce: {mismatches}")


def verified_bundle(directory):
    manifest, report = read(directory/"manifest.json"), read(directory/"report.json")
    if report.get("complete") is not True or report.get("smoke") is True:
        raise ValueError("Complete non-smoke evidence required")
    for path, expected in manifest.get("input_hashes", {}).items():
        if sha(path) != expected:
            raise ValueError(f"Changed upstream evidence: {path}")
    for name, expected in report["output_hashes"].items():
        target = (directory/name).resolve()
        if not target.is_relative_to(directory.resolve()) or sha(target) != expected:
            raise ValueError(f"Changed output: {name}")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Changed archived source: {name}")
    return manifest, report


def plot_diagnostics(output, groups, arrival, averaged, model):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), layout="constrained")
    x = np.arange(len(groups))
    for shift, key, label in ((-.24, "mean_max_abs_q_delta", "Maximum absolute Q change"),
                              (0, "mean_valid_q_delta_range", "Range of valid-action Q changes"),
                              (.24, "mean_margin", "Valid-action margin")):
        axes[0].bar(x+shift, [g[key] for g in groups], width=.24, label=label)
    names = [g["state_distribution"].capitalize() for g in groups]
    axes[0].set(xticks=x, xticklabels=names, ylabel="Mean learned-return units", title="Same-state numerical sensitivity")
    axes[0].set_ylim(0, max(g["mean_margin"] for g in groups)*1.45)
    axes[0].legend(frameon=False, fontsize=7)
    axes[1].bar(x, [g["spatial_changed_proposals"] for g in groups], color="#355f80")
    axes[1].set(xticks=x, xticklabels=names, ylim=(0, 1), ylabel="Changed final proposals", title="Natural vs zero spatial inputs")
    for i, group in enumerate(groups):
        axes[1].text(i, .03, f"{group['spatial_changed_proposals']} / {group['gates']} gates", ha="center")
    fig.supxlabel("Training-state panels; same checkpoint/mask. Means are descriptive, not pointwise bounds.", fontsize=8)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(output/f"input_action_sensitivity.{ext}", dpi=220)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), layout="constrained")
    flip = arrival["alternatives_with_delay_sign_flip"]
    axes[0].bar(["Sign changes", "No sign change"], [flip, arrival["alternatives"]-flip], color=["#b95039", "#355f80"])
    axes[0].set(ylabel="Alternatives", title="Additional arrival futures")
    for axis, report, title in zip(axes[1:], (averaged, model),
                                   ("Frozen hindsight choices\n18 sources, 54 gates", "Observed-input model probe\n36 sources, 72 gates")):
        axis.bar(["Parent", "Single", "Mean8"], [report["arms"][a]["mean_gain"][0] for a in ("parent", "single", "mean8")],
                 color=["#888888", "#b95039", "#355f80"])
        axis.axhline(0, color="gray", linewidth=.8)
        axis.set(title=title, ylabel="Mean branch delay saved (vehicle-seconds)")
    fig.supxlabel("Distinct panels; no pooling or uncertainty interval. Positive means less stopped waiting.", fontsize=8)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(output/f"future_labels_and_probe.{ext}", dpi=220)
    plt.close(fig)


def build(output, manuscript=DEFAULT_MANUSCRIPT):
    if output.exists():
        raise FileExistsError("Choose a new output directory")
    # Imports are lazy so command discovery needs no scientific dependencies.
    import torch
    from research.evidence.build_paper_evidence import load_evidence
    from research.evidence.export_evidence import controller_summary
    from research.audits.verify_spatial_input_audit import verify as verify_spatial
    from research.audits.audit_arrival_label_stability import summarize as arrival_summary
    from research.evaluation.evaluate_averaged_action_labels import freeze_choices, score_source, summarize
    from research.policies.averaged_label_model import fit_models, predict_source, prediction_errors
    from research.policies.averaged_label_model import summarize as model_summary
    from research.evidence.export_teacher_evidence import read_verified
    from research.audits.audit_teacher_alignment import score
    from research.audits.audit_teacher_horizon import summarize as horizon_summary
    from research.pilots.compare_spatial_pilot import compare
    from research.audits.verify_sumo_future_panel import verify as verify_sumo
    from research.evidence.export_sumo_future_evidence import tables as sumo_tables
    torch.set_num_threads(1)
    folders = {
        "main": ROOT/"results/replicate_evaluation/matched_shield_v5_20261015",
        "spatial": ROOT/"results/research_training/spatial_v9_k2bg79oc",
        "inputs": ROOT/"results/spatial_input_audit/pilot_20261022",
        "arrival": ROOT/"results/arrival_label_stability/panel_20261021T063020Z",
        "averaged": ROOT/"results/averaged_action_labels/panel_20261021T091742Z",
        "model": ROOT/"results/averaged_label_model/pilot_20261021T095353Z",
        "teacher": ROOT/"results/teacher_alignment/pilot_20261022",
        "horizon": ROOT/"results/teacher_horizon/pilot_20261022",
        "sumo": ROOT/"results/sumo_future_panel/full_20261023",
    }
    claims = []
    def claim(key, value, unit, panel):
        claims.append(dict(claim=key, value=value, unit=unit, panel=panel,
                           source=str(folders[panel].relative_to(ROOT))))
    main_manifest, main_report, rows = load_evidence(folders["main"])
    for row in controller_summary(rows):
        claim(f"{row['controller']}.mean_delay", row["mean_delay_s"], "s/arrived vehicle", "main")
        claim(f"{row['controller']}.mean_within_run_p95", row["mean_within_run_p95_s"], "s", "main")
    claim("runs", len(rows), "runs", "main")
    claim("signal_samples", sum(r["safety_samples"] for r in rows), "samples", "main")
    uq = [r for r in rows if r["label"].startswith("flowsync_uq_seed")]
    shield = [r for r in rows if r["label"].startswith("d3qn_shield_seed")]
    for key, value in (("uq_runs", len(uq)), ("fallback_activations", sum(r["fallback_activations"] for r in uq)),
                       ("fallback_ticks", sum(r["fallback_steps"] for r in uq)),
                       ("d3qn_shield_interventions", sum(r["shield_interventions"] for r in shield)),
                       ("d3qn_anti_starvation_interventions", sum(sum(v for k, v in
                        r["controller_diagnostics"]["shield"]["override_counts_by_reason"].items()
                        if k.startswith("anti_starvation")) for r in shield))):
        claim(key, value, "count", "main")
    for name in ("d3qn_shield_vs_max_pressure_shield_avg_delay", "flowsync_uq_vs_d3qn_shield_avg_delay"):
        item = main_report["comparisons"][name]
        claim(name, item["mean_delay_saved_s"], "s saved", "main")
        for end, value in zip(("low", "high"), item["bootstrap_ci95_s"]):
            claim(f"{name}.ci95_{end}", value, "s saved", "main")
    spatial = compare(folders["spatial"])
    if spatial != read(folders["spatial"]/"comparison.json"):
        raise ValueError("Spatial comparison changed")
    for key in ("mean_delay_control", "mean_delay_spatial", "mean_delay_parent"):
        claim(key, spatial["primary"][key], "s/arrived vehicle", "spatial")
    input_verification = verify_spatial(folders["inputs"])
    inputs = read(folders["inputs"]/"report.json")
    groups = [g for g in inputs["groups"] if g["model"] == "spatial_90"]
    claim("gates", sum(g["gates"] for g in groups), "gates", "inputs")
    claim("spatial_changed_proposals", sum(g["spatial_changed_proposals"] for g in groups), "gates", "inputs")
    for group in groups:
        for key in ("gates", "mean_max_abs_q_delta", "mean_valid_q_delta_range", "mean_margin"):
            claim(f"{group['state_distribution']}.{key}", group[key], "gates" if key == "gates" else "Q units", "inputs")
    _, arrival = verified_bundle(folders["arrival"])
    raw_arrival = lines(folders["arrival"]/"runs.jsonl")
    recomputed, _ = arrival_summary(raw_arrival, 18, False, None)
    same_fields(arrival, recomputed)
    for key in ("gates", "alternatives", "alternatives_with_delay_sign_flip", "original_choice_future_cases",
                "original_choices_harmful_future_cases", "original_choices_qualified_in_at_least_six_futures"):
        claim(key, arrival[key], "count", "arrival")
    _, averaged = verified_bundle(folders["averaged"])
    choices = freeze_choices(sorted(raw_arrival, key=lambda r: (r["training_seed"], r["scenario"])))
    if json.loads(json.dumps(choices)) != read(folders["averaged"]/"frozen_choices.json"):
        raise ValueError("Frozen averaged choices do not reconstruct")
    scores = [score_source(row, choices, range(8, 16))[0] for row in lines(folders["averaged"]/"runs.jsonl")]
    if scores != read(folders["averaged"]/"source_scores.json"):
        raise ValueError("Averaged raw scores changed")
    same_fields(averaged, summarize(scores, 18, False))
    manifest, model = verified_bundle(folders["model"])
    models = fit_models(lines(folders["model"]/"fit.jsonl"), manifest["config"], manifest["scenarios"], manifest["parents"])
    for (parent, arm), fitted in models.items():
        if fitted != read(folders["model"]/f"model_{parent}_{arm}.json"):
            raise ValueError("Saved model does not refit under current packaged implementation")
    scores = []
    for row, predicted in zip(lines(folders["model"]/"probe.jsonl"),
                              lines(folders["model"]/"predictions_before_outcomes.jsonl"), strict=True):
        current = predict_source(row, row["selected_steps"], models)
        if json.loads(json.dumps(current)) != predicted:
            raise ValueError("Pre-outcome model prediction changed")
        result, _ = score_source(row, predicted, range(8, 16), expected_gates=2)
        result["prediction_mae"] = prediction_errors(row, predicted)
        scores.append(result)
    if scores != read(folders["model"]/"source_scores.json"):
        raise ValueError("Model raw probe scores changed")
    same_fields(model, model_summary(scores, manifest["config"], manifest["scenarios"], 72, len(models)))
    for panel, report in (("averaged", averaged), ("model", model)):
        for arm, values in report["arms"].items():
            for key in ("cases", "changed_gates", "qualified_cases", "harmful_cases"):
                claim(f"{arm}.{key}", values[key], "count", panel)
            claim(f"{arm}.mean_delay_saved", values["mean_gain"][0], "vehicle-seconds", panel)
    frozen = read(folders["teacher"]/"frozen_proposals.json")
    for name, summary in (("teacher", lambda r: score(r, frozen)),
                          ("horizon", lambda r: horizon_summary(r, frozen, "completed"))):
        report, raw = read_verified(folders[name])
        same_fields(report, summary(raw))
        if name == "teacher":
            for key in ("sources", "eligible_gates", "signal_samples"):
                claim(key, report[key], "count", name)
        else:
            for role in ("first", "excluded"):
                for horizon in ("200", "600"):
                    gain = report["panels"][role][horizon]["mean_gain"]
                    for index, unit in enumerate(("vehicle-seconds", "vehicles", "s")):
                        claim(f"{role}.{horizon}.gain_{index}", gain[index], unit, name)
    sumo_verification = verify_sumo(folders["sumo"])
    if sumo_verification["smoke"]:
        raise ValueError("Scientific SUMO panel required, not smoke")
    cases = read(folders["sumo"]/"frozen_cases.json")
    _, sumo_sources, sumo_arms = sumo_tables(cases, lines(folders["sumo"]/"outcomes.jsonl"),
                                           read(folders["sumo"]/"frozen_choices.json"))
    for key, value in (("branches", sumo_verification["branches"]), ("source_gates", len(sumo_sources)),
                       ("check_cases", sum(s["check_futures"] for s in sumo_sources)),
                       ("positive_cases", sum(s["positive"] for s in sumo_sources)),
                       ("negative_cases", sum(s["negative"] for s in sumo_sources)),
                       ("deadband_cases", sum(s["deadband"] for s in sumo_sources)),
                       ("mixed_gates", sum(s["mixed"] for s in sumo_sources)),
                       ("source_ticks", sumo_verification["unique_source_ticks"]),
                       ("branch_ticks", sumo_verification["branch_ticks"])):
        claim(key, value, "count", "sumo")
    for source in sumo_sources:
        for key in ("positive", "negative", "single_delay_saved", "mean8_delay_saved"):
            claim(f"{source['source']}.{key}", source[key], "vehicle-seconds" if "saved" in key else "count", "sumo")
    for arm in sumo_arms:
        for key in ("mean_delay_saved_vehicle_seconds", "mean_completed_trips_gained", "mean_endpoint_wait_saved_s",
                    "changed_gates", "qualified_cases", "harmful_cases"):
            unit = "vehicle-seconds" if "delay" in key else "s" if "wait" in key else "count"
            claim(f"{arm['arm']}.{key}", arm[key], unit, "sumo")
    output.mkdir(parents=True, exist_ok=False)
    plot_diagnostics(output, groups, arrival, averaged, model)
    with (output/"claims.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(claims[0]))
        writer.writeheader()
        writer.writerows(claims)
    note = ("# Empirical manuscript numerical audit\n\n"
        f"Recomputed {len(claims)} quantities across nine preserved panels. "
        "Main statistics, spatial comparison/network probes, arrival labels, averaged "
        "choices, six model refits/predictions/probe scores, teacher/horizon summaries and "
        "the completed independent SUMO panel reproduce.\n\n"
        "No traffic trajectories were rerun. This ledger does not automatically validate "
        "every prose number, causal interpretation, reference, novelty or simulator accuracy. "
        "Archived source hashes verify; model computations use the current packaged helpers, "
        "whose exact output parity is measured, without claiming live-source byte parity.\n\n"
        "Units and panels are explicit in claims.csv; no panels or correlated samples are pooled. "
        "Publication readiness remains false.\n")
    (output/"README.md").write_text(note)
    audit = dict(verified=True, quantities=len(claims), traffic_rollouts=0, publication_ready=False,
                 manuscript_sha256=sha(manuscript), auditor_sha256=sha(__file__),
                 inputs={str(p.relative_to(ROOT)): sha(p) for d in folders.values() for p in sorted(d.iterdir())
                         if p.is_file() and p.suffix in (".json", ".jsonl", ".zip", ".md")},
                 spatial_verification=input_verification,
                 sumo_verification=sumo_verification,
                 outputs={p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    (output/"audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False)+"\n")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, default=DEFAULT_MANUSCRIPT)
    args = parser.parse_args()
    result = build(args.output, args.manuscript)
    print(json.dumps({k: result[k] for k in ("verified", "quantities", "traffic_rollouts", "publication_ready")}, indent=2))


if __name__ == "__main__":
    main()
