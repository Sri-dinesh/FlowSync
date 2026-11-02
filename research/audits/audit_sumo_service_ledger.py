"""Bounded deterministic controller/Signal mechanics; no native traffic or training."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from research.audits.sumo_branch_feasibility import Signal
from research.policies.sumo_classical import Clock, Counts
from research.policies.sumo_service_ledger import (
    DECISION_TICKS, MAX_BATCH_TICKS, QUANTUM_TICKS, RULES, SHARE_SCALE, VERSION,
    Rule, ServiceLedgerPolicy, _budget_ticks,
)

ROOT = Path(__file__).resolve().parents[2]
DESIGN = "research/manifests/service_ledger_design.json"
SOURCES = (
    DESIGN, "research/audits/audit_sumo_service_ledger.py",
    "research/audits/sumo_branch_feasibility.py", "research/policies/sumo_classical.py",
    "research/policies/sumo_service_ledger.py", "research/experiments/sumo_service_ledger.py",
    "server/tests/test_sumo_service_ledger.py",
)
SCHEMA = "service_ledger_mechanics_v1"


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _data(value):
    return json.loads(json.dumps(asdict(value), sort_keys=True, allow_nan=False))


def budget_certificate():
    """Check every integer-ceiling region's extreme admissible selected debts.

    Within each region the budget is constant and x-L*S increases with x.
    These cases support the stated induction, not a temporal-logic proof.
    """
    q, g, scale = QUANTUM_TICKS, DECISION_TICKS, SHARE_SCALE
    if q % g or not 0 < g <= q:
        raise ValueError("The stated debt induction requires aligned positive quanta")
    cases = {-q*scale+1, -1, 0}
    for k in range(1, 2*q//g+1):
        cases.update(((k-1)*g*scale+1, k*g*scale))
    checked = []
    for debt in sorted(cases):
        budget = _budget_ticks(debt, Rule())
        uncapped = q + g*((max(0,debt)+scale*g-1)//(scale*g))
        lower = debt-budget*scale
        if budget != uncapped or budget > MAX_BATCH_TICKS or lower < -2*q*scale:
            raise ValueError("Batch arithmetic contradicts the primary debt induction")
        checked.append(dict(selected_debt_units=debt, budget_ticks=budget,
                            minimum_possible_end_debt_units=lower))
    # Check the physical constants against the unchanged execution implementation.
    signal = Signal(age=q-1)
    signal.request(1)
    if signal.stage != "green":
        raise ValueError("Physical minimum green changed")
    signal.advance(); signal.request(1)
    stages = []
    while signal.stage != "green":
        stages.append(signal.stage); signal.advance()
        if len(stages) > 100:
            raise ValueError("Unbounded physical clearance")
    if stages != ["yellow"]*30+["red"]*10:
        raise ValueError("Physical clearance differs from the declared contract")
    return checked


def sequence(case, mode, phase):
    policy = ServiceLedgerPolicy(RULES[mode])
    signal = Signal(phase=phase, pending=phase)
    rows = []
    for tick in range(440):
        if tick < 80:
            ns, ew = 0, 0
        elif tick < 240:
            ns, ew = (9,1) if case == "skewed_reversal" else (1,1)
        elif tick == 240:
            ns, ew = 9, 1
        else:
            ns, ew = ((0,0) if case == "balanced_empty" else
                      (0,100) if case == "balanced_entitlement" else (100,0))
        if phase:
            ns, ew = ew, ns
        counts = Counts((ns,0,ew,0),(0,0,0,0),(ns,0,ew,0))
        before = Clock(signal.phase,signal.stage,signal.age)
        proposal = policy.begin_interval(counts,before)
        if tick % DECISION_TICKS == 0:
            signal.request(proposal.phase)
        receipt = policy.finish_interval(proposal,Clock(signal.phase,signal.stage,signal.age))
        rows.append(dict(case=case,mode=mode,initial_phase=phase,counts=counts.to_dict(),
                         before=_data(before),proposal=_data(proposal),receipt=_data(receipt)))
        signal.advance()
    return rows, policy.snapshot()


def run_checks():
    design = json.loads((ROOT/DESIGN).read_text())
    if design["version"] != VERSION or any(design[k] is not False for k in
            ("algorithmic_novelty_established","traffic_benefit_established","publication_ready","automatic_promotion")):
        raise ValueError("Design version/scope changed; review the candidate before mechanics")
    values = dict(dt_s=0.1,decision_ticks=DECISION_TICKS,quantum_ticks=QUANTUM_TICKS,
                  share_scale=SHARE_SCALE,maximum_batch_ticks=MAX_BATCH_TICKS)
    if any(type(design["parameters"][k]["value"]) is not type(value)
           or design["parameters"][k]["value"] != value for k,value in values.items()):
        raise ValueError("Declared design parameters differ from the implementation")
    certificate, traces, summaries = budget_certificate(), [], []
    for mode in RULES:
        cases = ["balanced_reversal","skewed_reversal"]
        if mode == "ledger":
            cases += ["balanced_empty","balanced_entitlement"]
        for phase in (0,1):
            for case in cases:
                rows, state = sequence(case,mode,phase)
                at_gate = rows[240]["proposal"]
                completions = [r["receipt"]["completed"] for r in rows if r["receipt"]["completed"]]
                summaries.append(dict(case=case,mode=mode,initial_phase=phase,
                    decision_at_240=at_gate, last_receipt=rows[-1]["receipt"],
                    completed_batches=len(completions),final_state=state))
                if mode == "ledger" and case != "skewed_reversal":
                    if (at_gate["phase"] != 1-phase or at_gate["reference"] != phase
                            or at_gate["batch"]["budget"] != 160
                            or rows[-1]["receipt"]["completed"]["received"] != 160
                            or sum(r["receipt"]["credited_batch"] == at_gate["batch"]["identifier"] for r in rows) != 160):
                        raise ValueError("Constructive batch/actual-service witness failed")
                    if any(r["receipt"]["credited_batch"] is not None for r in rows[240:280]):
                        raise ValueError("Clearance was falsely credited as green")
                if mode == "ledger" and case == "skewed_reversal" and at_gate["phase"] != phase:
                    raise ValueError("Distinct pressure histories lost the decision contrast")
                traces.extend(rows)
    report = dict(schema_version=SCHEMA,controller_version=VERSION,complete=True,
        scientific_panel_complete=False,input_sequences=len(summaries),controller_intervals=len(traces),
        native_traffic_runs=0,training_runs=0,performance_evaluated=False,
        arithmetic_extreme_cases=certificate,sequences=summaries,
        scope="Constructed delivered-packet/physical-clock sequences. Green receipts are opportunities, not vehicle departures or traffic-delay evidence.",
        allocation_bound="Conditional 2Q*S bound for debt-priority rules; arithmetic regions and mechanical cases checked, not a formal all-state safety proof.",
        algorithmic_novelty_established=False,traffic_benefit_established=False,publication_ready=False,automatic_promotion=False)
    return report,traces


def create(output):
    output = Path(output).resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Preserve existing mechanics evidence; use a new output")
    if any((p/"manifest.json").exists() or (p/"report.json").exists() for p in output.parents):
        raise ValueError("Do not write inside an existing evidence collection")
    source_hashes = {n:_hash(ROOT/n) for n in SOURCES}
    report, rows = run_checks()
    output.mkdir(parents=True,exist_ok=False)
    (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (output/"trace.jsonl.gz").open("xb") as raw:
        with gzip.GzipFile(filename="",fileobj=raw,mode="wb",mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row,sort_keys=True,allow_nan=False)+"\n").encode())
    with zipfile.ZipFile(output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCES:
            archive.write(ROOT/name,name)
    if any(_hash(ROOT/n) != value for n,value in source_hashes.items()):
        raise ValueError("Source changed during mechanics; preserve the incomplete attempt")
    manifest = dict(schema_version=SCHEMA,source_sha256=source_hashes,
        git_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip()),
        python_version=sys.version,output_sha256={p.name:_hash(p) for p in output.iterdir()})
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return report


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory/"manifest.json").read_text())
    if manifest["schema_version"] != SCHEMA or set(manifest["source_sha256"]) != set(SOURCES):
        raise ValueError("Unknown mechanics schema or source coverage")
    if set(manifest["output_sha256"]) != {"report.json","trace.jsonl.gz","source_snapshot.zip"}:
        raise ValueError("Incomplete mechanics output coverage")
    if any(_hash(directory/n) != h for n,h in manifest["output_sha256"].items()):
        raise ValueError("Mechanics output hash changed")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as archive:
        if len(archive.namelist()) != len(SOURCES) or set(archive.namelist()) != set(SOURCES):
            raise ValueError("Incomplete mechanics source archive")
        for name,h in manifest["source_sha256"].items():
            if _hash(ROOT/name) != h or hashlib.sha256(archive.read(name)).hexdigest() != h:
                raise ValueError("Mechanics sources changed; use their original archive")
    expected, rows = run_checks()
    actual = json.loads((directory/"report.json").read_text())
    if json.dumps(actual,sort_keys=True,allow_nan=False) != json.dumps(expected,sort_keys=True,allow_nan=False):
        raise ValueError("Mechanics report does not reconstruct")
    with gzip.open(directory/"trace.jsonl.gz","rt") as stream:
        saved = [json.loads(line) for line in stream]
    if json.dumps(saved,sort_keys=True,allow_nan=False) != json.dumps(rows,sort_keys=True,allow_nan=False):
        raise ValueError("Mechanics interval trace does not reconstruct")
    return dict(verified=True,input_sequences=expected["input_sequences"],
        controller_intervals=expected["controller_intervals"],native_traffic_runs=0,
        scientific_panel_complete=False,performance_evaluated=False,algorithmic_novelty_established=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output",type=Path); mode.add_argument("--verify",type=Path)
    args = parser.parse_args()
    result = verify(args.verify) if args.verify else create(args.output)
    keys = ("complete","verified","input_sequences","controller_intervals","native_traffic_runs",
            "scientific_panel_complete","performance_evaluated","algorithmic_novelty_established")
    print(json.dumps({k:result[k] for k in keys if k in result},indent=2))


if __name__ == "__main__":
    main()
