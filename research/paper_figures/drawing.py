"""Small Matplotlib drawing vocabulary and checks for static paper figures."""
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.path import Path

INK = "#182B3A"
BLUE = "#225E87"
TEAL = "#286B60"
GOLD = "#986A15"
GRAY = "#66717B"
FILLS = dict(blue="#EDF4F9", teal="#ECF5F1", gold="#FBF3DF", gray="#F3F4F5", white="#FFFFFF")


def style():
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":8.5,
        "mathtext.fontset":"dejavusans", "text.color":INK, "axes.labelcolor":INK,
        "pdf.fonttype":42, "ps.fonttype":42, "svg.fonttype":"none",
        "svg.hashsalt":"flowsync-methodology-figures-v1", "savefig.facecolor":"white"})


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self): return self.x, self.y+self.h/2
    @property
    def right(self): return self.x+self.w, self.y+self.h/2
    @property
    def top(self): return self.x+self.w/2, self.y+self.h
    @property
    def bottom(self): return self.x+self.w/2, self.y


class Board:
    """Coordinates use a ten-unit page width; physical text sizes stay fixed."""
    def __init__(self, height=6.4):
        style()
        self.fig, self.ax = plt.subplots(figsize=(7.16, 7.16*height/10))
        self.fig.subplots_adjust(left=.015, right=.985, bottom=.015, top=.985)
        self.ax.set(xlim=(0,10), ylim=(0,height)); self.ax.axis("off")
        self.height, self.labels, self.contained, self.boxes = height, [], [], []
        self.evidence = {}

    def text(self, x, y, text, *, size=8.5, color=INK, ha="center", va="center", bold=False, **kwargs):
        artist = self.ax.text(x, y, text, fontsize=size, color=color, ha=ha, va=va,
            fontweight="bold" if bold else "normal", linespacing=1.28, **kwargs)
        self.labels.append(artist)
        return artist

    def box(self, x, y, w, h, title, body="", *, tone="blue", dashed=False):
        rect = Box(x,y,w,h)
        patch = FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.015,rounding_size=0.06",
            facecolor=FILLS[tone], edgecolor=GRAY if tone=="gray" else INK, linewidth=.8,
            linestyle=(0,(4,3)) if dashed else "solid", zorder=2)
        self.ax.add_patch(patch)
        heading = self.text(x+w/2,y+h-.23 if body else y+h/2,title,size=8.7,bold=True,zorder=3)
        self.contained.append((heading,patch))
        if body:
            detail = self.text(x+w/2,y+(h-.34)/2-.02,body,size=8.0,zorder=3)
            self.contained.append((detail,patch))
        self.boxes.append(rect)
        return rect

    def panel(self, x, y, w, h, label):
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor="none",edgecolor="#B2BAC1",linewidth=.65))
        self.text(x+.1,y+h-.2,label,size=8.4,ha="left",bold=True)

    def arrow(self, start, end, *, via=(), dashed=False, color=INK, label=None, at=None):
        points = [start,*via,end]
        path = Path(points,[Path.MOVETO]+[Path.LINETO]*(len(points)-1))
        self.ax.add_patch(FancyArrowPatch(path=path,arrowstyle="-|>",mutation_scale=9,
            linewidth=.85,color=color,linestyle=(0,(4,2.5)) if dashed else "solid",zorder=1))
        if label:
            if at is None: raise ValueError("Edge labels need an explicit unobstructed position")
            self.text(*at,label,size=8,color=color,bbox=dict(facecolor="white",edgecolor="none",pad=1))

    def band(self, x, y, w, h, label, *, color=BLUE, fill=None, hatch=None):
        self.ax.add_patch(Rectangle((x,y),w,h,facecolor=fill or color,edgecolor=INK,linewidth=.65,hatch=hatch))
        if label:
            self.text(x+w/2,y+h/2,label,size=8,color=INK if fill else "white",bold=True)

    def validate(self):
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        for text in self.labels:
            bounds = text.get_window_extent(renderer)
            page = self.fig.bbox.padded(1)
            if not (page.contains(bounds.x0,bounds.y0) and page.contains(bounds.x1,bounds.y1)):
                raise ValueError("Figure text extends past page: "+text.get_text())
        for text,patch in self.contained:
            outer,inner = patch.get_window_extent(renderer).padded(-2),text.get_window_extent(renderer)
            if not (outer.contains(inner.x0,inner.y0) and outer.contains(inner.x1,inner.y1)):
                raise ValueError("Text does not fit its box: "+text.get_text())
        for i,a in enumerate(self.boxes):
            for b in self.boxes[i+1:]:
                if min(a.x+a.w,b.x+b.w)-max(a.x,b.x)>.02 and min(a.y+a.h,b.y+b.h)-max(a.y,b.y)>.02:
                    raise ValueError("Opaque diagram boxes overlap")

    def close(self):
        plt.close(self.fig)
