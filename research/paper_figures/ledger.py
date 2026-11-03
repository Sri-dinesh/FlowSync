"""Ledger transaction diagram and a constructed, non-traffic timing witness."""
from itertools import groupby

from .drawing import Board, BLUE, TEAL, GOLD, GRAY, FILLS


def ledger_mechanism():
    b = Board(6.8)
    counts = b.box(.2,5.0,2.3,1.25,"Delivered counts","Incoming / outgoing\nObserved pressures")
    begin = b.box(3.25,5.0,3.4,1.25,"begin_interval","At an unlocked eligible gate:\nDebt ≥ Q S; otherwise MP\nLatch target + green budget")
    signal = b.box(7.4,5.0,2.4,1.25,"Physical execution","Explicit phase request\nUnchanged signal FSM",tone="teal")
    finish = b.box(7.4,2.65,2.4,1.25,"finish_interval","Validate actual clock\nSame proposal token",tone="teal")
    commit = b.box(3.25,2.65,3.4,1.25,"Commit feedback","Update signed allocation debt\nCredit actual target GREEN\nReject stale or duplicate receipt",tone="teal")
    state = b.box(.2,2.65,2.3,1.25,"Persistent state","Signed debt z\nOne latched batch",tone="gray")
    b.arrow(counts.right,begin.left); b.arrow(begin.right,signal.left)
    b.arrow(signal.bottom,finish.top,label="executed state",at=(8.6,4.48))
    b.arrow(finish.left,commit.right); b.arrow(commit.left,state.right)
    b.arrow(state.top,begin.bottom,via=((1.35,4.45),(4.95,4.45)),label="next interval",at=(3.0,4.45))
    b.text(5,1.88,r"$L=\min\!\left(3Q,\; Q+G\left\lceil \frac{\max(D_{\mathrm{target}},0)}{SG}\right\rceil\right)$",size=11)
    b.text(5,1.22,r"$Q=80$ ticks, $G=20$ ticks, $S=2^{20}$ units per green tick; one tick is 0.1 s.",size=8.3)
    b.text(5,.7,"Clearance freezes allocation debt and batch receipts. New counts cannot revoke a batch.",size=8.1)
    b.text(5,.23,"Zero-count green may retire existing positive debt; a zero packet does not erase memory.",size=8)
    return b


def ledger_witness():
    # Reuse the existing constructed audit, not a native simulator or saved
    # performance panel. It supplies actual policy and physical-clock receipts.
    from research.audits.audit_sumo_service_ledger import sequence
    from research.policies.sumo_service_ledger import SHARE_SCALE
    cases = [("Balanced history","balanced_reversal"),("Skewed history","skewed_reversal")]
    traces = [(label,*sequence(case,"ledger",0)) for label,case in cases]
    a,c = (trace[240] for _,trace,_ in traces)
    if a["before"] != c["before"] or a["counts"] != c["counts"]:
        raise ValueError("The constructed witness no longer has the same current state")
    if [r["proposal"]["phase"] for r in (a,c)] != [1,0] or a["proposal"]["batch"]["budget"] != 160:
        raise ValueError("Constructed ledger decisions differ from the frozen mechanism")
    b = Board(6.9)
    b.text(5,6.55,"Constructed mechanism illustration; no traffic-delay result",size=9,bold=True)
    h1=b.box(.3,4.85,4.25,1.15,"History A: balanced pressures","0–8 s: (0, 0); 8–24 s: (1, 1)\nBoth phases have positive pressure after 8 s")
    h2=b.box(5.45,4.85,4.25,1.15,"History B: skewed pressures","0–8 s: (0, 0); 8–24 s: (9, 1)\nBoth phases have positive pressure after 8 s")
    common=b.box(2.0,3.2,6.0,1.05,"Same decision state at t = 24 s","Pressures (9, 1); NS GREEN age 24 s; MP prefers NS",tone="gray")
    b.arrow(h1.bottom,(3.5,4.25),via=((2.425,4.5),(3.5,4.5)))
    b.arrow(h2.bottom,(6.5,4.25),via=((7.575,4.5),(6.5,4.5)))
    x0,scale=2.0,7.7/44
    summary=[]
    for y,(label,trace,state) in zip((2.1,1.25),traces):
        b.text(.2,y+.28,"A" if label.startswith("Balanced") else "B",ha="left",bold=True)
        for (phase,stage),members in groupby(enumerate(trace),key=lambda item:(item[1]["receipt"]["executed"]["phase"],item[1]["receipt"]["executed"]["stage"])):
            members=list(members); start=members[0][0]/10; duration=len(members)/10
            green=stage=="green"
            text=("NS GREEN" if phase==0 else "EW GREEN") if green else "Y" if stage=="yellow" else ""
            color=BLUE if phase==0 else TEAL
            b.band(x0+start*scale,y,duration*scale,.56,text,color=color,
                fill=None if green else FILLS["gold"] if stage=="yellow" else FILLS["gray"],
                hatch="///" if green and phase==1 else None)
        gate=trace[240]["proposal"]
        summary.append(dict(case=trace[0]["case"],debt_ew_s=-gate["debt_ns_units"]/(10*SHARE_SCALE),
            phase=gate["phase"],budget_green_s=gate["batch"]["budget"]/10))
    for t in (0,8,24,28,44):
        b.text(x0+t*scale,.92,str(t),size=8)
    b.text(5,.52,"A: EW debt 8 s → EW batch 16 s. B: EW debt ≈1.6 s → NS batch 8 s.",size=8.2)
    b.text(5,.15,"Time in seconds. After the gate, NS-only pressure illustrates the cost of an irrevocable EW batch.",size=7.9)
    b.evidence=dict(kind="constructed_controller_and_clock_illustration",controller_intervals=880,
        native_traffic_runs=0,training_runs=0,performance_evaluated=False,gate_s=24,decisions=summary)
    return b
