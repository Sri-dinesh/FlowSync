"""Runtime-specific physical transitions and finite-horizon study design."""
from .drawing import Board, BLUE, TEAL, GOLD, GRAY, FILLS


def physical_signal():
    b = Board(5.3)
    green = b.box(.2,3.65,2.05,1.0,"GREEN p","Minimum 8 s",tone="teal")
    yellow = b.box(2.7,3.65,2.05,1.0,"YELLOW p","Exactly 3 s",tone="gold")
    red = b.box(5.2,3.65,2.05,1.0,"ALL-RED","Exactly 1 s",tone="gray")
    next_green = b.box(7.7,3.65,2.05,1.0,"GREEN q","Committed target",tone="teal")
    b.arrow(green.right,yellow.left); b.arrow(yellow.right,red.left); b.arrow(red.right,next_green.left)
    b.text(5,5.05,"Independent SUMO execution contract",size=9,bold=True)
    b.text(5,3.05,"Example: request q at t = 8 s after green p starts at t = 0.",size=8.2)
    x,scale = 1.55,.5
    b.text(.7,2.19,"NS",bold=True); b.text(.7,1.29,"EW",bold=True)
    b.band(x,1.9,8*scale,.58,"GREEN",color=TEAL)
    b.band(x+8*scale,1.9,3*scale,.58,"Y",fill=FILLS["gold"])
    b.band(x+11*scale,1.9,5*scale,.58,"RED",fill=FILLS["gray"])
    b.band(x,1.0,12*scale,.58,"RED",fill=FILLS["gray"])
    b.band(x+12*scale,1.0,4*scale,.58,"GREEN",color=TEAL)
    for t in (0,8,11,12,16):
        xpos=x+t*scale
        b.ax.plot([xpos,xpos],[.85,2.6],color="#BBC1C7",linewidth=.6,linestyle=":",zorder=0)
        b.text(xpos,.61,str(t),size=8)
    b.text(5,.15,"Time (s). Illustrative transition; these numerical timings are not universal across runtimes.",size=8)
    return b


def study_design():
    b = Board(7.1)
    b.text(5,6.78,"Deferred scientific design; not collected performance evidence",size=9,bold=True)
    families = [("Balanced","NS/EW rates 0.2 / 0.2"),("NS dominant","NS/EW rates 0.3 / 0.1"),("EW dominant","NS/EW rates 0.1 / 0.3")]
    boxes=[]
    for i,(name,rates) in enumerate(families):
        boxes.append(b.box(.3+3.35*i,5.0,2.7,1.15,name,rates+"\nTwo traffic seeds"))
    b.text(5,4.48,"Within every seed: two initial phases × two sensing conditions × six controllers",size=8.5)
    names=["Ledger","Pressure\nbudget","Pressure\nbatch","Debt\nbatch","Original\nMP","Watchdog"]
    for row,(label,y) in enumerate((("Clean",2.95),("Mixed",1.85))):
        b.text(.12,y+.37,label,size=8,ha="left",bold=True)
        for col,name in enumerate(names):
            b.band(1.15+col*1.43,y,1.33,.75,name,color=BLUE if row==0 else TEAL)
    b.text(5,1.17,"6 traffic seeds × 24 paired episodes = 144 runs; each run lasts 360 s.",size=8.4)
    b.text(5,.68,"180 s prefix is secondary; 360 s is primary. Endpoints overlap.",size=8.2)
    b.text(5,.2,"Average starts within seed. Resample traffic seeds within family, not ticks or controller cells.",size=8)
    return b
