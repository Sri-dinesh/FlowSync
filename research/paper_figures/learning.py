"""Versioned numeric observations, dueling network and corrected research replay."""
from .drawing import Board, BLUE, TEAL, GOLD, GRAY, FILLS


def observation_schemas():
    b = Board(5.9)
    x0,scale = 1.7,8.0/64
    rows = [
        (4.6,"v6: 28",[(28,"Base features",BLUE)]),
        (3.5,"v7: 36",[(28,"Base features",BLUE),(4,"O",TEAL),(4,"T",GOLD)]),
        (2.4,"v8: 64",[(28,"Base features",BLUE),(4,"O",TEAL),(4,"T",GOLD),
            (12,"Lag 10\n12 counts",TEAL),(12,"Lag 30\n12 counts",TEAL),(4,"F",GRAY)]),
        (1.3,"v9: 48",[(28,"Base features",BLUE),(4,"O",TEAL),(4,"T",GOLD),(12,"Upstream\n12 counts",TEAL)]),
    ]
    for y,label,parts in rows:
        b.text(.25,y+.36,label,ha="left",bold=True)
        x = x0
        for width,text,color in parts:
            b.band(x,y,width*scale,.72,text,color=color)
            x += width*scale
    for index in (0,28,36,48,60,64): b.text(x0+index*scale,5.55,str(index),size=8)
    b.text(5,5.88,"Feature indices; one schema per checkpoint; temporal lags are 10 Hz ticks",size=8.3)
    b.text(5,.74,"O: four outgoing counts. T: four phase-service timers. F: age and availability flags.",size=8.0)
    b.text(5,.28,"Matched controls zero only the added temporal 28 or spatial 12 inputs.",size=8.1)
    return b


def dueling_network():
    b = Board(6.5)
    state = b.box(.2,3.0,1.65,1.45,"Numeric state","28 / 36 / 48 / 64\nVersion-specific")
    shared = b.box(2.3,3.0,2.05,1.45,"Shared features","Linear 256 + LN\nReLU; repeat once")
    value = b.box(4.85,4.35,1.95,1.25,"Value stream","128 + ReLU\nScalar V(s)")
    advantage = b.box(4.85,1.9,1.95,1.25,"Advantage stream","128 + ReLU\nFour A(s,a)")
    combine = b.box(7.35,3.0,2.4,1.45,"Dueling combination","Center advantages\nover valid actions",tone="teal")
    mask = b.box(7.35,5.25,2.4,.9,"Valid-action mask","M(s)",tone="gray")
    action = b.box(7.35,.6,2.4,1.05,"Masked argmax","Select a valid phase",tone="teal")
    b.arrow(state.right,shared.left)
    b.arrow(shared.right,value.left,via=((4.6,3.725),(4.6,4.975)))
    b.arrow(shared.right,advantage.left,via=((4.6,3.725),(4.6,2.525)))
    b.arrow(value.right,(7.35,4.02),via=((7.05,4.975),(7.05,4.02)))
    b.arrow(advantage.right,(7.35,3.43),via=((7.05,2.525),(7.05,3.43)))
    b.arrow(mask.bottom,combine.top)
    b.arrow(combine.bottom,action.top)
    b.text(3.55,.95,r"$Q(s,a)=V(s)+A(s,a)-\mathrm{mean}_{b\in M(s)} A(s,b)$",size=9.0)
    b.text(4.5,.25,"LN: LayerNorm. Four action outputs belong to the custom simulator, not two-phase SUMO.",size=8.0)
    return b


def research_training():
    b = Board(7.0)
    teacher = b.box(.2,5.2,2.05,1.15,"Teacher experience","Demonstration flags\nOptional warm start")
    online = b.box(2.7,5.2,2.05,1.15,"Online collection","Completed decisions\nDuration + v5 reward")
    replay = b.box(5.2,5.2,2.05,1.15,"Prioritized replay","TD-error priorities\nDemo + online data")
    batch = b.box(7.7,5.2,2.05,1.15,"Minibatch","Importance weights\nValidity masks")
    target = b.box(7.7,3.0,2.05,1.15,"Double-DQN target","Online selects action\nTarget evaluates Q")
    loss = b.box(5.2,3.0,2.05,1.15,"Training loss","Weighted Smooth L1\n+ eligible demo margin")
    adam = b.box(2.7,3.0,2.05,1.15,"Gradient update","Adam optimizer\nL2 gradient clipping")
    weights = b.box(.2,3.0,2.05,1.15,"Online Q weights","Periodic copy\nto target Q")
    checkpoint = b.box(3.0,.7,4.0,1.15,"Validation + checkpoint identity","Record configuration and source\nSelect only on declared development data",tone="teal")
    b.arrow(teacher.top,replay.top,via=((1.225,6.7),(6.225,6.7)))
    b.arrow(online.right,replay.left); b.arrow(replay.right,batch.left)
    b.arrow(batch.bottom,target.top)
    b.arrow(target.left,loss.right); b.arrow(loss.left,adam.right); b.arrow(adam.left,weights.right)
    b.arrow(weights.top,online.bottom,via=((1.225,4.45),(3.725,4.45)))
    b.arrow(weights.bottom,checkpoint.left,via=((1.225,1.275),))
    b.text(5,2.3,r"$y=R_{\mathrm{macro}}+(1-\mathrm{done})\,\gamma^{\Delta t/\Delta t_{\mathrm{ref}}}\,Q_{\mathrm{target}}(s',a^*)$",size=9)
    b.text(5,.2,"Corrected research replay stores proposed actions and drops the final incomplete macro-action.",size=8)
    return b
