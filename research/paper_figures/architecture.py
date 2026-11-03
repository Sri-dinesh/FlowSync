"""Separate execution paths, causal control boundary and evidence ownership."""
from .drawing import Board, GRAY


def system_architecture():
    b = Board(7.8)
    lanes = [
        (5.95,"(a) Interactive application",[
            ("Next.js client","Pages + live state"),("FastAPI services","HTTP + WebSockets"),
            ("Application runtime","Custom simulation"),("Persistence","Models + history")],"blue"),
        (4.15,"(b) Audited custom-simulator research",[
            ("Scenario + simulator","Demand + dynamics"),("Delivered sensing","Synthetic faults"),
            ("Observed policy","Checkpoint or classical"),("Execution + audit","FSM, metrics, traces")],"teal"),
        (2.35,"(c) Independent SUMO research",[
            ("SUMO + TraCI","Straight-only topology"),("Delivered counts","Clean or synthetic faults"),
            ("Two-phase control","Ledger or classical"),("Execution + audit","Lamps + accounting")],"blue"),
        (.55,"(d) Experimental camera workflow",[
            ("Video + source clock","Recorded observations"),("Detection + tracks","Centroid association"),
            ("Geometry + events","Counts + crossings"),("Saved telemetry","No physical actuation")],"gray"),
    ]
    for y,label,nodes,tone in lanes:
        b.panel(.08,y,9.84,1.63,label)
        boxes = [b.box(.25+2.48*i,y+.18,2.08,.92,title,body,tone=tone) for i,(title,body) in enumerate(nodes)]
        for a,c in zip(boxes,boxes[1:]): b.arrow(a.right,c.left)
        if y==5.95:
            b.arrow(boxes[0].top,boxes[-1].top,via=((1.29,7.15),(8.73,7.15)),
                label="Next.js server routes / Prisma",at=(5.0,7.15),dashed=True)
    b.text(5,.17,"Separate runtimes; shared project ownership does not imply numerical equivalence.",size=8)
    return b


def control_boundary():
    b = Board(6.7)
    env = b.box(.25,5.05,2.05,1.1,"Custom simulator","Scenario + demand")
    sensed = b.box(2.8,5.05,2.05,1.1,"Delivered packet","Misses / delay / drops")
    encoded = b.box(5.35,5.05,2.05,1.1,"Observed features","Context + action mask")
    policy = b.box(7.9,5.05,1.85,1.1,"Policy proposal","Checkpoint-explicit")
    fallback = b.box(7.9,3.0,1.85,1.1,"Fallback","Optional supervisor",tone="gold",dashed=True)
    shield = b.box(5.35,3.0,2.05,1.1,"Additional shield","Optional intervention",tone="gold",dashed=True)
    physical = b.box(2.8,3.0,2.05,1.1,"Physical signal FSM","Min green + clearance",tone="teal")
    lamps = b.box(.25,3.0,2.05,1.1,"Executed lamps","Actual signal state",tone="teal")
    for a,c in zip((env,sensed,encoded),(sensed,encoded,policy)): b.arrow(a.right,c.left)
    b.arrow(policy.bottom,fallback.top)
    for a,c in zip((fallback,shield,physical),(shield,physical,lamps)): b.arrow(a.left,c.right)
    b.arrow(lamps.top,env.bottom,label="applied control",at=(1.28,4.58))
    truth = b.box(.25,.7,4.2,1.1,"Truth-based evaluation","Waiting, throughput, retained backlog",tone="gray")
    audit = b.box(5.05,.7,4.7,1.1,"Independent executed-signal audit","Sample lamps; save events and provenance",tone="gray")
    b.arrow((.25,5.6),truth.left,via=((.08,5.6),(.08,1.25)),dashed=True,color=GRAY)
    b.arrow(lamps.bottom,audit.top,via=((1.28,2.35),(7.4,2.35)),dashed=True,color=GRAY)
    b.text(5,.22,"Evaluation truth never substitutes for corrupted controller inputs.",size=8.3,bold=True)
    return b


def evidence_workflow():
    b = Board(5.8)
    inputs = b.box(.25,4.0,2.5,1.2,"Frozen inputs","Sources, config, seeds\nCheckpoint + runtime")
    run = b.box(3.75,4.0,2.5,1.2,"Executed episode","Delivered packets\nProposals + lamps")
    bundle = b.box(7.25,4.0,2.5,1.2,"Saved evidence","Traces + checkpoint\nEpisode records")
    manifest = b.box(7.25,1.55,2.5,1.2,"Provenance bundle","Hashes + manifest\nArchived sources",tone="teal")
    verify = b.box(3.75,1.55,2.5,1.2,"Saved-data verification","Sensing + actions\nSignals + waiting",tone="teal")
    export = b.box(.25,1.55,2.5,1.2,"Paper assets","Versioned exports\nUnits + claim scope",tone="teal")
    b.arrow(inputs.right,run.left); b.arrow(run.right,bundle.left)
    b.arrow(bundle.bottom,manifest.top)
    b.arrow(manifest.left,verify.right); b.arrow(verify.left,export.right)
    b.text(5,.65,"Verification reconstructs recorded evidence; it does not independently resimulate traffic.",size=8.2)
    b.text(5,.25,"Local ignored artifacts need separate distribution; a source clone is not the complete dataset.",size=8)
    return b
