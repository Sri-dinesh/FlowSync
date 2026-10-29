"""Export verified sensing/control evidence without combining their units."""
import argparse
import csv
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research.pilots.run_count_restoration_pilot import verify,sha,write


def csv_file(path,rows):
    with path.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def export(source,output):
    audit=verify(source)
    report=json.loads((source/"report.json").read_text())
    if report["control"] is None: raise ValueError("Control evidence was not collected.")
    rows=[json.loads(line) for line in (source/"control.jsonl").read_text().splitlines()]
    output.mkdir(parents=True,exist_ok=False)
    reconstruction=[dict(method=name,**report["reconstruction"]["metrics"][name]) for name in ("raw","ema","101","202","303")]
    csv_file(output/"count_metrics.csv",reconstruction)
    csv_file(output/"control_cases.csv",rows)
    def group(actor,arm,fault):
        return [r for r in rows if (r["actor"]!="pressure" if actor=="d3qn" else r["actor"]==actor)
                and (r["arm"].startswith("restored_") if arm=="restored" and actor=="pressure" else r["arm"]==arm)
                and (fault=="all" or r["fault"]==fault)]
    summary=[]
    for actor,arms in (("d3qn",("raw","ema","restored","uq")),("pressure",("raw","ema","restored","bare"))):
        for arm in arms:
            for fault in ("clean","validation_mixed","all"):
                subset=group(actor,arm,fault)
                summary.append(dict(actor=actor,method=arm,fault=fault,rows=len(subset),
                                    **{key:statistics.mean(r[key] for r in subset) for key in ("delay","p95","passed")}))
    csv_file(output/"control_summary.csv",summary)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(1,2,figsize=(12,5.8),layout="constrained")
    axes[0].bar(["Raw","EMA","Model 101","Model 202","Model 303"],[r["mae"] for r in reconstruction],
                color=["#7b8794","#d69e2e","#1768ac","#4789c0","#77aad4"])
    axes[0].set(title="A. Count reconstruction on excluded sources",ylabel="MAE (counts per movement)",ylim=(0,max(.1,1.25*max(r["mae"] for r in reconstruction))))
    for i,row in enumerate(reconstruction): axes[0].text(i,row["mae"]+.0015,f"{row['mae']:.4f}",ha="center",fontsize=9)
    methods=[("d3qn","raw","D3QN raw"),("d3qn","ema","D3QN EMA"),("d3qn","restored","D3QN restored"),
             ("pressure","raw","MP shield"),("pressure","restored","MP restored"),("pressure","bare","MP bare")]
    values=[statistics.mean(r["delay"] for r in group(actor,arm,"validation_mixed")) for actor,arm,_ in methods]
    axes[1].bar([name for _,_,name in methods],values,color=["#7b8794","#d69e2e","#1768ac","#8e5ea2","#b288c0","#565d69"])
    axes[1].set(title="B. Traffic control with mixed sensing faults",ylabel="Mean stopped wait per arrived vehicle (s)",ylim=(0,max(14,1.2*max(values))))
    axes[1].tick_params(axis="x",rotation=25)
    for i,value in enumerate(values): axes[1].text(i,value+.12,f"{value:.3f}",ha="center",fontsize=9)
    for ax in axes: ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
    status="passes" if report["continue_to_expanded_validation"] else "fails"
    fig.suptitle(f"Sensing and control outcomes: frozen control screen {status}",fontsize=13)
    fig.supxlabel("A: 12 training-only probe sources; models share those observations. B: 3 development traffic realizations, with policy/restorer pairs.\nDifferent panels and units; descriptive means, no confidence intervals. MP restored receives the same learned estimators.",fontsize=9)
    fig.savefig(output/"sensing_and_control.png",dpi=220)
    fig.savefig(output/"sensing_and_control.svg")
    plt.close(fig)
    implementation=Path(__file__)
    (output/"exporter_source.py").write_bytes(implementation.read_bytes())
    write(output/"manifest.json",dict(input_directory=str(source.resolve()),verification=audit,
        input_sha256={name:sha(source/name) for name in ("manifest.json","report.json","reconstruction.json","control.jsonl","frozen_models.json")},
        output_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()},
        publication_ready=False,scope="Exports of existing verified observations; no new traffic runs, statistical significance or model promotion."))
    return dict(complete=True,output=str(output),control_screen_passed=report["continue_to_expanded_validation"],publication_ready=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(export(args.source,args.output),indent=2))


if __name__=="__main__": main()
