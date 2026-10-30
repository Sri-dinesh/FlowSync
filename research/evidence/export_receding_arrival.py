"""Post-hoc tables and chosen-service witnesses; no new control or simulation.

Hash/summary checks here complement the panel's separate full replay verifier.
Future positions label observed service only; they never select a control action.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from research.analysis.arrival_reference_gap import service_witness
from research.audits.audit_arrival_reference_gap import csv_file
from research.pilots.run_receding_arrival_panel import PLAN, METHODS, PRIMARY, collect_rows, comparison
from research.pilots.run_arrival_window_panel import means, sha, write


def service_events(raw):
    """Compare the proxy's 2 s option with actual contiguous executed green."""
    frames, events = raw["frames"], []
    if any(frame["step"] != step for step, frame in enumerate(frames)):
        raise ValueError("Service evidence needs contiguous frames")
    for gate, frame in enumerate(frames):
        if not frame["policy"]["gate"] or frame["policy"]["reason"] != "supported_extension":
            continue
        phase, contiguous = frame["before"]["phase"], 0
        for future in frames[gate:gate+20]:
            if future["after"]["phase"] != phase or future["after"]["color"] != "GREEN":
                break
            contiguous += 1
        observed_ticks = min(20, len(frames)-gate)
        hold = "cut_short" if contiguous < observed_ticks else "full_option" if contiguous == 20 else "censored"
        for identifier in frame["policy"]["used_ids"]:
            witness = service_witness(frames, gate, identifier)
            upper = witness["crossing_after_s_upper"]
            events.append(dict(case_id=raw["case"]["case_id"], method=raw["method"], **witness,
                contiguous_green_ticks=contiguous, green_hold=hold,
                crossed_after_current_green=upper is not None and upper > contiguous*.1+1e-9))
    return events


def support_summary(events):
    return dict(support_events=len(events),
        distinct_case_track_pairs=len({(e["case_id"], e["track_id"]) for e in events}),
        service_status=dict(Counter(e["status"] for e in events)),
        green_hold=dict(Counter(e["green_hold"] for e in events)),
        crossed_after_current_green=sum(e["crossed_after_current_green"] for e in events))


def export(source, output):
    manifest = json.loads((source/"manifest.json").read_text())
    report = json.loads((source/"report.json").read_text())
    if not report["complete"] or manifest["plan"] != json.loads(json.dumps(PLAN)):
        raise ValueError("Export requires a complete frozen receding panel")
    files = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file() and p != source/"report.json"}
    if files != set(report["output_sha256"]) or any(sha(source/n) != h for n,h in report["output_sha256"].items()):
        raise ValueError("Receding source output hashes/coverage changed")
    rows = collect_rows(source)
    if rows != report["rows"] or comparison(rows) != report["comparison"]:
        raise ValueError("Receding raw summary/screen reconstruction differs")
    output.mkdir(parents=True, exist_ok=False)
    cases = {c["case_id"]: c for c in manifest["cases"]}
    all_rows = [dict(case_id=r["case_id"], method=r["method"], traffic_seed=cases[r["case_id"]]["seed"],
        scenario=cases[r["case_id"]]["scenario"]["scenario_id"], fault=cases[r["case_id"]]["fault"]["name"],
        **{k:r[k] for k in ("delay", "p95", "passed", "arrivals", "samples", "violations", "policy_gates", "extension_proposals")},
        shield_override_ticks=r["shield"]["total_overrides"], raw_file=r["raw_file"], raw_sha256=r["sha256"]) for r in rows]
    csv_file(output/"all_cases.csv", all_rows)
    csv_file(output/"summary.csv", [dict(method=method, **report["comparison"]["means"][method]) for method in METHODS])
    faults = sorted({r["fault"] for r in all_rows})
    csv_file(output/"condition_summary.csv", [dict(method=method, fault=fault,
        **means([r for r in all_rows if r["method"] == method and r["fault"] == fault])) for method in METHODS for fault in faults])
    primary = {r["case_id"]:r for r in rows if r["method"] == PRIMARY}
    paired = [dict(case_id=r["case_id"], reference=r["method"], primary_delay=primary[r["case_id"]]["delay"], reference_delay=r["delay"],
        delay_saved_s=r["delay"]-primary[r["case_id"]]["delay"],
        p95_saved_s=r["p95"]-primary[r["case_id"]]["p95"], passed_gained=primary[r["case_id"]]["passed"]-r["passed"])
        for r in rows if r["method"] != PRIMARY]
    csv_file(output/"primary_paired_cases.csv", paired)
    events = []
    for row in rows:
        if row["method"] not in (PRIMARY, "window_2s"):
            continue
        with gzip.open(source/row["raw_file"], "rt") as stream:
            events.extend(service_events(json.load(stream)))
    csv_file(output/"chosen_service_events.csv", events)
    support = {method:support_summary([e for e in events if e["method"] == method]) for method in ("window_2s", PRIMARY)}
    diagnosis = dict(complete=True, runs=len(rows), condition_rows=len(METHODS)*len(faults), paired_rows=len(paired),
        screen_passed=report["comparison"]["continue_to_fresh_development"], support=support,
        scope="Post-hoc chosen-trajectory witnesses, not counterfactual benefits, independent track replicates or a new selection rule. Repeated support for a track is counted explicitly. A shortened green can still deliver service; causation is not established.",
        publication_ready=False, automatic_promotion=False)
    write(output/"diagnosis.json", diagnosis)
    (output/"exporter_source.py").write_bytes(Path(__file__).read_bytes())
    write(output/"manifest.json", dict(input_directory=str(source.resolve()),
        input_sha256={n:sha(source/n) for n in ("manifest.json", "report.json")},
        output_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()},
        scope="Sealed output hashes, raw summaries/screen and post-hoc service witnesses. Full observation/decision/signal replay is the separate panel verifier. No new traffic simulation."))
    return diagnosis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
