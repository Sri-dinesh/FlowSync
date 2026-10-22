#!/usr/bin/env python3
"""Provenance-checked tables/figure for the failed teacher/horizon diagnostics."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.audits.audit_teacher_alignment import score
from research.audits.audit_teacher_horizon import summarize
from research.training.train_policy import file_hash


def read_verified(directory):
    manifest=json.loads((directory/"manifest.json").read_text())
    report=json.loads((directory/"report.json").read_text())
    for name,digest in manifest["input_hashes"].items():
        if file_hash(Path(name))!=digest: raise ValueError("Changed diagnostic input")
    for name,digest in report["output_hashes"].items():
        if file_hash(directory/name)!=digest: raise ValueError("Changed diagnostic output")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        for name,digest in manifest["source_hashes"].items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest: raise ValueError("Archived source mismatch")
    return report,[json.loads(l) for l in (directory/"sources.jsonl").read_text().splitlines()]


def export(alignment,horizon,output):
    short,short_rows=read_verified(alignment)
    long,long_rows=read_verified(horizon)
    frozen=json.loads((alignment/"frozen_proposals.json").read_text())
    for report,recomputed in ((short,score(short_rows,frozen)),(long,summarize(long_rows,frozen,"completed"))):
        if not report["complete"] or any(report[k]!=v for k,v in recomputed.items()): raise ValueError("Incomplete/non-reproducing summary")
    table=[]
    for role in ("first","excluded","all"):
        for h in (200,600):
            gains=[]
            for row in long_rows:
                for event in row["events"]:
                    for future in event["futures"]:
                        if role!="all" and future["role"]!=role: continue
                        policy=future["branches"]["policy"]["prefixes"][str(h)]
                        upstream=future["branches"]["upstream_mp"]["prefixes"][str(h)]
                        gains.append([policy["incremental_delay_vehicle_seconds"]-upstream["incremental_delay_vehicle_seconds"],
                            upstream["vehicles_passed"]-policy["vehicles_passed"],policy["upstream_max_wait_s"]-upstream["upstream_max_wait_s"]])
            independent=[statistics.mean(g[i] for g in gains) for i in range(3)]
            if independent!=long["panels"][role][str(h)]["mean_gain"]: raise ValueError("Independent raw mean mismatch")
            table.append(dict(future_panel=role,horizon_s=h/10,paired_future_cases=len(gains),
                mean_delay_saved_vehicle_seconds=independent[0],mean_throughput_gained=independent[1],
                mean_endpoint_max_wait_saved_s=independent[2]))
    output.mkdir(parents=True,exist_ok=False)
    with (output/"teacher_horizon.csv").open("x") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4.4),layout="constrained")
    colors={"first":"#d97706","excluded":"#2563eb"}
    for role in ("first","excluded"):
        selected=[r for r in table if r["future_panel"]==role]
        axes[0].plot([r["horizon_s"] for r in selected],[r["mean_delay_saved_vehicle_seconds"] for r in selected],
                     marker="o",linewidth=2,color=colors[role],label=f"{role.capitalize()} future set")
        parent=long["panels"][role]["600"]["per_parent_mean_delay_saved"]
        axes[1].plot([101,202,303],[parent[str(s)] for s in (101,202,303)],marker="o",color=colors[role],label=role.capitalize())
    for axis in axes:
        axis.axhline(0,color="#475569",linewidth=.9,linestyle="--");axis.spines[["top","right"]].set_visible(False)
        axis.set_ylabel("Mean delay saved (vehicle-seconds)");axis.grid(axis="y",alpha=.18)
    axes[0].set(xlabel="Branch horizon (seconds)",xticks=[20,60],title="Same decisions, different future arrivals")
    axes[0].legend(frameon=False,fontsize=9)
    axes[1].set(xlabel="Policy training replicate",xticks=[101,202,303],title="60-second outcome by replicate")
    fig.suptitle("Upstream teacher substitution: no reliable improvement",fontsize=13)
    fig.supxlabel("7 correlated training-state gates; 8 futures/set; 5/1/1 gates by replicate. Positive = less delay.",fontsize=9)
    fig.savefig(output/"teacher_horizon.png",dpi=180);fig.savefig(output/"teacher_horizon.svg");plt.close(fig)
    text=("# Teacher/horizon diagnostic evidence\n\n"
        "Original teacher screen: failed. Horizon extension: exploratory; cannot promote a policy.\n\n"
        "| Future set | Horizon (s) | Mean branch delay saved (vehicle-seconds) | Mean throughput gain |\n"
        "| --- | ---: | ---: | ---: |\n")
    for row in table:
        text+=f"| {row['future_panel']} | {row['horizon_s']:.0f} | {row['mean_delay_saved_vehicle_seconds']:.6f} | {row['mean_throughput_gained']:.6f} |\n"
    text+=("\nEvery 20-second branch prefix reproduced exactly in the 60-second extension. "
        "The first future set's positive 60-second mean fails on the separate set. "
        "At 60 seconds, all three replicate means are negative in that separate set.\n\n"
        "Units are branch incremental stopped waiting, not full-run mean delay. "
        "Future sets are disjoint RNG keys, not independent intersections/training replicates. "
        "No confidence interval, significance, safety certification, learned-policy gain or novelty is claimed. "
        "The future streams were previously inspected at 20 seconds; this is not fresh confirmation.\n")
    (output/"EVIDENCE_SUMMARY.md").write_text(text)
    manifest=dict(inputs={str((d/n).resolve()):file_hash(d/n) for d in (alignment,horizon) for n in ("manifest.json","report.json","sources.jsonl")},
        exporter_sha256=file_hash(Path(__file__)),publication_ready=False,
        outputs={f.name:file_hash(f) for f in output.iterdir() if f.is_file()})
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return table


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("alignment",type=Path);p.add_argument("horizon",type=Path);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();print(json.dumps(export(args.alignment,args.horizon,args.output),indent=2))
